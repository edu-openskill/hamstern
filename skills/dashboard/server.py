"""hams-dashboard HTTP 서버
사용법: python3 server.py [--port 7777] [--project /path/to/project]
"""
import argparse, json, re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone

STATIC_DIR = Path(__file__).parent / "static"

class HamsHandler(BaseHTTPRequestHandler):
    project_root: str = "."

    def log_message(self, fmt, *args):
        pass

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, content):
        body = content.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"
        root = Path(self.project_root)

        if path == "/":
            index = STATIC_DIR / "index.html"
            self._html(index.read_text(encoding="utf-8") if index.exists() else "<h1>index.html 없음</h1>")
        elif path == "/api/decisions":
            f = root / ".hamstern" / "decisions.md"
            self._json({"content": f.read_text(encoding="utf-8") if f.exists() else ""})
        elif path == "/api/sessions":
            sessions_dir = root / ".hamstern" / "sessions"
            files = []
            if sessions_dir.exists():
                for f in sorted(sessions_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
                    files.append({"name": f.name, "content": f.read_text(encoding="utf-8")})
            self._json({"files": files})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = urlparse(self.path).path.rstrip("/")

        if path == "/api/pin/boss":
            self._handle_boss_pin(body)
        else:
            self._json({"error": "not found"}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/pin/boss/"):
            self._handle_boss_unpin(path[len("/api/pin/boss/"):])
        else:
            self._json({"error": "not found"}, 404)

    def _handle_boss_pin(self, body):
        root = Path(self.project_root)
        decisions_dir = root / ".hamstern"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        decisions_file = decisions_dir / "decisions.md"
        log_file = decisions_dir / "decisions-log.md"

        decision = body.get("decision", "")
        category = body.get("category", "Other")
        background = body.get("background", "")
        source = body.get("source_session", "unknown")

        content = decisions_file.read_text(encoding="utf-8") if decisions_file.exists() else "# 프로젝트 결정사항\n"
        cat_header = f"## {category}"
        new_item = f"- {decision}"

        if cat_header in content:
            content = content.replace(cat_header, cat_header + "\n" + new_item, 1)
        else:
            content = content.rstrip() + f"\n\n{cat_header}\n{new_item}\n"

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        content = re.sub(r"_마지막 업데이트:.*?_\n", f"_마지막 업데이트: {ts}_\n", content)
        if "_마지막 업데이트:" not in content:
            content = content.replace(
                "# 프로젝트 결정사항\n",
                f"# 프로젝트 결정사항\n\n_마지막 업데이트: {ts}_\n_업데이트 방법: /hams:dashboard에서 핀으로 확정_\n"
            )

        decisions_file.write_text(content, encoding="utf-8")

        log_entry = f"\n---\n\n## {ts} | 핀 추가\n- **결정:** {decision}\n- **카테고리:** {category}\n- **배경:** {background}\n- **출처:** mom MD · session {source}\n"
        if not log_file.exists():
            log_file.write_text("# Decisions Log\n<!-- append-only. 수동 편집 금지. -->\n")
        with log_file.open("a", encoding="utf-8") as f:
            f.write(log_entry)

        # CLAUDE.md 에는 쓰지 않음 — 사용자가 /hams:remind 로 명시적 환기.
        self._json({"status": "ok"})

    def _handle_boss_unpin(self, decision_id):
        root = Path(self.project_root)
        decisions_dir = root / ".hamstern"
        decisions_file = decisions_dir / "decisions.md"
        log_file = decisions_dir / "decisions-log.md"

        if not decisions_file.exists():
            self._json({"error": "decisions.md 없음"}, 404)
            return

        lines = decisions_file.read_text(encoding="utf-8").splitlines()
        items = [l for l in lines if l.startswith("- ")]
        try:
            removed = items[int(decision_id)]
        except (ValueError, IndexError):
            self._json({"error": "잘못된 인덱스"}, 400)
            return

        new_content = "\n".join(l for l in lines if l != removed)
        decisions_file.write_text(new_content + "\n", encoding="utf-8")

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        if log_file.exists():
            with log_file.open("a", encoding="utf-8") as f:
                f.write(f"\n---\n\n## {ts} | 핀 제거\n- **결정:** {removed.lstrip('- ')}\n- **제거 이유:** 사용자가 제외 선택\n")

        self._json({"status": "ok"})


def run(port: int, project_root: str):
    HamsHandler.project_root = project_root
    server = HTTPServer(("127.0.0.1", port), HamsHandler)
    print(f"hams-dashboard: http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--project", default=".")
    args = parser.parse_args()
    run(args.port, args.project)
