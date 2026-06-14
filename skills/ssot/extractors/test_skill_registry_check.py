"""스킬 레지스트리 정합성 추출기 테스트 (skill_registry_check.py).

production 은 /hams:<name> 슬래시 참조(레지스트리 미등록) 와 orphan 스킬 디렉터리를
탐지한다. Windows + Python 3.14 의 핸들 상속 버그를 피하려 모든 subprocess 에
stdin=DEVNULL 을 명시한다.
"""

import json
import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).parent / "skill_registry_check.py"


def _git(args, **kw):
    """git 래퍼 — pytest on Windows 핸들 오염 방지를 위해 stdin/stdout/stderr 명시."""
    subprocess.run(
        ["git"] + args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kw,
    ).check_returncode()


def _init_repo_with_skill(tmp_path):
    """최소 git 저장소: marketplace.json(why 등록) + skills/why/SKILL.md
    + .gitignore(__pycache__/) 를 커밋."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(["init", str(root)])
    _git(["-C", str(root), "config", "user.email", "t@t.com"])
    _git(["-C", str(root), "config", "user.name", "T"])
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"skills": ["./skills/why"]}]}), encoding="utf-8")
    skill_dir = root / "skills" / "why"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# why", encoding="utf-8")
    (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    _git(["-C", str(root), "add", "-A"])
    _git(["-C", str(root), "commit", "-m", "init"])
    return root


def _run(root, *files):
    out = subprocess.run([sys.executable, str(SCRIPT), str(root), *files],
                         capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert out.returncode == 0, f"script crashed: {out.stderr}"
    return out.stdout


def test_flags_unregistered_ref(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    (root / "docs.md").write_text("see /hams:record for details", encoding="utf-8")
    out = _run(root, "docs.md")
    assert "WARN" in out and "record" in out and "docs.md:1" in out


def test_ignores_registered_ref(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    (root / "docs.md").write_text("use /hams:why", encoding="utf-8")
    out = _run(root, "docs.md")
    assert "why" not in out


def test_flags_orphan_skill_dir(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    # record/ has only gitignored __pycache__ → git ls-files returns empty → orphan.
    # (Depends on _init_repo_with_skill committing .gitignore with __pycache__/.)
    (root / "skills" / "record" / "__pycache__").mkdir(parents=True)
    (root / "skills" / "record" / "__pycache__" / "t.pyc").write_text("x", encoding="utf-8")
    out = _run(root)
    assert "WARN" in out and "skills/record" in out and "orphan" in out.lower()


def test_diary_core_lib_not_flagged_as_orphan(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    # 공유 lib: SKILL.md 없지만 추적 파일 있음 → orphan 아님
    (root / "skills" / "diary-core").mkdir(parents=True)
    (root / "skills" / "diary-core" / "render.py").write_text("x", encoding="utf-8")
    _git(["-C", str(root), "add", "-A"])
    _git(["-C", str(root), "commit", "-m", "add diary-core"])
    out = _run(root)
    assert "diary-core" not in out


def test_missing_marketplace_does_not_crash(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    (root / ".claude-plugin" / "marketplace.json").unlink()
    out = _run(root, "skills/why/SKILL.md")
    assert "marketplace.json" in out and "건너뜀" in out
