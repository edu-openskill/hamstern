"""Layer 2 regression for /hams:dashboard local serve.

serve.py 는 plugin 정적 자산 + project 데이터 디렉터리를 path 분기로 동시 serve.
"""
import importlib.util
import socket
from pathlib import Path

_HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("dashboard_serve", _HERE / "serve.py")
serve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serve)


def _make_handler(plugin_dir: Path, data_dir: Path):
    """HamsHandler 의 class-level 속성을 주입한 서브클래스 반환.

    Note: base class 에도 주입해 self=None 호출 (단위 테스트용) 도 지원.
    """
    class _H(serve.HamsHandler):
        pass
    _H.plugin_dir = plugin_dir
    _H.data_dir = data_dir
    serve.HamsHandler.plugin_dir = plugin_dir
    serve.HamsHandler.data_dir = data_dir
    return _H


def test_translate_root_returns_plugin_index(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir()
    data_dir.mkdir()
    (plugin_dir / "index.html").write_text("<html>plugin index</html>", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/")  # type: ignore[arg-type]
    assert Path(result) == plugin_dir / "index.html"


def test_translate_app_js_returns_plugin_app_js(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (plugin_dir / "app.js").write_text("// app", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/app.js")
    assert Path(result) == plugin_dir / "app.js"


def test_translate_style_css_returns_plugin_style_css(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (plugin_dir / "style.css").write_text("body{}", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/style.css")
    assert Path(result) == plugin_dir / "style.css"


def test_translate_data_manifest_returns_data_dir(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (data_dir / "manifest.json").write_text("{}", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/data/manifest.json")
    assert Path(result) == data_dir / "manifest.json"


def test_translate_data_sessions_subpath(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (data_dir / "sessions").mkdir()
    (data_dir / "sessions" / "foo.md").write_text("# foo", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/data/sessions/foo.md")
    assert Path(result) == data_dir / "sessions" / "foo.md"


def test_translate_blocks_data_traversal(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("forbidden", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/data/../../secret.txt")
    resolved = Path(result).resolve()
    assert secret.resolve() != resolved, "traversal escaped data_dir to access secret"


def test_translate_blocks_root_traversal(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("forbidden", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/../secret.txt")
    resolved = Path(result).resolve()
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
