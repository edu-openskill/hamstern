"""hamstern /hams:dashboard 의 local serve 모드.

plugin 정적 자산 (docs/{index,app,style}) + project 데이터 (Sub-D/E: .hamstern/dashboard-data/ 또는 Sub-F: hamstern-data/projects/{uuid}/) 를
path 분기로 동시 serve. 동적 포트 (OS 할당). Stdlib only.
"""
from __future__ import annotations

import argparse
import socket
import sys
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path


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

    def translate_path(self, path: str) -> str:
        return _route_path(path, self.plugin_dir, self.data_dir)

    def log_message(self, fmt, *args):
        pass


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
    args = parser.parse_args()

    HamsHandler.plugin_dir = Path(args.plugin_dir).resolve()
    HamsHandler.data_dir = Path(args.data_dir).resolve()

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
