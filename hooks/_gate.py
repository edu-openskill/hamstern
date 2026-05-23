"""Project-scoping gate for hamstern plugin hooks.

Plugin hooks fire globally in every Claude Code session. To keep hamstern's
side effects (creating .hamstern/baby-hamster/, writing CLAUDE.md, etc.)
contained to projects the user actually uses hamstern in, every hook must
gate itself with is_hamstern_project() at entry.

Marker: presence of a `.hamstern/` directory in the session cwd, AND
absence of `.hamstern/.disabled` (so users can pause hamstern in a project
without deleting their data).
"""
import re
import time
from pathlib import Path
from typing import Optional


# Slash commands whose user prompt AND assistant reply are treated as noise
# from the project's perspective — they are meta operations (publishing a
# blog post, collecting an external skill registry, picking/creating skills)
# unrelated to the project's development decisions. Both user_prompt.py
# (filtering the user prompt) and stop.py (filtering the assistant reply)
# consult this list so neither side leaks into baby-hamster.
NOISE_COMMAND_RE = re.compile(
    r"^\s*/hams:(diary|registry-collector|skill-creator|skill-picker)\b"
)


def is_noise_command(prompt: Optional[str]) -> bool:
    """True if the prompt is a slash invocation of a known noise skill."""
    if not prompt:
        return False
    return bool(NOISE_COMMAND_RE.match(prompt))


def is_hamstern_project(cwd: Optional[str]) -> bool:
    """Return True if `cwd` looks like a hamstern-active project.

    Active means:
      - `.hamstern/` directory exists at project root
      - `.hamstern/.disabled` does NOT exist (toggle-off marker)

    The `.hamstern/` directory doubles as both data store and activation
    marker — hamstern itself creates it on first use via /hams:start.
    """
    if not cwd:
        return False
    try:
        marker = Path(cwd) / ".hamstern"
        if not marker.is_dir():
            return False
        if (marker / ".disabled").exists():
            return False
        return True
    except (OSError, ValueError):
        return False


def is_deeptalk_running(cwd: Optional[str]) -> bool:
    """True if a fresh `.deeptalk-running` marker exists in `.hamstern/`.

    The marker is set by skills (deeptalk, rule, skill-creator) that want
    to suppress baby-hamster recording during multi-turn user interactions.
    Auto-deletes stale markers older than 24 hours so a crashed session
    doesn't permanently silence the hook.
    """
    if not cwd:
        return False
    try:
        flag = Path(cwd) / ".hamstern" / ".deeptalk-running"
        if not flag.exists():
            return False
        if time.time() - flag.stat().st_mtime > 86400:
            flag.unlink(missing_ok=True)
            return False
        return True
    except (OSError, ValueError):
        return False
