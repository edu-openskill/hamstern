"""Layer 2 regression for /hams:dashboard local serve.

serve.py 는 plugin 정적 자산 + project 데이터 디렉터리를 path 분기로 동시 serve.
"""
import importlib.util
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
