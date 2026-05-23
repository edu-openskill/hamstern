"""Direct args form: /hams:audit-decisions remove "<text>"
실패 시 stderr 메시지 + non-zero exit. 성공 시 decisions.md 갱신 + log append.
"""
import importlib.util
from pathlib import Path

_HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("audit_remove", _HERE / "remove.py")
removemod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(removemod)


def _setup(tmp_path: Path, decisions_md: str, log_md: str | None = None):
    h = tmp_path / ".hamstern"
    h.mkdir()
    (h / "decisions.md").write_text(decisions_md, encoding="utf-8")
    if log_md is not None:
        (h / "decisions-log.md").write_text(log_md, encoding="utf-8")
    return h


def test_removes_matching_line(tmp_path):
    h = _setup(tmp_path, "# decisions\n\n## A\n- foo bar\n- baz\n")

    result = removemod.run(project_root=tmp_path, text="foo bar")

    assert result.removed is True
    assert result.line == "- foo bar"
    new = (h / "decisions.md").read_text(encoding="utf-8")
    assert "- foo bar" not in new
    assert "- baz" in new
