"""
스킬 레지스트리 정합성 추출기 테스트 (skill_registry_check.py)
"""

import json
import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).parent / "skill_registry_check.py"


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _git(args, **kw):
    """git 명령 래퍼 — pytest on Windows 핸들 오염을 방지하기 위해 stdin/stdout/stderr를 모두 명시."""
    subprocess.run(
        ["git"] + args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kw,
    ).check_returncode()


def _init_repo_with_skill(tmp_path: pathlib.Path) -> pathlib.Path:
    """최소 git 저장소: skills/why/SKILL.md + .gitignore(__pycache__/) 커밋."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(["init", str(root)])
    _git(["-C", str(root), "config", "user.email", "t@t.com"])
    _git(["-C", str(root), "config", "user.name", "T"])

    skill_dir = root / "skills" / "why"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# why", encoding="utf-8")

    # .gitignore — __pycache__/ 무시 (fix 4 테스트의 전제)
    (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")

    _git(["-C", str(root), "add", "-A"])
    _git(["-C", str(root), "commit", "-m", "init"])
    return root


def _make_marketplace(root: pathlib.Path, skill_names: list[str]) -> None:
    plugin_dir = root / ".claude-plugin"
    plugin_dir.mkdir(exist_ok=True)
    data = {"plugins": [{"skills": [f"skills/{n}" for n in skill_names]}]}
    (plugin_dir / "marketplace.json").write_text(
        json.dumps(data), encoding="utf-8")


def _run(root, *files):
    out = subprocess.run([sys.executable, str(SCRIPT), str(root), *files],
                         capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert out.returncode == 0, f"script crashed: {out.stderr}"  # Fix 3
    return out.stdout


# ──────────────────────────────────────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────────────────────────────────────

def test_no_warn_when_skill_registered(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    _make_marketplace(root, ["why"])
    # skills/why 를 참조하는 파일 생성
    ref_file = root / "docs" / "ref.md"
    ref_file.parent.mkdir()
    ref_file.write_text("see skills/why for details", encoding="utf-8")
    out = _run(root, "docs/ref.md")
    assert "미등록" not in out


def test_warn_when_skill_unregistered(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    _make_marketplace(root, [])  # 아무것도 등록 안 함
    ref_file = root / "docs" / "ref.md"
    ref_file.parent.mkdir()
    ref_file.write_text("uses skills/why here", encoding="utf-8")
    out = _run(root, "docs/ref.md")
    assert "why" in out and "미등록" in out


def test_flags_orphan_skill_dir(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    _make_marketplace(root, ["why"])
    # 'record' 디렉터리: SKILL.md 없음, git-추적 파일 없음 → orphan
    record_dir = root / "skills" / "record"
    record_dir.mkdir()
    # record/ has only gitignored __pycache__ → git ls-files returns empty → orphan.
    # (Depends on _init_repo_with_skill committing .gitignore with __pycache__/.)
    (record_dir / "__pycache__").mkdir()
    (record_dir / "__pycache__" / "junk.pyc").write_text("x", encoding="utf-8")
    out = _run(root, "skills/why/SKILL.md")
    assert "record" in out and "orphan" in out


def test_no_orphan_for_tracked_dir_without_skill_md(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    _make_marketplace(root, ["why"])
    # 'wip' 디렉터리: SKILL.md 없지만 파일 하나를 git에 추적
    wip_dir = root / "skills" / "wip"
    wip_dir.mkdir()
    (wip_dir / "notes.md").write_text("WIP", encoding="utf-8")
    _git(["-C", str(root), "add", "skills/wip/notes.md"])
    _git(["-C", str(root), "commit", "-m", "add wip"])
    out = _run(root, "skills/why/SKILL.md")
    assert "wip" not in out


def test_missing_marketplace_does_not_crash(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    (root / ".claude-plugin" / "marketplace.json").unlink(missing_ok=True)
    out = _run(root, "skills/why/SKILL.md")
    assert "marketplace.json" in out and "건너뜀" in out
