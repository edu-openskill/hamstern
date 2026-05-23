# Multi-Platform Session Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sub-project B spec (`docs/discussions/2026-05-23-multi-platform-handoff-design.md`) 를 단계별로 실행한다 — `docs/conventions.md` + `skills/record/SKILL.md` 신설 + 마켓플레이스 등록 + 포맷 호환성 회귀 테스트 + CLI 시나리오 manual 검증.

**Architecture:** record 는 신규 markdown-only 스킬. 런타임 동작은 Claude 가 SKILL.md 의 5-step 의사코드를 해석해 Bash/Write 도구로 수행. 테스트는 format spec 의 round-trip 호환성 검증 (reference 알고리즘 포함). 기존 hooks 또는 다른 스킬 변경 없음.

**Tech Stack:** Python 3 (pytest, stdlib only), markdown (SKILL.md + conventions.md), git (commit per task).

**Spec:** `docs/discussions/2026-05-23-multi-platform-handoff-design.md` (commit `88f2329`)

---

## File Structure

**신규 파일 (4개)**

| 파일 | 책임 |
|------|------|
| `docs/conventions.md` | 표준 저장소 레이아웃 + 경로 해석 의사코드 + 능력 프로브 패턴 + decisions.md/decisions-log.md 포맷 스펙. record + 향후 sub-project 가 공통 참조. |
| `skills/record/SKILL.md` | `/hams:record` 슬래시 명령 정의. Frontmatter + 5-step 본문 + 두 포맷 스펙 inline. |
| `skills/record/test_record_format.py` | Layer 2 포맷 호환성 회귀 테스트. 참조 Python 알고리즘 (test-only) + 케이스 6개. |
| `docs/plans/2026-05-23-record-verification.md` | Layer 3 manual 검증 결과 (Task 8 에서 생성). |

**수정 파일 (2개)**

| 파일 | 변경 |
|------|------|
| `.claude-plugin/marketplace.json` | `plugins[0].skills` 배열에 `./skills/record` 추가 (1줄) |
| `README.md` | changelog 맨 위에 2026-05-23 Sub-project B 항목 추가 |

---

## Task 0 — 사전 점검

- [ ] **Step 0.1: 현재 테스트 그린 상태 확인 (baseline)**

Run (PowerShell):
```powershell
cd C:\Users\ssarm\workspace\hamstern\hamstern-plugin
python -m pytest hooks/ -q
```
Expected: `18 passed`.

- [ ] **Step 0.2: 작업 브랜치 확인**

Run:
```powershell
git status -sb
git branch --show-current
```
Expected: `main` 브랜치. Sub-project A 의 `skills/why/SKILL.md` dirty 상태는 그대로 유지 (이번에도 건드리지 않음).

---

## Task 1 — `docs/conventions.md` 작성 (Phase 0)

**Files:**
- Create: `docs/conventions.md`

- [ ] **Step 1: Write `docs/conventions.md`**

Create a new file at `docs/conventions.md` with the following exact content:

```markdown
# Hamstern Plugin Conventions

> 모든 hamstern 스킬·hook 이 따르는 공통 규약. 신규 스킬 추가 시 이 문서를 먼저 읽고 따른다.

## 1. 표준 저장소 레이아웃

```
{project_root}/.hamstern/
  baby-hamster/         # 원본 턴 로그 (hook 자동 append, CLI 전용)
  mom-hamster/
    mom.md              # 세션별 baby 집계본 (Stop hook 자동 갱신)
  boss-hamster/
    decisions.md        # 현재 결정사항 (hot, 카테고리별)         ← record/dashboard 공동 쓰기
    decisions-log.md    # append-only 전체 이력 (cold)            ← record 가 append
{project_root}/.claude/rules/{topic}.md (+references/)  # 영구 룰 (자동 로드)
```

`{project_root}` = `git rev-parse --show-toplevel` 결과, 실패 시 `pwd`.

## 2. 경로 해석 의사코드

모든 스킬은 다음 두 함수를 본문 첫 단계에 호출한다 (의사코드 — Claude 가 Bash 도구로 실행):

```
resolve_root():
  try:
    r = $(git rev-parse --show-toplevel 2>/dev/null)
    if r is empty: r = $(pwd)
  except: r = $(pwd)
  return r

ensure_store(r):
  try:
    mkdir -p {r}/.hamstern/boss-hamster
    return OK
  except (no FS, EACCES, ENOENT, sandbox):
    return FALLBACK_TEXT

store_paths(r):
  return {
    decisions: {r}/.hamstern/boss-hamster/decisions.md,
    log:       {r}/.hamstern/boss-hamster/decisions-log.md,
    mom:       {r}/.hamstern/mom-hamster/mom.md
  }
```

## 3. 능력 프로브 패턴 (FS-try + Text-fallback)

환경 식별 변수 (`CLAUDE_CODE_REMOTE` 등) 에 **의존하지 않는다**. 대신 항상 FS 쓰기를 시도하고 실패 시 텍스트 폴백:

```
try:
  ensure_store(r)
  write decisions.md
  write decisions-log.md
on failure:
  output the same markdown to chat
  instruct user to paste into CLI session
```

이 패턴은 Claude Code CLI 에서는 FS 모드, Claude Desktop App sandbox 에서는 텍스트 폴백으로 자연스럽게 분기된다.

## 4. `decisions.md` 포맷

```markdown
# 프로젝트 결정사항

_마지막 업데이트: {ISO timestamp}_

## {카테고리: Architecture | Performance | UI | Testing | Deployment | Other}
- {결정 내용} (이유: {왜}) <!-- session: {id} -->

## 실패·폐기 (왜 안 했나)
- {시도 내용} → 폐기: {이유} <!-- session: {id} -->

## 열린 질문
- {미정 사항} <!-- session: {id} -->
```

규칙:
- 헤더 `# 프로젝트 결정사항` 은 고정
- `_마지막 업데이트: ...` 라인은 매 쓰기마다 갱신
- `## {카테고리}` 는 위 6개 + 특별 카테고리 (`실패·폐기`, `열린 질문`)
- 항목 끝의 `<!-- session: {id} -->` 마커로 idempotent 재호출 시 갱신 매칭
- 중복 판정: Jaccard 유사도 > 0.7 (dashboard 의 dedup 임계와 동일)

## 5. `decisions-log.md` 포맷 (append-only)

```markdown
# Decisions Log
<!-- append-only. 수동 편집 금지. -->

## {YYYY-MM-DD HH:MM} · session {id}
+ [결정] {…}
+ [실패] {…}
+ [열림] {…}
```

규칙:
- 첫 줄 헤더는 파일 생성 시 한 번만
- 매 record 호출마다 `## {timestamp} · session {id}` 블록 1개 append
- 같은 session 재호출 시 새 블록을 append (decisions.md 와 달리 갱신 X — log 는 추적용)

## 6. 진입점 분리 (P6)

| 진입점 | 성격 | 쓰기 대상 |
|--------|------|-----------|
| hook (`UserPromptSubmit`, `Stop`) | 자동 (CLI 전용), raw turn append | `baby-hamster/*.md`, `mom-hamster/mom.md` |
| `/hams:record` | 수동 (CLI + Desktop), distilled decision | `boss-hamster/decisions.md`, `decisions-log.md` |
| `/hams:dashboard` | 수동 (CLI), Opus 분석 + 사용자 핀 | `boss-hamster/decisions.md` |

세 진입점은 **서로 호출하지 않는다**. 같은 저장소 포맷만 공유.
```

- [ ] **Step 2: Commit**

Run:
```powershell
git add docs/conventions.md
git commit -m "docs(conventions): standard layout + path resolution + format spec (Phase 0)"
```

---

## Task 2 — `skills/record/SKILL.md` 작성 (Phase 1)

**Files:**
- Create: `skills/record/SKILL.md`

- [ ] **Step 1: Create directory and write SKILL.md**

Create directory `skills/record/` then write `skills/record/SKILL.md` with the following exact content:

```markdown
---
name: record
description: |
  지금 세션의 결정·실패·열린질문을 정리해 프로젝트 결정 저장소(decisions.md)에 기록.
  CLI·Desktop 양쪽 동작, FS 쓰기 불가 시 텍스트 폴백.
  사용법:
    /hams:record         # 후보 확인 모드 (기본)
    /hams:record --yes   # 후보 자동 채택 (긴 세션 끝)
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# /hams:record

지금 세션에서 합의된 결정·실패·열린질문을 추출(distill)해 프로젝트의 `decisions.md` 에 병합한다. CLI·Desktop 양쪽에서 동일하게 동작 — Desktop sandbox 처럼 FS 쓰기가 안 되면 동일 마크다운을 채팅에 출력해 사용자가 CLI 에서 복붙할 수 있게 한다.

## 왜 record 인가

- `/hams:dashboard` 는 mom→boss 분석·핀 흐름이라 CLI 전용 (Opus 호출 + 백그라운드 서버).
- Stop hook 은 baby/mom 자동 캡쳐라 CLI 전용 + 자동.
- **Desktop App 에서도 결정을 같은 저장소에 남기려면 사용자 트리거 슬래시 명령이 필요** — 그게 record.
- 진입점 분리: hook=raw turn, record=distilled decision, dashboard=Opus 정리. 셋 모두 종착지 `decisions.md` 동일.

자세한 규약은 [`docs/conventions.md`](../../docs/conventions.md) 참조.

## Claude 실행 절차

### Step 1 — 경로 해석 & 저장소 보장

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT=$(pwd)
echo "resolved root: $ROOT"
```

사용자에게 resolved root 를 echo 해서 잘못된 경우 즉시 abort 가능하게 한다.

```bash
mkdir -p "$ROOT/.hamstern/boss-hamster" 2>/dev/null
```

`mkdir` 가 실패하면 (sandbox, EACCES 등) → **Step 5 (텍스트 폴백)** 으로.
`mkdir` 가 성공하면 → Step 2 로.

### Step 2 — Distill (현재 세션 컨텍스트에서 추출)

지금까지의 대화에서 다음 세 종류를 분리해 후보 추출:

1. **결정 (decision)** — 이번 세션에 확정한 것 + 이유 한 줄
   - 예: "포터블 경로는 git-root → pwd 폴백 (이유: 비-git 디렉토리에서도 동작 보장)"
2. **실패·폐기 (rejected)** — 시도했다 버린 것 + 이유 한 줄
   - 예: "환경변수 기반 환경 판단 → 폐기 (이유: CLAUDE_CODE_REMOTE 같은 변수는 미문서, 의존하면 깨짐)"
3. **열린 질문 (open)** — 미정 상태로 남은 것
   - 예: "decisions.md hot 영역 상한을 토픽당 N개로 할지 총 토큰으로 할지"

**중요**:
- 원본 턴 로그는 만들지 않는다 (그건 hook 의 baby 영역).
- 후보 5–15 개 정도가 적정. 너무 많으면 사용자가 검토 부담.
- 각 항목에 `category` 라벨 한 줄 (Architecture/Performance/UI/Testing/Deployment/Other) 부착.

### Step 3 — 사용자 확인 (헛것 방지)

`AskUserQuestion` 으로 카테고리별 후보 표 제시. 각 항목에 keep/drop 선택.

`AskUserQuestion` 이 동작하지 않는 환경 (e.g., Desktop 일부) 에서는 폴백으로 다음 패턴 사용:

```
[ 후보 ]
1. (Architecture) 포터블 경로는 git-root → pwd 폴백 (이유: ...)
2. (실패·폐기) 환경변수 기반 환경 판단 → 폐기 (이유: ...)
3. (열린 질문) decisions.md hot 영역 상한 결정 방식

drop 할 번호를 쉼표로 답하세요 (없으면 enter):
```

호출 인자에 `--yes` 가 있으면 이 확인 단계 skip 하고 전부 채택.

### Step 4 — 병합 기록 (idempotent)

`$ROOT/.hamstern/boss-hamster/decisions.md` 가 없으면 빈 템플릿으로 시작:

```markdown
# 프로젝트 결정사항

_마지막 업데이트: {ISO timestamp}_
```

각 채택된 후보에 대해:

1. **세션 마커 매칭**: 같은 `<!-- session: {id} -->` 마커가 이미 있으면 그 항목을 **갱신** (replace).
2. **Jaccard 매칭**: 새 항목 텍스트 vs 기존 항목 텍스트의 Jaccard 유사도가 > 0.7 이면 **skip** (이미 있는 결정).
3. **신규**: 위 두 케이스 아니면 해당 카테고리 (`## {category}`) 섹션 끝에 **append**. 카테고리 섹션이 없으면 새로 생성.

쓰기 시 `_마지막 업데이트: ...` 라인을 현재 ISO timestamp 로 갱신.

이어서 `decisions-log.md` 에 append-only 블록을 추가:

```markdown
## {YYYY-MM-DD HH:MM} · session {id}
+ [결정] 포터블 경로는 git-root → pwd 폴백
+ [실패] 환경변수 기반 환경 판단 → 폐기
+ [열림] decisions.md hot 영역 상한 결정 방식
```

`decisions-log.md` 가 없으면 첫 줄에 `# Decisions Log\n<!-- append-only. 수동 편집 금지. -->\n` 추가 후 블록 append.

### Step 5 — 텍스트 폴백 (FS 쓰기 차단 시)

다음 메시지를 채팅에 출력:

```
⚠️ 파일 시스템 쓰기 불가 환경입니다 (예: Claude Desktop sandbox).
아래 마크다운을 CLI 세션에서 {project_root}/.hamstern/boss-hamster/ 에 직접 병합하세요.

=== decisions.md (병합용) ===
(전체 decisions.md 내용을 Step 4 규칙대로 합성해 출력 — 기존 decisions.md 를 모르므로 새 항목만 카테고리별 정리해서 보여줌)

=== decisions-log.md (append 블록) ===
(Step 4 의 timestamp 블록)
```

포맷이 동일하므로 사용자가 복붙하면 CLI 의 record 호출과 같은 저장소로 수렴.

## 사용 예시

```bash
# 마일스톤 끝에 한 번
/hams:record

# 긴 세션의 정리 패스 (확인 생략)
/hams:record --yes
```

## 다른 진입점과의 관계

- **hook (CLI 자동)** 은 raw turn 을 baby 에 append. record 는 distilled 결정을 decisions 에 합침. 둘은 **서로 호출하지 않는다**. 같은 저장소 포맷만 공유.
- **dashboard** 의 ✅ 핀 흐름도 같은 `decisions.md` 에 쓴다. record 와 dashboard 모두 Step 4 의 dedup (session 마커 + Jaccard) 을 따르므로 충돌하지 않음.
- **/hams:remind** 는 record 가 쓴 `decisions.md` 를 그대로 환기 — 포맷 호환성이 핵심.
```

- [ ] **Step 2: Commit**

Run:
```powershell
git add skills/record/SKILL.md
git commit -m "feat(record): add /hams:record skill for manual session capture (CLI + Desktop)"
```

---

## Task 3 — `skills/record/test_record_format.py` 작성 (Layer 2)

**Files:**
- Create: `skills/record/test_record_format.py`

이 파일은 **참조 알고리즘 (test-only)** + 6개 케이스 형태. 런타임 코드가 아닌 spec 검증용 — Claude 가 SKILL.md 본문의 의사코드를 따랐을 때 나와야 할 출력이 reference 알고리즘과 일치하는지 회귀 보호.

- [ ] **Step 1: Write the test file**

`skills/record/test_record_format.py`:

```python
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
```

- [ ] **Step 2: Run the tests**

Run:
```powershell
python -m pytest skills/record/test_record_format.py -v
```
Expected: 6 PASS.

If any fail, the reference algorithm needs adjustment (it must round-trip the spec correctly).

- [ ] **Step 3: Confirm hooks tests still green (regression)**

Run:
```powershell
python -m pytest hooks/ -q
```
Expected: `18 passed`.

- [ ] **Step 4: Commit**

Run:
```powershell
git add skills/record/test_record_format.py
git commit -m "test(record): format-compatibility regression for decisions.md + decisions-log.md"
```

---

## Task 4 — `.claude-plugin/marketplace.json` 에 record 등록

**Files:**
- Modify: `.claude-plugin/marketplace.json` (skills 배열에 1줄 추가)

- [ ] **Step 1: Add `./skills/record` to the skills array**

`.claude-plugin/marketplace.json` 의 `plugins[0].skills` 배열 (현재 12개 항목) 마지막에 `./skills/record` 추가. 위치는 알파벳 순 X — 기존 순서 유지하고 끝에 append:

수정 후 파일 전체:

```json
{
  "name": "hamstern",
  "owner": {
    "name": "getinthere"
  },
  "metadata": {
    "description": "hamstern 프로젝트 관리 플러그인 (Tier 1-4 회의록, 결정사항, 스킬 추천)",
    "version": "1.1.0"
  },
  "plugins": [
    {
      "name": "hams",
      "description": "hamstern 프로젝트 관리 플러그인 (Tier 1-4 회의록, 결정사항, 스킬 추천)",
      "source": "./",
      "skills": [
        "./skills/skill-picker",
        "./skills/skill-creator",
        "./skills/dashboard",
        "./skills/audit-decisions",
        "./skills/registry-collector",
        "./skills/remind",
        "./skills/why",
        "./skills/rule",
        "./skills/diary",
        "./skills/start",
        "./skills/stop",
        "./skills/deeptalk",
        "./skills/record"
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate JSON**

Run:
```powershell
python -c "import json; json.load(open('.claude-plugin/marketplace.json'))"
```
Expected: no output (silent = valid JSON).

- [ ] **Step 3: Commit**

Run:
```powershell
git add .claude-plugin/marketplace.json
git commit -m "feat(marketplace): register /hams:record skill"
```

---

## Task 5 — Layer 1 정적 검증

**Files:** (검증만)

- [ ] **Step 1: SKILL.md frontmatter parsing**

Run (PowerShell):
```powershell
python -c "import re; t=open('skills/record/SKILL.md',encoding='utf-8').read(); m=re.match(r'---\n(.+?)\n---', t, re.DOTALL); print('frontmatter ok' if m and 'name: record' in m.group(1) and 'description:' in m.group(1) and 'allowed-tools:' in m.group(1) else 'FAIL')"
```
Expected: `frontmatter ok`.

- [ ] **Step 2: conventions.md 필수 섹션 존재 확인**

Run:
```powershell
$content = Get-Content docs/conventions.md -Raw
foreach ($h in '# Hamstern Plugin Conventions','## 1. 표준 저장소 레이아웃','## 2. 경로 해석 의사코드','## 3. 능력 프로브','## 4. `decisions.md` 포맷','## 5. `decisions-log.md` 포맷','## 6. 진입점 분리') {
  "{0,-50} {1}" -f $h, $(if ($content.Contains($h)) {'OK'} else {'MISSING'})
}
```
Expected: 모두 `OK`.

- [ ] **Step 3: dashboard 의 `_handle_boss_pin` 가 record 와 동일 포맷 사용 확인**

Run:
```powershell
Select-String -Path 'skills/dashboard/server.py' -Pattern '# 프로젝트 결정사항|## \{category\}|마지막 업데이트' | Select-Object LineNumber, Line
```
Expected: 최소 2개 매치 (헤더 + 카테고리 + 타임스탬프). 이는 record 의 출력이 dashboard 가 읽는 포맷과 호환됨을 의미.

- [ ] **Step 4: No commit** — 검증만, 다음 Task 로.

---

## Task 6 — README 신규 changelog 항목

**Files:**
- Modify: `README.md` (changelog 맨 위에 항목 추가)

- [ ] **Step 1: Read README to confirm current state**

`Read` `README.md` 의 changelog 영역 (`## 📝 변경 내역 (Changelog)` 헤더와 그 아래) 을 확인. 가장 위 항목이 Sub-project A 의 `### 2026-05-23 — cmux 잔재 제거 + hooks 중복 정리 + 대시보드 검증` 이어야 함.

- [ ] **Step 2: Insert new entry ABOVE the Sub-project A entry**

Sub-project A 항목 바로 위에 다음 신규 entry 를 삽입 (즉, 이게 새로운 최상단 entry 가 됨):

```markdown
### 2026-05-23 — 멀티 플랫폼 핸드오프 (`/hams:record` 신설)

- **`/hams:record` 신규 스킬** — 지금 세션의 결정·실패·열린질문을 distill 해 `decisions.md` 에 idempotent 병합. **Claude Code CLI + Claude Desktop App 양쪽에서 동작** (Desktop sandbox 처럼 FS 쓰기 실패 시 동일 마크다운을 채팅 출력해 사용자가 CLI 에서 복붙).
- **공통 규약 문서 `docs/conventions.md`** — 표준 저장소 레이아웃 + 경로 해석 의사코드 (`git rev-parse → pwd` 폴백) + 능력 프로브 패턴 + decisions.md / decisions-log.md 포맷 스펙. 향후 신규 스킬도 이 규약을 따른다.
- **진입점 분리 명문화** — hook(자동/raw turn) ≠ record(수동/distilled) ≠ dashboard(Opus 정리). 셋 모두 같은 `decisions.md` 에 쓰되 서로 호출하지 않음.
- **포맷 호환성 회귀 테스트** — `skills/record/test_record_format.py` 가 dashboard 의 pin 흐름과 record 가 같은 포맷에 수렴함을 6개 케이스로 검증.
- **마켓플레이스 등록** — `.claude-plugin/marketplace.json` 의 skills 배열에 `./skills/record` 추가.
- 출처 설계: `docs/plans/2026-05-22-record-handoff-redesign.md` 의 Phase 0 + Phase 1 만 채택. Phase 2-5 (라우팅 가드 / 계층 메모리 / 3 청중 분리 / 자동화) 는 추후 별도 sub-project.
```

순서 확인 후 commit.

- [ ] **Step 3: Commit**

Run:
```powershell
git add README.md
git commit -m "docs(readme): add 2026-05-23 multi-platform handoff (/hams:record) changelog"
```

---

## Task 7 — 최종 그린 게이트

**Files:** (검증만)

- [ ] **Step 1: 전체 테스트 그린**

Run:
```powershell
python -m pytest hooks/ skills/record/ -v
```
Expected: 모든 테스트 PASS (hooks 18 + record 6 = 24).

- [ ] **Step 2: record 가 신규 스킬로 마켓플레이스에 등록되었는지 확인**

Run:
```powershell
python -c "import json; m=json.load(open('.claude-plugin/marketplace.json')); print('record registered' if './skills/record' in m['plugins'][0]['skills'] else 'MISSING')"
```
Expected: `record registered`.

- [ ] **Step 3: P6 (hook ≠ record) 검증 — 다른 스킬이 record 를 호출하지 않음**

Run:
```powershell
Select-String -Path "skills\*\SKILL.md","hooks\*.py" -Pattern "/hams:record|hams_record|skills/record/" -ErrorAction SilentlyContinue | Where-Object { $_.Path -notlike "*skills\record\*" }
```
Expected: 0 results. (record 만 자신을 정의, 다른 곳에선 참조 안 함.)

- [ ] **Step 4: No commit** — 다음 Task 로.

---

## Task 8 — Manual 검증 (Layer 3) + verification log

**Files:**
- Create: `docs/plans/2026-05-23-record-verification.md`

> 주의: 이 task 는 Claude Code CLI 세션에서 실제 `/hams:record` 슬래시 명령을 호출해 검증합니다. 슬래시 명령은 사용자가 새 CLI 세션에서 `/hams:record` 를 입력해야 트리거됩니다 — 이 plan 의 실행자가 동일 세션 안에서 자동 트리거하기 어렵습니다. 따라서 step 1-5 는 사용자 또는 검증자가 별도 CLI 세션에서 수행, step 6 은 Desktop 환경 접근자가 수행, 결과를 verification.md 에 기록.

- [ ] **Step 1: 사전 준비 — 검증용 임시 프로젝트**

Run (PowerShell):
```powershell
$VERIFY_DIR = "$env:TEMP\record-verify-$(Get-Random)"
New-Item -ItemType Directory -Path $VERIFY_DIR | Out-Null
cd $VERIFY_DIR
git init -q
echo "test" | Out-File -Encoding utf8 README.md
git add README.md; git commit -qm "init"
"VERIFY_DIR=$VERIFY_DIR"
```

생성된 `$VERIFY_DIR` 를 verification.md 에 기록.

- [ ] **Step 2: CLI 세션 시나리오 1 — 첫 record 호출**

새 Claude Code 세션을 `$VERIFY_DIR` 에서 시작. 더미 결정 한두 개를 만들 만큼 짧은 대화 후:

```
/hams:record
```

확인 단계에서 모든 후보 채택. 종료 후 verification.md 에 다음 결과 기록:
- [ ] `$VERIFY_DIR/.hamstern/boss-hamster/decisions.md` 가 생성됨
- [ ] `# 프로젝트 결정사항` 헤더 + `_마지막 업데이트:_` 라인 정상
- [ ] 채택한 결정이 카테고리별 섹션에 `- {결정} <!-- session: {id} -->` 형식으로 들어감
- [ ] `decisions-log.md` 가 생성되고 timestamp 블록이 정확히 1개 있음

- [ ] **Step 3: 시나리오 2 — 같은 세션에서 두 번째 record 호출 (idempotent)**

같은 세션에서 추가 결정을 한두 개 만들 만한 대화 후:

```
/hams:record
```

종료 후 결과 기록:
- [ ] `decisions.md` 가 갱신됨 (기존 항목 보존 + 신규 항목 추가 + 동일 session id 의 옛 항목은 갱신/중복 없음)
- [ ] `decisions-log.md` 에 timestamp 블록이 2개 됨 (append-only)

- [ ] **Step 4: 시나리오 3 — FS 쓰기 차단 시 텍스트 폴백**

PowerShell 에서 `.hamstern/boss-hamster/` 디렉토리 권한 차단 (또는 디렉토리를 일시 read-only 로 만들기):

```powershell
$acl = Get-Acl "$VERIFY_DIR\.hamstern\boss-hamster"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("$env:USERNAME","Write","Deny")
$acl.AddAccessRule($rule)
Set-Acl "$VERIFY_DIR\.hamstern\boss-hamster" $acl
```

다시 CLI 세션에서 `/hams:record` 호출. 종료 후:
- [ ] Claude 가 텍스트 폴백 메시지를 출력 (⚠️ + 동일 마크다운)
- [ ] `decisions.md` 의 mtime 이 차단 전과 동일 (실제 쓰기 안 됨)

권한 복원:
```powershell
$acl = Get-Acl "$VERIFY_DIR\.hamstern\boss-hamster"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("$env:USERNAME","Write","Deny")
$acl.RemoveAccessRule($rule) | Out-Null
Set-Acl "$VERIFY_DIR\.hamstern\boss-hamster" $acl
```

- [ ] **Step 5: 시나리오 4 — dashboard 호환성**

같은 `$VERIFY_DIR` 에서:

```
/hams:dashboard
```

브라우저가 열리면 Decisions 탭에서:
- [ ] record 가 쓴 항목들이 카테고리별로 정상 표시
- [ ] dashboard 의 ✅ 핀 흐름으로 새 항목을 추가해도 record 가 쓴 항목과 충돌 없음

- [ ] **Step 6: 시나리오 5 — /hams:remind 환기**

```
/hams:remind
```

종료 후:
- [ ] `decisions.md` 본문이 응답에 그대로 출력됨
- [ ] 카테고리·항목 형식이 사람이 읽기에 자연스러움

- [ ] **Step 7: 시나리오 6 — Claude Desktop App 환경 (옵션)**

Desktop App 환경 접근이 가능하면:
1. Anthropic Claude Desktop 에서 새 대화 시작
2. `/hams:record` 호출 시도

가능한 결과 분기:
- (A) Desktop 이 record 슬래시 명령을 인식하고 실행 → Step 1 의 FS-try 가 발화. 결과 기록.
- (B) Desktop 이 슬래시 명령을 인식하지만 Bash/Write 도구가 sandbox 차단 → Step 5 텍스트 폴백 발화. 결과 기록.
- (C) Desktop 이 슬래시 명령 자체를 인식 못 함 → spec 의 가정과 다름. 결과 기록 + 후속 task 분리 (Desktop 호환성 재설계).

Desktop 환경 접근 불가하면 이 step 은 **명시적 후속 task 로 분리** — verification.md 에 "Desktop 검증 보류, 사용자 첫 사용 시점에 실행" 기록.

- [ ] **Step 8: 검증 정리**

Run:
```powershell
cd C:\Users\ssarm\workspace\hamstern\hamstern-plugin
Remove-Item -Recurse -Force $VERIFY_DIR -ErrorAction SilentlyContinue
```

- [ ] **Step 9: Write `docs/plans/2026-05-23-record-verification.md`**

Create the file with this template, filling each ✅/❌ from actual results:

```markdown
# /hams:record Verification — 2026-05-23

> Sub-project B (`docs/discussions/2026-05-23-multi-platform-handoff-design.md`) 의 Task 8 검증.
> 환경: Windows 11 / PowerShell / Python 3.x / 임시 디렉토리 `$env:TEMP\record-verify-{random}`

## 시나리오 결과

| # | 시나리오 | 결과 | 비고 |
|---|----------|------|------|
| 1 | 첫 record 호출 → decisions.md + decisions-log.md 생성 | ✅ / ❌ | |
| 2 | 같은 세션 두 번째 호출 → 갱신 (중복 X) + log append | ✅ / ❌ | |
| 3 | FS 쓰기 차단 → 텍스트 폴백 출력 | ✅ / ❌ | |
| 4 | dashboard 가 record 항목 정상 표시 | ✅ / ❌ | |
| 5 | /hams:remind 가 record 의 decisions.md 환기 | ✅ / ❌ | |
| 6 | Claude Desktop App 환경 | ✅ / ❌ / 보류 | (A) FS-try OK / (B) 텍스트 폴백 / (C) 슬래시 미인식 |

## 발견된 후속 작업

- (없음 / 또는 각 실패 항목별 후속 task 후보)

## 결론

(전체 흐름 무결성 평가 — 1-2 문장. Desktop 검증이 보류면 그것도 명시.)
```

- [ ] **Step 10: Commit verification log**

Run:
```powershell
git add docs/plans/2026-05-23-record-verification.md
git commit -m "test(verify): /hams:record CLI scenarios + Desktop note"
```

---

## Definition of Done

- [ ] Task 1–7 의 모든 step 완료, `python -m pytest hooks/ skills/record/ -v` 그린 (24/24)
- [ ] Task 8 의 verification.md 에 시나리오 1-5 (CLI) 결과 기록, 시나리오 6 (Desktop) 결과 또는 보류 명시
- [ ] `python -c "import json; m=json.load(open('.claude-plugin/marketplace.json')); print('./skills/record' in m['plugins'][0]['skills'])"` → `True`
- [ ] `Select-String -Path "skills\*\SKILL.md","hooks\*.py" -Pattern "/hams:record|skills/record/" | Where-Object { $_.Path -notlike "*skills\record\*" }` 결과 0 건 (P6 hook ≠ record 검증)
- [ ] git log 에 신규 commit 7개 (Tasks 1, 2, 3, 4, 6, 8 = 6개; Task 5, 7 = no commit; Task 8 의 verification = +1)

## Out of Scope

- Phase 2: `why`/`rule` 라우팅 가드
- Phase 3: 결정 저장소 hot/cold 계층화 + 강등
- Phase 4: `chat` 신규 스킬, `diary` 홈 경로 이동
- Phase 5: 자동화 (transcript-watcher 데몬 등)
- hooks 자체 추가 변경
- 글로벌 영역 (`~/.hamstern/`, `~/.claude/hams-diary.json`)
