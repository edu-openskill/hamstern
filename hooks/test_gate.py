"""Tests for the project-scoping gate."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from _gate import is_hamstern_project


def test_returns_true_when_hamstern_dir_exists(tmp_path):
    (tmp_path / ".hamstern").mkdir()
    assert is_hamstern_project(str(tmp_path)) is True


def test_returns_false_when_hamstern_dir_missing(tmp_path):
    assert is_hamstern_project(str(tmp_path)) is False


def test_returns_false_when_hamstern_is_a_file_not_dir(tmp_path):
    (tmp_path / ".hamstern").write_text("oops")
    assert is_hamstern_project(str(tmp_path)) is False


def test_returns_false_when_disabled_marker_present(tmp_path):
    (tmp_path / ".hamstern").mkdir()
    (tmp_path / ".hamstern" / ".disabled").write_text("")
    assert is_hamstern_project(str(tmp_path)) is False


def test_handles_missing_cwd_gracefully():
    assert is_hamstern_project("/nonexistent/path/does/not/exist") is False


def test_handles_empty_string_cwd():
    assert is_hamstern_project("") is False


def test_handles_none_cwd():
    assert is_hamstern_project(None) is False


def test_deeptalk_running_returns_false_when_marker_missing(tmp_path):
    from _gate import is_deeptalk_running
    (tmp_path / ".hamstern").mkdir()
    assert is_deeptalk_running(str(tmp_path)) is False


def test_deeptalk_running_returns_true_when_fresh_marker_present(tmp_path):
    from _gate import is_deeptalk_running
    flag = tmp_path / ".hamstern" / ".deeptalk-running"
    flag.parent.mkdir()
    flag.touch()
    assert is_deeptalk_running(str(tmp_path)) is True


def test_deeptalk_running_auto_deletes_stale_marker(tmp_path):
    """Marker older than 24h is treated as not-running AND auto-removed."""
    import os, time
    from _gate import is_deeptalk_running
    flag = tmp_path / ".hamstern" / ".deeptalk-running"
    flag.parent.mkdir()
    flag.touch()
    old = time.time() - 90000  # 25 hours ago
    os.utime(flag, (old, old))
    assert is_deeptalk_running(str(tmp_path)) is False
    assert not flag.exists(), "stale marker should be auto-deleted"
