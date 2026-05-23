"""Layer 2 regression for /hams:dashboard build step.

build.py 는 .hamstern/*.md 를 docs/data/ 로 번들 + manifest.json 생성.
"""
import json
from pathlib import Path

from skills.dashboard import build


def _setup_project(tmp_path: Path, *, decisions: str | None = None,
                   decisions_log: str | None = None,
                   sessions: dict[str, str] | None = None) -> Path:
    """tmp_path 에 .hamstern/ 가짜 프로젝트 생성."""
    hamstern = tmp_path / ".hamstern"
    hamstern.mkdir()
    if decisions is not None:
        (hamstern / "decisions.md").write_text(decisions, encoding="utf-8")
    if decisions_log is not None:
        (hamstern / "decisions-log.md").write_text(decisions_log, encoding="utf-8")
    if sessions:
        (hamstern / "sessions").mkdir()
        for name, body in sessions.items():
            (hamstern / "sessions" / name).write_text(body, encoding="utf-8")
    return tmp_path


def test_empty_hamstern_produces_empty_manifest(tmp_path):
    project = _setup_project(tmp_path)
    out = tmp_path / "docs" / "data"

    build.run(project_root=project, out_dir=out)

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["decisions"] is False
    assert manifest["decisions_log"] is False
    assert manifest["sessions"] == []
    assert not (out / "decisions.md").exists()
    assert not (out / "decisions-log.md").exists()
