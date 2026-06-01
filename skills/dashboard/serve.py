"""hamstern /hams:dashboard 의 local serve 모드.

plugin 정적 자산 (docs/{index,app,style}) + project 데이터 (Sub-D/E: .hamstern/dashboard-data/ 또는 Sub-F: hamstern-data/projects/{uuid}/) 를
path 분기로 동시 serve. 동적 포트 (OS 할당). Stdlib only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import socket
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path


def _load_remove_module():
    """sibling 스킬 audit-decisions/remove.py 를 로드 (삭제 로직 단일 소스 재사용)."""
    p = Path(__file__).resolve().parent.parent / "audit-decisions" / "remove.py"
    spec = importlib.util.spec_from_file_location("hams_remove", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _safe_join(base: Path, rel: str) -> str:
    """base 의 자손인지 검증 후 path 반환. 탈출 시 sentinel (존재하지 않는 path) 반환 → 404."""
    candidate = (base / rel).resolve()
    base_resolved = base.resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError:
        return str(base_resolved / "__forbidden__")
    return str(candidate)


def _route_path(path: str, plugin_dir: Path, data_dir: Path) -> str:
    """순수 함수 — HTTP request path 를 파일시스템 path 로 매핑. test 가 직접 호출."""
    path = path.split("?", 1)[0].split("#", 1)[0]
    if path.startswith("/data/"):
        return _safe_join(data_dir, path[len("/data/"):])
    if path in ("/", ""):
        path = "/index.html"
    return _safe_join(plugin_dir, path.lstrip("/"))


class HamsHandler(SimpleHTTPRequestHandler):
    plugin_dir: Path = None
    data_dir: Path = None
    hamstern_data: Path = None   # 지정 시 do_POST 삭제 활성 (메커니즘 B). None = 읽기 전용.

    def translate_path(self, path: str) -> str:
        return _route_path(path, self.plugin_dir, self.data_dir)

    def log_message(self, fmt, *args):
        pass

    def _send_json(self, code: int, obj: dict) -> None:
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/api/remove-decision":
            self._send_json(404, {"ok": False, "error": "unknown endpoint"})
            return
        hd = HamsHandler.hamstern_data
        if not hd:
            # publish/정적 모드 — 서버 삭제 비활성. 클라이언트가 클립보드 fallback.
            self._send_json(400, {"ok": False, "error": "read-only server (no --hamstern-data)"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 1_000_000:
                raise ValueError("bad content length")
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            uuid = str(body.get("uuid", "")).strip()
            text = str(body.get("text", "")).strip()
            if not uuid or not text:
                raise ValueError("uuid and text required")
        except Exception as e:
            self._send_json(400, {"ok": False, "error": f"bad request: {e}"})
            return

        base_dir = hd / "projects" / uuid
        try:
            base_dir.resolve().relative_to((hd / "projects").resolve())
        except ValueError:
            self._send_json(400, {"ok": False, "error": "invalid uuid"})
            return
        if not base_dir.is_dir():
            self._send_json(404, {"ok": False, "error": "project not found"})
            return

        try:
            remove = _load_remove_module()
            result = remove.run(base_dir=base_dir, text=text)
        except Exception as e:
            self._send_json(500, {"ok": False, "error": f"remove failed: {e}"})
            return
        if not getattr(result, "removed", False):
            self._send_json(404, {"ok": False, "error": getattr(result, "reason", "no match")})
            return

        # served 복사본 동기화 → 클라이언트 reload 가 최신 반영
        self._sync_served(uuid, base_dir)
        pushed = self._git_commit_push(hd, uuid)
        self._send_json(200, {"ok": True, "removed": result.line, "pushed": pushed})

    def _sync_served(self, uuid: str, base_dir: Path) -> None:
        data_dir = HamsHandler.data_dir
        if not data_dir:
            return
        dst = data_dir / "p" / uuid
        try:
            dst.mkdir(parents=True, exist_ok=True)
            for fn in ("decisions.md", "decisions-log.md"):
                src = base_dir / fn
                if src.is_file():
                    shutil.copy2(src, dst / fn)
        except Exception:
            pass  # 동기화 실패해도 삭제 자체는 성공

    def _git_commit_push(self, hd: Path, uuid: str) -> bool:
        def git(*args):
            return subprocess.run(
                ["git", "-C", str(hd), *args],
                capture_output=True, text=True,
            )
        git("add", f"projects/{uuid}/decisions.md", f"projects/{uuid}/decisions-log.md")
        commit = git("commit", "-m", "dashboard: remove decision")
        if commit.returncode != 0:
            return False  # nothing to commit / commit 실패
        push = git("push", "origin", "HEAD")
        return push.returncode == 0  # 오프라인/리모트 없음이면 local commit 만


def pick_port() -> int:
    """OS 가 할당한 자유 포트 (ephemeral range)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="hamstern dashboard local server")
    parser.add_argument("--plugin-dir", required=True, help="docs/ 자산이 있는 plugin 디렉터리")
    parser.add_argument("--data-dir", required=True, help="build.py 가 만든 데이터 디렉터리 (Sub-D/E: .hamstern/dashboard-data, Sub-F: hamstern-data 의 docs/data 또는 임시 dir)")
    parser.add_argument("--port", type=int, default=0, help="0 = OS 동적 할당")
    parser.add_argument("--hamstern-data", help="지정 시 do_POST 서버사이드 결정 삭제+git push 활성 (로컬 모드). 미지정=읽기 전용.")
    args = parser.parse_args()

    HamsHandler.plugin_dir = Path(args.plugin_dir).resolve()
    HamsHandler.data_dir = Path(args.data_dir).resolve()
    HamsHandler.hamstern_data = Path(args.hamstern_data).resolve() if args.hamstern_data else None

    if not HamsHandler.plugin_dir.is_dir():
        print(f"plugin-dir not found: {HamsHandler.plugin_dir}", file=sys.stderr)
        sys.exit(1)

    HamsHandler.data_dir.mkdir(parents=True, exist_ok=True)

    port = args.port if args.port else pick_port()
    try:
        server = HTTPServer(("127.0.0.1", port), HamsHandler)
    except OSError as e:
        print(f"failed to bind port {port}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"http://localhost:{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
