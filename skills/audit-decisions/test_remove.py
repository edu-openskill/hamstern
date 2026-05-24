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


def test_removes_line_with_session_marker(tmp_path):
    _setup(
        tmp_path,
        "# d\n\n## A\n- foo bar <!-- session: session_2026-05-22.md -->\n- baz\n",
    )

    result = removemod.run(project_root=tmp_path, text="foo bar")

    assert result.removed is True
    new = (tmp_path / ".hamstern" / "decisions.md").read_text(encoding="utf-8")
    assert "foo bar" not in new
    assert "- baz" in new


def test_no_match_returns_false(tmp_path):
    _setup(tmp_path, "# d\n\n## A\n- foo\n")

    result = removemod.run(project_root=tmp_path, text="does not exist")

    assert result.removed is False
    assert "no matching decision" in result.reason
    assert (tmp_path / ".hamstern" / "decisions.md").read_text(encoding="utf-8") == \
        "# d\n\n## A\n- foo\n"


def test_only_first_match_removed(tmp_path):
    _setup(tmp_path, "# d\n\n## A\n- dup\n- dup\n")

    result = removemod.run(project_root=tmp_path, text="dup")

    assert result.removed is True
    new = (tmp_path / ".hamstern" / "decisions.md").read_text(encoding="utf-8")
    assert new.count("- dup") == 1


def test_log_appended_on_successful_remove(tmp_path):
    _setup(
        tmp_path,
        "# d\n\n## A\n- foo\n",
        log_md="# Decisions Log\n",
    )

    removemod.run(project_root=tmp_path, text="foo")

    log = (tmp_path / ".hamstern" / "decisions-log.md").read_text(encoding="utf-8")
    assert "핀 제거" in log
    assert "**결정:** foo" in log


def test_run_with_base_dir_arg(tmp_path):
    """Sub-F: base_dir 직접 지정 (hamstern-data/projects/{uuid}/)."""
    base = tmp_path / "uuid-abc"
    base.mkdir()
    (base / "decisions.md").write_text("# d\n\n## A\n- foo\n", encoding="utf-8")

    result = removemod.run(base_dir=base, text="foo")

    assert result.removed is True
    new = (base / "decisions.md").read_text(encoding="utf-8")
    assert "- foo" not in new
