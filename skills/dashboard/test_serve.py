"""Layer 2 regression for /hams:dashboard local serve.

serve.py 는 plugin 정적 자산 + project 데이터 디렉터리를 path 분기로 동시 serve.
"""
import importlib.util
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

_HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("dashboard_serve", _HERE / "serve.py")
serve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serve)


def _route(plugin_dir: Path, data_dir: Path, request_path: str) -> Path:
    """test 헬퍼 — _route_path 의 결과를 Path 로 감싸 반환."""
    return Path(serve._route_path(request_path, plugin_dir, data_dir))


def test_translate_root_returns_plugin_index(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir()
    data_dir.mkdir()
    (plugin_dir / "index.html").write_text("<html>plugin index</html>", encoding="utf-8")

    assert _route(plugin_dir, data_dir, "/") == plugin_dir / "index.html"


def test_translate_app_js_returns_plugin_app_js(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (plugin_dir / "app.js").write_text("// app", encoding="utf-8")

    assert _route(plugin_dir, data_dir, "/app.js") == plugin_dir / "app.js"


def test_translate_style_css_returns_plugin_style_css(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (plugin_dir / "style.css").write_text("body{}", encoding="utf-8")

    assert _route(plugin_dir, data_dir, "/style.css") == plugin_dir / "style.css"


def test_translate_data_manifest_returns_data_dir(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (data_dir / "manifest.json").write_text("{}", encoding="utf-8")

    assert _route(plugin_dir, data_dir, "/data/manifest.json") == data_dir / "manifest.json"


def test_translate_data_sessions_subpath(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (data_dir / "sessions").mkdir()
    (data_dir / "sessions" / "foo.md").write_text("# foo", encoding="utf-8")

    assert _route(plugin_dir, data_dir, "/data/sessions/foo.md") == data_dir / "sessions" / "foo.md"


def test_translate_blocks_data_traversal(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("forbidden", encoding="utf-8")

    resolved = _route(plugin_dir, data_dir, "/data/../../secret.txt").resolve()
    assert secret.resolve() != resolved, "traversal escaped data_dir to access secret"


def test_translate_blocks_root_traversal(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("forbidden", encoding="utf-8")

    resolved = _route(plugin_dir, data_dir, "/../secret.txt").resolve()
    assert secret.resolve() != resolved, "traversal escaped plugin_dir to access secret"


def test_pick_port_returns_valid_bindable_port():
    p1 = serve.pick_port()
    p2 = serve.pick_port()
    assert 1024 <= p1 <= 65535
    assert 1024 <= p2 <= 65535
    assert isinstance(p1, int) and isinstance(p2, int)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", p1))
    finally:
        s.close()


def test_e2e_http_server_serves_plugin_and_data(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (plugin_dir / "index.html").write_text("<html>idx</html>", encoding="utf-8")
    (plugin_dir / "app.js").write_text("// app", encoding="utf-8")
    (data_dir / "manifest.json").write_text('{"schema_version":1}', encoding="utf-8")

    # 인스턴스화 시 plugin_dir/data_dir 가 필요 — subclass 로 주입
    class _H(serve.HamsHandler):
        pass
    _H.plugin_dir = plugin_dir
    _H.data_dir = data_dir

    port = serve.pick_port()
    server = HTTPServer(("127.0.0.1", port), _H)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as r:
            assert r.status == 200
            assert b"idx" in r.read()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/app.js", timeout=2) as r:
            assert r.status == 200
            assert b"app" in r.read()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/data/manifest.json", timeout=2) as r:
            assert r.status == 200
            assert b"schema_version" in r.read()
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/data/../../secret", timeout=2)
            assert False, "traversal request should 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
