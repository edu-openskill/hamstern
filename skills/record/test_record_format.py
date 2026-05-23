"""Layer 2 format-compatibility regression for /hams:record.

The SKILL.md is markdown-only — Claude interprets the pseudocode at runtime
and uses Bash/Write tools. This file holds a reference Python implementation
of the merge algorithm (Step 4) so we can regression-test the format spec
(decisions.md + decisions-log.md) against drift.

The reference impl is test-only — it is NOT imported by any runtime code.
"""
import re
from datetime import datetime, timezone


# ─────────────────────────────────────────────────────────────────────────────
# Reference algorithm (test-only mirror of SKILL.md Step 4 pseudocode)
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES = ("Architecture", "Performance", "UI", "Testing", "Deployment", "Other")
SPECIAL_SECTIONS = ("실패·폐기 (왜 안 했나)", "열린 질문")
EMPTY_TEMPLATE = "# 프로젝트 결정사항\n\n_마지막 업데이트: {ts}_\n"
SESSION_MARKER_RE = re.compile(r"<!--\s*session:\s*(\S+?)\s*-->")
ITEM_RE = re.compile(r"^- (?P<body>.+?)(?:\s*<!--\s*session:\s*(?P<sid>\S+?)\s*-->)?$")


def jaccard(a: str, b: str) -> float:
    """Token-set Jaccard similarity (lowercase, whitespace split)."""
    sa, sb = set(a.lower().split()), set(b.lower().split())
    union = sa | sb
    return (len(sa & sb) / len(union)) if union else 0.0


def merge_decision(
    existing_md: str,
    category: str,
    body: str,
    session_id: str,
    ts: str,
) -> str:
    """Apply Step 4 algorithm: session-marker update OR Jaccard skip OR append.

    Returns the new full decisions.md content.
    """
    if not existing_md.strip():
        existing_md = EMPTY_TEMPLATE.format(ts=ts)

    new_item = f"- {body} <!-- session: {session_id} -->"
    section_header = f"## {category}"

    lines = existing_md.splitlines()
    in_target_section = False
    found_section = False
    updated = False
    skipped = False
    out_lines = []

    for ln in lines:
        if ln.startswith("## "):
            in_target_section = ln.strip() == section_header
            if in_target_section:
                found_section = True
            out_lines.append(ln)
            continue

        if in_target_section and ln.startswith("- "):
            m = ITEM_RE.match(ln)
            if m:
                existing_body = m.group("body")
                existing_sid = m.group("sid")
                if existing_sid == session_id:
                    out_lines.append(new_item)  # update in place
                    updated = True
                    continue
                if jaccard(existing_body, body) > 0.7:
                    out_lines.append(ln)  # keep existing, mark skip
                    skipped = True
                    continue
        out_lines.append(ln)

    if not updated and not skipped:
        if not found_section:
            if out_lines and out_lines[-1].strip():
                out_lines.append("")
            out_lines.append(section_header)
        else:
            # find end of target section to append before next ##
            insert_idx = None
            saw_section = False
            for i, ln in enumerate(out_lines):
                if ln.strip() == section_header:
                    saw_section = True
                    continue
                if saw_section and ln.startswith("## "):
                    insert_idx = i
                    break
            if insert_idx is None:
                out_lines.append(new_item)
            else:
                out_lines.insert(insert_idx, new_item)
                # bump _마지막 업데이트 line
                out_lines = _bump_timestamp(out_lines, ts)
                return "\n".join(out_lines) + "\n"
        out_lines.append(new_item)

    out_lines = _bump_timestamp(out_lines, ts)
    return "\n".join(out_lines) + "\n"


def _bump_timestamp(lines, ts):
    out = []
    bumped = False
    for ln in lines:
        if ln.startswith("_마지막 업데이트:"):
            out.append(f"_마지막 업데이트: {ts}_")
            bumped = True
        else:
            out.append(ln)
    if not bumped:
        # insert after the H1
        for i, ln in enumerate(out):
            if ln.startswith("# 프로젝트 결정사항"):
                out.insert(i + 1, "")
                out.insert(i + 2, f"_마지막 업데이트: {ts}_")
                break
    return out


def append_log(existing_log: str, session_id: str, ts: str, decisions, rejects, opens) -> str:
    """Append-only log block."""
    if not existing_log.strip():
        existing_log = "# Decisions Log\n<!-- append-only. 수동 편집 금지. -->\n"
    block = [f"\n## {ts} · session {session_id}"]
    for d in decisions:
        block.append(f"+ [결정] {d}")
    for r in rejects:
        block.append(f"+ [실패] {r}")
    for o in opens:
        block.append(f"+ [열림] {o}")
    return existing_log.rstrip() + "\n" + "\n".join(block) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

TS = "2026-05-23T12:00:00"


def test_empty_decisions_creates_template_and_appends():
    out = merge_decision("", "Architecture", "use portable git-root path", "sess1", TS)
    assert "# 프로젝트 결정사항" in out
    assert f"_마지막 업데이트: {TS}_" in out
    assert "## Architecture" in out
    assert "- use portable git-root path <!-- session: sess1 -->" in out


def test_append_to_existing_category():
    existing = (
        "# 프로젝트 결정사항\n\n"
        "_마지막 업데이트: 2026-05-22T10:00:00_\n\n"
        "## Architecture\n"
        "- old decision <!-- session: old -->\n"
    )
    out = merge_decision(existing, "Architecture", "new decision", "sess2", TS)
    assert "- old decision <!-- session: old -->" in out
    assert "- new decision <!-- session: sess2 -->" in out
    assert f"_마지막 업데이트: {TS}_" in out


def test_new_category_creates_section():
    existing = (
        "# 프로젝트 결정사항\n\n"
        "_마지막 업데이트: 2026-05-22T10:00:00_\n\n"
        "## Architecture\n"
        "- a <!-- session: old -->\n"
    )
    out = merge_decision(existing, "Performance", "fast path", "sess3", TS)
    assert "## Architecture" in out
    assert "## Performance" in out
    assert "- fast path <!-- session: sess3 -->" in out


def test_same_session_id_updates_in_place():
    existing = (
        "# 프로젝트 결정사항\n\n"
        "_마지막 업데이트: 2026-05-22T10:00:00_\n\n"
        "## Architecture\n"
        "- old text <!-- session: sess1 -->\n"
    )
    out = merge_decision(existing, "Architecture", "revised text", "sess1", TS)
    # Old line replaced, no duplicate
    assert out.count("session: sess1") == 1
    assert "- revised text <!-- session: sess1 -->" in out
    assert "- old text <!-- session: sess1 -->" not in out


def test_jaccard_match_skips_duplicate():
    existing = (
        "# 프로젝트 결정사항\n\n"
        "_마지막 업데이트: 2026-05-22T10:00:00_\n\n"
        "## Architecture\n"
        "- use portable git-root path everywhere <!-- session: old -->\n"
    )
    # Same words, different session
    out = merge_decision(existing, "Architecture", "use portable git-root path everywhere", "sess2", TS)
    assert out.count("session: old") == 1
    assert "session: sess2" not in out


def test_log_append_only_preserves_existing_blocks():
    existing_log = (
        "# Decisions Log\n"
        "<!-- append-only. 수동 편집 금지. -->\n\n"
        "## 2026-05-22 10:00 · session old\n"
        "+ [결정] old decision\n"
    )
    out = append_log(existing_log, "sess1", "2026-05-23 12:00",
                     ["new decision"], [], [])
    assert "## 2026-05-22 10:00 · session old" in out
    assert "+ [결정] old decision" in out
    assert "## 2026-05-23 12:00 · session sess1" in out
    assert "+ [결정] new decision" in out


# ─────────────────────────────────────────────────────────────────────────────
# Sub-C additions: sessions/{id}.md (full distill) + migration
# ─────────────────────────────────────────────────────────────────────────────

def write_session(session_id, ts, decisions, rejects, opens):
    """Generate sessions/{session_id}.md content (test-only reference)."""
    lines = [f"# Session {session_id}", "", f"_기록: {ts}_", "", "## 결정"]
    for d in decisions:
        lines.append(f"- {d}")
    lines.extend(["", "## 실패·폐기"])
    for r in rejects:
        lines.append(f"- {r}")
    lines.extend(["", "## 열린 질문"])
    for o in opens:
        lines.append(f"- {o}")
    return "\n".join(lines) + "\n"


def migrate_old_to_new(root):
    """Idempotent migration: baby/mom/boss-hamster → sessions/ + decisions.md.

    `root` is a pathlib.Path pointing to the project root (containing .hamstern/).
    Returns (migrated: bool, backup_path: Path or None).
    """
    import shutil
    from datetime import datetime, timezone
    hamstern = root / ".hamstern"
    has_old = any((hamstern / d).is_dir() for d in ("baby-hamster", "mom-hamster", "boss-hamster"))
    if not has_old:
        return (False, None)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    backup = root / f".hamstern.bak.{ts}"
    shutil.copytree(hamstern, backup)

    sessions = hamstern / "sessions"
    sessions.mkdir(exist_ok=True)

    baby = hamstern / "baby-hamster"
    if baby.is_dir():
        for f in baby.glob("*.md"):
            target = sessions / f.name
            shutil.move(str(f), str(target))
        try:
            baby.rmdir()
        except OSError:
            pass  # not empty (non-md files) — leave

    boss = hamstern / "boss-hamster"
    if (boss / "decisions.md").exists():
        shutil.move(str(boss / "decisions.md"), str(hamstern / "decisions.md"))
    if (boss / "decisions-log.md").exists():
        shutil.move(str(boss / "decisions-log.md"), str(hamstern / "decisions-log.md"))

    shutil.rmtree(hamstern / "mom-hamster", ignore_errors=True)
    shutil.rmtree(boss, ignore_errors=True)

    return (True, backup)


def test_session_file_format_with_all_three_sections():
    out = write_session(
        "sess1", "2026-05-23T12:00:00",
        decisions=["use git-root path (이유: portable)"],
        rejects=["env var detection → 폐기 (이유: undocumented)"],
        opens=["hot limit method"],
    )
    assert "# Session sess1" in out
    assert "_기록: 2026-05-23T12:00:00_" in out
    assert "## 결정" in out
    assert "- use git-root path (이유: portable)" in out
    assert "## 실패·폐기" in out
    assert "- env var detection → 폐기 (이유: undocumented)" in out
    assert "## 열린 질문" in out
    assert "- hot limit method" in out


def test_session_file_idempotent_replace(tmp_path):
    """Same session_id re-call overwrites the session file (replace, not append)."""
    sessions = tmp_path / ".hamstern" / "sessions"
    sessions.mkdir(parents=True)
    f = sessions / "sess1.md"
    f.write_text(write_session("sess1", "2026-05-23T10:00:00",
                                ["old decision"], [], []), encoding="utf-8")
    # Second call with same id but different content
    f.write_text(write_session("sess1", "2026-05-23T12:00:00",
                                ["new decision"], [], []), encoding="utf-8")
    content = f.read_text(encoding="utf-8")
    assert "new decision" in content
    assert "old decision" not in content


def test_migrate_old_structure_to_new(tmp_path):
    """Old baby/mom/boss-hamster tree → flat sessions/ + decisions.md, with backup."""
    hamstern = tmp_path / ".hamstern"
    (hamstern / "baby-hamster").mkdir(parents=True)
    (hamstern / "baby-hamster" / "session_old1.md").write_text("old session 1", encoding="utf-8")
    (hamstern / "baby-hamster" / "session_old2.md").write_text("old session 2", encoding="utf-8")
    (hamstern / "mom-hamster").mkdir()
    (hamstern / "mom-hamster" / "mom.md").write_text("mom aggregate", encoding="utf-8")
    (hamstern / "boss-hamster").mkdir()
    (hamstern / "boss-hamster" / "decisions.md").write_text("# 프로젝트 결정사항\n## Architecture\n- old\n", encoding="utf-8")
    (hamstern / "boss-hamster" / "decisions-log.md").write_text("# Decisions Log\n", encoding="utf-8")

    migrated, backup = migrate_old_to_new(tmp_path)
    assert migrated is True
    assert backup is not None and backup.exists()
    # Backup preserves the old structure
    assert (backup / "baby-hamster" / "session_old1.md").exists()
    assert (backup / "mom-hamster" / "mom.md").exists()
    assert (backup / "boss-hamster" / "decisions.md").exists()
    # New structure correct
    assert (hamstern / "sessions" / "session_old1.md").exists()
    assert (hamstern / "sessions" / "session_old2.md").exists()
    assert (hamstern / "decisions.md").exists()
    assert (hamstern / "decisions-log.md").exists()
    # Old dirs gone
    assert not (hamstern / "baby-hamster").exists()
    assert not (hamstern / "mom-hamster").exists()
    assert not (hamstern / "boss-hamster").exists()


def test_migrate_is_noop_when_no_old_structure(tmp_path):
    """If only new structure exists, migrate does nothing."""
    hamstern = tmp_path / ".hamstern"
    (hamstern / "sessions").mkdir(parents=True)
    (hamstern / "sessions" / "session_new.md").write_text("new", encoding="utf-8")
    (hamstern / "decisions.md").write_text("# 프로젝트 결정사항\n", encoding="utf-8")

    migrated, backup = migrate_old_to_new(tmp_path)
    assert migrated is False
    assert backup is None
    # New structure intact
    assert (hamstern / "sessions" / "session_new.md").exists()
    assert (hamstern / "decisions.md").exists()
