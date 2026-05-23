import sys, json, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _gate import is_hamstern_project, is_noise_command, is_deeptalk_running

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
AGGREGATE_SCRIPT = PLUGIN_ROOT / "skills" / "dashboard" / "scripts" / "aggregate.py"


def _trigger_aggregate(cwd: str) -> None:
    """Best-effort baby→mom aggregation at session end. Failure is silent."""
    try:
        subprocess.run(
            [sys.executable, str(AGGREGATE_SCRIPT), cwd],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        pass


def _latest_user_prompt(transcript_path: str) -> str:
    """Read the most recent user message from the transcript.

    Used to detect whether the just-finished turn was triggered by a noise
    slash command (diary/registry-collector/skill-creator/skill-picker), in
    which case the assistant's reply — typically very long — should NOT be
    recorded into baby-hamster.
    """
    if not transcript_path or not Path(transcript_path).exists():
        return ""
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").strip().splitlines()
        msgs = [json.loads(l) for l in lines if l.strip()]
        user_msgs = [m for m in msgs if m.get("role") == "user"]
        if not user_msgs:
            return ""
        content = user_msgs[-1].get("content", "")
        if isinstance(content, list):
            content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
        return str(content)
    except Exception:
        return ""


def record_stop(session_id: str, cwd: str, transcript_path: str) -> None:
    if is_deeptalk_running(cwd):
        return
    if is_noise_command(_latest_user_prompt(transcript_path)):
        return
    baby = Path(cwd) / ".hamstern" / "baby-hamster" / f"session_{session_id}.md"
    if not baby.exists():
        return
    last_msg = ""
    if transcript_path and Path(transcript_path).exists():
        try:
            lines = Path(transcript_path).read_text(encoding="utf-8").strip().splitlines()
            msgs = [json.loads(l) for l in lines if l.strip()]
            assistant_msgs = [m for m in msgs if m.get("role") == "assistant"]
            if assistant_msgs:
                content = assistant_msgs[-1].get("content", "")
                if isinstance(content, list):
                    content = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
                last_msg = str(content)[:2000]
        except Exception:
            pass
    with baby.open("a", encoding="utf-8") as f:
        f.write(f"**Claude:** {last_msg}\n")
    _trigger_aggregate(cwd)

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    cwd = data.get("cwd", ".")
    if not is_hamstern_project(cwd):
        return
    record_stop(
        session_id=data.get("session_id", "unknown"),
        cwd=cwd,
        transcript_path=data.get("transcript_path", ""),
    )

if __name__ == "__main__":
    main()
