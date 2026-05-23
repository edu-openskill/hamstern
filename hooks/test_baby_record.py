import tempfile, json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

def test_user_prompt_creates_baby_file():
    from user_prompt import record_prompt
    with tempfile.TemporaryDirectory() as d:
        record_prompt(session_id="s1", cwd=d, prompt="안녕하세요")
        baby = Path(d) / ".hamstern" / "baby-hamster" / "session_s1.md"
        assert baby.exists()
        content = baby.read_text()
        assert "session_id: s1" in content
        assert "**User:** 안녕하세요" in content

def test_user_prompt_appends_turns():
    from user_prompt import record_prompt
    with tempfile.TemporaryDirectory() as d:
        record_prompt(session_id="s1", cwd=d, prompt="첫 번째")
        record_prompt(session_id="s1", cwd=d, prompt="두 번째")
        baby = Path(d) / ".hamstern" / "baby-hamster" / "session_s1.md"
        content = baby.read_text()
        assert "## Turn 1" in content
        assert "## Turn 2" in content

def test_user_prompt_skipped_when_deeptalk_running():
    from user_prompt import record_prompt
    with tempfile.TemporaryDirectory() as d:
        flag = Path(d) / ".hamstern" / ".deeptalk-running"
        flag.parent.mkdir(parents=True)
        flag.touch()
        record_prompt(session_id="s1", cwd=d, prompt="deep talk content")
        baby = Path(d) / ".hamstern" / "baby-hamster" / "session_s1.md"
        assert not baby.exists()

def test_user_prompt_proceeds_when_deeptalk_flag_stale():
    import os, time
    from user_prompt import record_prompt
    with tempfile.TemporaryDirectory() as d:
        flag = Path(d) / ".hamstern" / ".deeptalk-running"
        flag.parent.mkdir(parents=True)
        flag.touch()
        old = time.time() - 90000
        os.utime(flag, (old, old))
        record_prompt(session_id="s1", cwd=d, prompt="후속 대화")
        baby = Path(d) / ".hamstern" / "baby-hamster" / "session_s1.md"
        assert baby.exists()
        assert "**User:** 후속 대화" in baby.read_text(encoding="utf-8")
        assert not flag.exists()

def test_stop_skipped_when_deeptalk_running():
    from stop import record_stop
    with tempfile.TemporaryDirectory() as d:
        baby = Path(d) / ".hamstern" / "baby-hamster" / "session_s1.md"
        baby.parent.mkdir(parents=True)
        baby.write_text("---\nsession_id: s1\n---\n", encoding="utf-8")
        flag = Path(d) / ".hamstern" / ".deeptalk-running"
        flag.touch()
        record_stop(session_id="s1", cwd=d, transcript_path="")
        assert "**Claude:**" not in baby.read_text(encoding="utf-8")
