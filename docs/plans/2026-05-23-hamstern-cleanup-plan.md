# Hamstern Plugin Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sub-project A 의 spec (`docs/discussions/2026-05-23-hamstern-cleanup-design.md`) 을 단계별로 실행한다 — cmux 잔재·중복 코드·orphan 파일을 제거하고 `_gate.py` 로 통합한 뒤, 대시보드의 baby→mom→decisions 흐름을 실제로 검증한다.

**Architecture:** TDD 우선. 새로운 `is_deeptalk_running()` 함수를 `_gate.py` 에 추가 → `user_prompt.py` / `stop.py` 가 import 로 단일 진실 출처를 사용 → cmux 관련 코드·테스트·문서 일괄 삭제 → 대시보드 6단계 manual 검증. 작업 단위로 commit.

**Tech Stack:** Python 3 stdlib only (hooks + `server.py` 모두), pytest (테스트), bash/PowerShell (검증 명령), git (commit 단위).

**Spec:** `docs/discussions/2026-05-23-hamstern-cleanup-design.md` (commit `c8a6546`)

---

## File Structure

**수정 대상 파일 (12개)**

| 파일 | 책임 | 변경 |
|------|------|------|
| `hooks/_gate.py` | 프로젝트-스코핑 + 노이즈 필터 게이트 (canonical) | `is_deeptalk_running()` 추가 |
| `hooks/user_prompt.py` | UserPromptSubmit hook 진입점 | `is_app_running` 삭제, `is_deeptalk_running` 을 `_gate` import 로 |
| `hooks/stop.py` | Stop hook 진입점 | `is_app_running` 삭제, `is_deeptalk_running` 을 `_gate` import 로 |
| `hooks/test_gate.py` | _gate 단위 테스트 | `is_deeptalk_running` 케이스 3개 추가 |
| `hooks/test_baby_record.py` | hook 행동 테스트 | `test_user_prompt_skipped_when_app_running` 삭제 |
| `hooks/test_all_hooks_gated.py` | 게이팅 통합 테스트 | (변경 없음 — cmux 케이스가 별도로 있지 않음) |
| `hooks/migrate_claude_md.py` | (orphan) | **삭제** |
| `hooks/test_migrate_claude_md.py` | migrate 테스트 | **삭제** |
| `skills/dashboard/dashboard.sh` | (죽은 cmux 호출) | **삭제** |
| `skills/dashboard/SKILL.md` | 대시보드 사용 안내 | 41 줄 cmux 언급 정정 |
| `skills/audit-decisions/SKILL.md` | 결정 재검토 안내 | 64–84 줄 example 블록 재작성 |
| `README.md` | 사용자 README | 50–57 줄 cmux 섹션 삭제 + 신규 changelog 추가 |

**검증 산출물 (1개 신규)**
- `docs/plans/2026-05-23-cleanup-verification.md` — Task 8 의 검증 체크리스트 결과

---

## 사전 점검 (Task 0)

- [ ] **Step 0.1: 현재 테스트 그린 상태 확인 (baseline)**

Run (PowerShell):
```powershell
cd C:\Users\ssarm\workspace\hamstern\hamstern-plugin
python -m pytest hooks/ -v
```
Expected: 모든 테스트 통과. 만약 빨간 케이스가 있으면 그것은 cleanup 작업과 무관한 사전 결함 — 사용자에게 보고하고 작업 보류.

- [ ] **Step 0.2: 작업 브랜치 확인**

Run:
```powershell
git status
git branch --show-current
```
Expected: clean working tree, `main` 브랜치 (혹은 사용자가 명시한 작업 브랜치).

---

## Task 1 — `_gate.py` 에 `is_deeptalk_running()` 추가 (TDD)

**Files:**
- Modify: `hooks/test_gate.py` (테스트 3개 추가)
- Modify: `hooks/_gate.py` (함수 추가, time/os import)

- [ ] **Step 1: Write failing test in `hooks/test_gate.py`**

`hooks/test_gate.py` 마지막에 다음 3개 테스트를 추가 (파일 끝에 append):

```python


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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
python -m pytest hooks/test_gate.py -v -k deeptalk
```
Expected: 3개 케이스 모두 FAIL with `ImportError: cannot import name 'is_deeptalk_running' from '_gate'`.

- [ ] **Step 3: Add `is_deeptalk_running()` to `hooks/_gate.py`**

`hooks/_gate.py` 의 import 섹션 (line 12-14) 을 다음으로 교체:

```python
import os
import re
import time
from pathlib import Path
from typing import Optional
```

그 다음, 파일 맨 끝 (line 55 이후) 에 다음 함수를 추가:

```python


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
```

- [ ] **Step 4: Run test to verify all 3 pass**

Run:
```powershell
python -m pytest hooks/test_gate.py -v -k deeptalk
```
Expected: 3 PASS.

- [ ] **Step 5: Run full gate test suite**

Run:
```powershell
python -m pytest hooks/test_gate.py -v
```
Expected: 모든 테스트 (기존 7 + 신규 3 = 10) PASS.

- [ ] **Step 6: Commit**

Run:
```powershell
git add hooks/_gate.py hooks/test_gate.py
git commit -m "feat(gate): extract is_deeptalk_running() to _gate.py with stale-marker auto-cleanup"
```

---

## Task 2 — `user_prompt.py` / `stop.py` 가 `_gate.is_deeptalk_running` 사용 + cmux 제거

**Files:**
- Modify: `hooks/user_prompt.py` (line 6 import, lines 9-29 함수 둘 삭제, line 32 분기 단순화)
- Modify: `hooks/stop.py` (line 5 import, lines 48-64 함수 둘 삭제, line 67 분기 단순화)
- Modify: `hooks/test_baby_record.py` (line 16-25 케이스 삭제)

- [ ] **Step 1: Update `hooks/user_prompt.py` — import + 두 함수 삭제 + 분기 단순화**

`hooks/user_prompt.py` 의 line 6 (현재 `from _gate import is_hamstern_project, is_noise_command`) 을 다음으로 교체:

```python
from _gate import is_hamstern_project, is_noise_command, is_deeptalk_running
```

그 다음, line 9-29 의 `is_app_running` 과 `is_deeptalk_running` 두 함수 정의를 모두 **삭제**. 즉 line 9 부터 line 29 까지 (양쪽 함수 포함, 사이 빈 줄도) 전부 제거. 그러면 line 31 의 `def record_prompt(...)` 가 line 8 다음 (한 줄 빈 줄 둔 뒤) 바로 오게 됨.

그리고 line 32 (현재 `if is_app_running(cwd) or is_deeptalk_running(cwd):`) 을 다음으로 교체:

```python
    if is_deeptalk_running(cwd):
```

최종 `hooks/user_prompt.py` 전체가 다음과 같아야 함:

```python
import sys, json, re
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from _gate import is_hamstern_project, is_noise_command, is_deeptalk_running


def record_prompt(session_id: str, cwd: str, prompt: str) -> None:
    if is_deeptalk_running(cwd):
        return
    if is_noise_command(prompt):
        return
    baby_dir = Path(cwd) / ".hamstern" / "baby-hamster"
    baby_dir.mkdir(parents=True, exist_ok=True)
    baby = baby_dir / f"session_{session_id}.md"
    if not baby.exists():
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        baby.write_text(
            f"---\nsession_id: {session_id}\nstarted_at: {ts}\ncwd: {cwd}\nsource: plugin-hook\n---\n",
            encoding="utf-8",
        )
    content = baby.read_text(encoding="utf-8")
    turn = len(re.findall(r"^## Turn", content, re.MULTILINE)) + 1
    baby.write_text(content + f"\n## Turn {turn}\n**User:** {prompt}\n", encoding="utf-8")

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    cwd = data.get("cwd", ".")
    if not is_hamstern_project(cwd):
        return
    record_prompt(
        session_id=data.get("session_id", "unknown"),
        cwd=cwd,
        prompt=data.get("prompt", ""),
    )

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Update `hooks/stop.py` — import + 두 함수 삭제 + 분기 단순화**

`hooks/stop.py` 의 line 5 (현재 `from _gate import is_hamstern_project, is_noise_command`) 을 다음으로 교체:

```python
from _gate import is_hamstern_project, is_noise_command, is_deeptalk_running
```

그 다음, line 48-64 의 `is_app_running` 과 `is_deeptalk_running` 두 함수 정의를 모두 **삭제** (사이 빈 줄도 함께).

그리고 line 67 (현재 `if is_app_running(cwd) or is_deeptalk_running(cwd):`) 을 다음으로 교체:

```python
    if is_deeptalk_running(cwd):
```

`hooks/stop.py` 의 나머지 부분 (line 1-46 의 import / _trigger_aggregate / _latest_user_prompt, line 66 이후의 record_stop 본문 / main) 은 **그대로 유지**.

확인용 — 수정 후 `hooks/stop.py` 의 상단/중간 핵심 부분이 이렇게 보여야 함:

```python
import sys, json, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _gate import is_hamstern_project, is_noise_command, is_deeptalk_running

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
AGGREGATE_SCRIPT = PLUGIN_ROOT / "skills" / "dashboard" / "scripts" / "aggregate.py"


def _trigger_aggregate(cwd: str) -> None:
    ...  # 기존 코드 유지

def _latest_user_prompt(transcript_path: str) -> str:
    ...  # 기존 코드 유지

def record_stop(session_id: str, cwd: str, transcript_path: str) -> None:
    if is_deeptalk_running(cwd):
        return
    if is_noise_command(_latest_user_prompt(transcript_path)):
        return
    ...  # 나머지 본문 그대로
```

- [ ] **Step 3: Delete cmux test case in `hooks/test_baby_record.py`**

`hooks/test_baby_record.py` 의 line 16-25 (전체 `test_user_prompt_skipped_when_app_running` 함수 + 다음 빈 줄) 을 통째로 **삭제**.

삭제 후 파일 상단 (line 1-16) 이 다음과 같아야 함:

```python
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
    ...  # 기존 그대로 (이전 line 27부터)
```

(즉 기존 line 27 의 `test_user_prompt_appends_turns` 가 line 16 위치로 올라옴.)

- [ ] **Step 4: Run full hooks test suite**

Run:
```powershell
python -m pytest hooks/ -v --ignore=hooks/test_migrate_claude_md.py
```
Expected: 모든 테스트 PASS. (`test_migrate_claude_md.py` 는 Task 4 에서 삭제하므로 일단 ignore.)

- [ ] **Step 5: Sanity grep — hooks 에 cmux/app-running 흔적 없음 확인**

Run (PowerShell):
```powershell
Select-String -Path "hooks\*.py" -Pattern "cmux|app[-_]running|is_app_running" -CaseSensitive:$false
```
Expected: 결과 0 건.

- [ ] **Step 6: Commit**

Run:
```powershell
git add hooks/user_prompt.py hooks/stop.py hooks/test_baby_record.py
git commit -m "refactor(hooks): use _gate.is_deeptalk_running, remove cmux .app-running gate"
```

---

## Task 3 — `dashboard.sh` 삭제

**Files:**
- Delete: `skills/dashboard/dashboard.sh`

- [ ] **Step 1: Confirm no caller references the script**

Run (PowerShell, repo 루트에서):
```powershell
Select-String -Path "**\*" -Pattern "dashboard\.sh" -CaseSensitive:$false -ErrorAction SilentlyContinue
```
Expected: 결과는 이 plan 문서 + spec 문서 외에 없어야 함. (코드/SKILL.md/marketplace.json/README 등 어디서도 참조 안 함.)

만약 다른 참조가 발견되면 그것을 먼저 정리 (예상 외 발견 시 사용자에게 보고).

- [ ] **Step 2: Delete the file**

Run:
```powershell
git rm skills/dashboard/dashboard.sh
```

- [ ] **Step 3: Commit**

Run:
```powershell
git commit -m "chore(dashboard): remove dead dashboard.sh (cmux binary launcher, never referenced)"
```

---

## Task 4 — `migrate_claude_md.py` + 테스트 삭제

**Files:**
- Delete: `hooks/migrate_claude_md.py`
- Delete: `hooks/test_migrate_claude_md.py`

- [ ] **Step 1: Confirm no caller references migrate_claude_md**

Run (PowerShell):
```powershell
Select-String -Path "hooks\*.py","skills\**\*.md","skills\**\*.py","*.md",".claude-plugin\*.json" -Pattern "migrate_claude_md" -ErrorAction SilentlyContinue
```
Expected: 결과는 이 plan 문서, spec 문서, README 의 changelog 외에 없어야 함.

만약 라이브 코드/스킬에서 참조가 발견되면 사용자에게 보고하고 보류.

- [ ] **Step 2: Delete both files**

Run:
```powershell
git rm hooks/migrate_claude_md.py hooks/test_migrate_claude_md.py
```

- [ ] **Step 3: Run full hooks test suite**

Run:
```powershell
python -m pytest hooks/ -v
```
Expected: 모든 테스트 PASS (migrate 테스트 사라진 채로 그린).

- [ ] **Step 4: Commit**

Run:
```powershell
git commit -m "chore(hooks): remove orphan migrate_claude_md.py and its test (never wired up)"
```

---

## Task 5 — SKILL.md 정정 (cmux 언급 제거)

**Files:**
- Modify: `skills/dashboard/SKILL.md` (line 41)
- Modify: `skills/audit-decisions/SKILL.md` (line 64-84 example 블록)

- [ ] **Step 1: Update `skills/dashboard/SKILL.md` line 41**

현재 line 41:
```
Stop hook이 cmux/deeptalk 활성으로 bail했거나, 세션이 비정상 종료된 경우 수동 집계:
```

다음으로 교체:
```
Stop hook이 deeptalk 활성으로 bail했거나, 세션이 비정상 종료된 경우 수동 집계:
```

- [ ] **Step 2: Replace cmux example in `skills/audit-decisions/SKILL.md`**

현재 line 64-84 의 example 블록 (`📌 결정사항: "HTTP 대시보드 서버 구현"` 부터 `[유지] — 이대로 진행` 까지) 을 다음으로 교체:

````markdown
```
📌 결정사항: "외부 도구 양보 메커니즘 유지"
├─ 카테고리: architecture
├─ 배경: (context.md에서 추출)
└─ 타당성: ⬛⬜⬜⬜⬜ (1/5) — 매우 낮음

분석:
  ❌ 폐기 추천:
  - 이 양보 메커니즘이 가정했던 외부 도구 (예: macOS 전용 동반 앱) 가
    사용자 환경에 더 이상 존재하지 않습니다.
  - 양보 로직이 남아 있으면 hook 동작을 무음으로 만들 수 있어
    디버깅을 어렵게 합니다.
  - 폐기하려면:
    1. 마커 체크 분기 제거
    2. 관련 테스트 케이스 정리
  - 유지하려면:
    1. 양보 대상 도구의 실제 사용 사례 1개 이상 제시

[폐기 승인] — 이 결정을 지우겠습니다 (⚠️ 돌이킬 수 없음)
[보류] — 더 생각해본 후 나중에
[유지] — 이대로 진행
```
````

(블록 구조·이모지·라벨은 위·아래의 example 와 동일한 패턴 유지. 내용만 cmux 무관한 일반 시나리오로 교체.)

이어서 line 100-105 의 폐기 시 최종 확인 블록 안의 결정사항 라벨도 정정:

현재:
```
📌 "HTTP 대시보드 서버 구현"
   (context에서 폐기된 이유 표시)
```

다음으로 교체:
```
📌 "외부 도구 양보 메커니즘 유지"
   (context에서 폐기된 이유 표시)
```

- [ ] **Step 3: Sanity grep**

Run (PowerShell):
```powershell
Select-String -Path "skills\dashboard\SKILL.md","skills\audit-decisions\SKILL.md" -Pattern "cmux"
```
Expected: 결과 0 건.

- [ ] **Step 4: Commit**

Run:
```powershell
git add skills/dashboard/SKILL.md skills/audit-decisions/SKILL.md
git commit -m "docs(skills): drop cmux references from dashboard and audit-decisions SKILL.md"
```

---

## Task 6 — README 정리

**Files:**
- Modify: `README.md` (line 50-57 삭제, 상단 changelog 신규 항목 추가)

- [ ] **Step 1: Delete lines 50-57 ("cmux 툴 (macOS) 과의 공존" 섹션)**

`README.md` 의 line 50 부터 line 57 까지 (heading `## cmux 툴 (macOS) 과의 공존` 부터 빈 줄 포함 `데이터·CLAUDE.md 가 두 군데서 동시에 쓰여 충돌하는 일 없음.` 다음 빈 줄까지) 통째로 삭제.

삭제 후 line 48 의 `/hams:start` 코드 블록 끝 (` ``` `) 다음에 빈 줄 한 줄 두고 바로 line 59 의 `---` 구분선이 오도록.

- [ ] **Step 2: Add new changelog entry at the top of "📝 변경 내역"**

`README.md` 의 `## 📝 변경 내역 (Changelog)` 헤더 (현재 line 403) 바로 아래, 첫 번째 changelog 항목 (`### 2026-04-27 — strip_giscus.py ...`) **위에** 다음 신규 항목 삽입:

```markdown
### 2026-05-23 — cmux 잔재 제거 + hooks 중복 정리 + 대시보드 검증

- **cmux 양보 메커니즘 (`.app-running` 마커) 완전 제거** — cmux 가 macOS 전용 동반 앱이고 사용자 환경에서 사용 안 함. `hooks/user_prompt.py` / `hooks/stop.py` 양쪽의 `is_app_running()` 함수 + 분기 삭제. `skills/dashboard/dashboard.sh` (cmux 바이너리 호출용 죽은 스크립트) 삭제.
- **`is_deeptalk_running()` 을 `hooks/_gate.py` 로 단일화** — 양쪽 hook 에 복붙되어 있던 함수를 게이트 모듈로 추출. 두 곳에서 동작이 미묘하게 달랐던 stale-marker auto-cleanup 차이도 자연 해소.
- **orphan `migrate_claude_md.py` + 테스트 삭제** — 1개월간 어디서도 호출 안 됨. 옛 CLAUDE.md 의 `<!-- hamstern:decisions:start --> ... <!-- hamstern:decisions:end -->` 잔존 마커는 수동 삭제 필요 (대다수 사용자는 이미 정리됨).
- **대시보드 작동 검증** — `python3 skills/dashboard/server.py --port 7777 --project {cwd}` 흐름 + `baby → mom → boss → /hams:remind` 핸드오프 무결성 6단계 manual 검증 완료. 결과: `docs/plans/2026-05-23-cleanup-verification.md`.
- **SKILL.md 정합성 정정** — `skills/dashboard/SKILL.md` 의 cmux 언급 제거, `skills/audit-decisions/SKILL.md` 의 cmux example 을 일반 시나리오로 교체.
```

- [ ] **Step 3: Verify README 가 문법적으로 OK**

Run (PowerShell):
```powershell
Select-String -Path "README.md" -Pattern "cmux" | Where-Object { $_.LineNumber -lt 400 }
```
Expected: 결과 0 건 (changelog 영역 400+ 줄에 과거 history 는 남아 있을 수 있음 — 그것은 의도된 history 유지).

- [ ] **Step 4: Commit**

Run:
```powershell
git add README.md
git commit -m "docs(readme): remove cmux coexistence section, add 2026-05-23 cleanup changelog"
```

---

## Task 7 — 최종 정합성 그린 게이트

**Files:** (검증만)

- [ ] **Step 1: Run full hooks test suite**

Run:
```powershell
python -m pytest hooks/ -v
```
Expected: 모든 테스트 PASS, 빨간 케이스 0.

- [ ] **Step 2: Repo-wide cmux/app-running grep**

Run (PowerShell):
```powershell
Select-String -Path "hooks\*.py","skills\**\*.py","skills\**\*.md","skills\**\*.sh",".claude-plugin\*.json" -Pattern "cmux|app[-_]running" -CaseSensitive:$false -ErrorAction SilentlyContinue
```
Expected: 결과 0 건. (README 의 changelog 과거 history 와 `docs/discussions/` 의 spec 문서는 별도 — 위 path glob 에서 제외됨.)

만약 결과가 있으면, 해당 위치를 사용자에게 보고하고 조치 후 재실행.

- [ ] **Step 3: No commit (검증만)** — 다음 Task 로 진행.

---

## Task 8 — 대시보드 작동 검증 (Manual + Smoke)

**Files:**
- Create: `docs/plans/2026-05-23-cleanup-verification.md` (검증 결과 노트)

> 주의: 이 task 는 사용자 환경에서 실행되는 manual 검증입니다. 각 step 의 명령을 직접 실행하고 결과를 기록합니다. 실패 항목은 verification.md 에 기록 후 후속 task 로 분리 (이 cleanup plan 의 범위는 "검증" 까지 — 신규 버그 수정은 별 sub-project).
>
> **세션 일관성**: `$VERIFY_DIR` 와 `$SERVER_PID` 는 PowerShell 변수라 새 창을 열면 사라집니다. Step 1-9 를 **하나의 PowerShell 세션** 에서 실행하거나, Step 1 에서 경로를 텍스트 파일 (`$env:TEMP\verify_dir.txt`) 에 기록하고 후속 step 에서 `$VERIFY_DIR = Get-Content $env:TEMP\verify_dir.txt` 로 복원하세요.

- [ ] **Step 1: 사전 준비 — 테스트용 임시 프로젝트 디렉토리**

Run (PowerShell):
```powershell
$VERIFY_DIR = "$env:TEMP\hamstern-verify-$(Get-Random)"
New-Item -ItemType Directory -Path $VERIFY_DIR | Out-Null
New-Item -ItemType Directory -Path "$VERIFY_DIR\.hamstern\baby-hamster" -Force | Out-Null
New-Item -ItemType Directory -Path "$VERIFY_DIR\.hamstern\mom-hamster" -Force | Out-Null
New-Item -ItemType Directory -Path "$VERIFY_DIR\.hamstern\boss-hamster" -Force | Out-Null
@"
---
session_id: TEST
started_at: 2026-05-23T00:00:00
cwd: $VERIFY_DIR
source: verification
---

## Turn 1
**User:** 검증용 더미 prompt — baby → mom → boss 흐름 테스트
**Claude:** 검증용 더미 응답.
"@ | Set-Content -Encoding utf8 -Path "$VERIFY_DIR\.hamstern\baby-hamster\session_TEST.md"
echo "VERIFY_DIR=$VERIFY_DIR"
```

생성된 `$VERIFY_DIR` 경로를 verification.md 에 기록.

- [ ] **Step 2: 서버 기동 (background, PID 캡쳐)**

Run (같은 PowerShell 세션에서):
```powershell
$proc = Start-Process -PassThru -WindowStyle Hidden -FilePath python `
    -ArgumentList "C:\Users\ssarm\workspace\hamstern\hamstern-plugin\skills\dashboard\server.py","--port","7777","--project",$VERIFY_DIR
$SERVER_PID = $proc.Id
Start-Sleep -Seconds 2
"SERVER_PID=$SERVER_PID"
```
Expected: PID 한 줄 출력.

확인:
```powershell
Test-NetConnection -ComputerName localhost -Port 7777 -WarningAction SilentlyContinue | Select-Object TcpTestSucceeded
```
Expected: `TcpTestSucceeded : True`. 만약 False 면 서버 기동 실패 — `Get-Content` 로 stdout 확인할 수 없으므로, `Start-Process` 대신 새 창에서 foreground 로 띄워서 에러 메시지 확인 후 재시도.

- [ ] **Step 3: 5개 GET 엔드포인트 200 응답 검증**

Run (PowerShell — 별도 창에서):
```powershell
foreach ($p in '/','/api/baby','/api/mom','/api/decisions','/api/analyze/status') {
    $r = Invoke-WebRequest -Uri "http://localhost:7777$p" -UseBasicParsing
    "{0,-25} {1}" -f $p, $r.StatusCode
}
```
Expected: 5개 모두 `200`.

verification.md 에 결과 표 기록.

- [ ] **Step 4: baby 파일 인식 검증**

Run:
```powershell
(Invoke-WebRequest -Uri "http://localhost:7777/api/baby" -UseBasicParsing).Content | ConvertFrom-Json
```
Expected: `files` 배열에 `session_TEST.md` 1개 항목이 있고 `content` 에 "검증용 더미 prompt" 문자열 포함.

- [ ] **Step 5: mom 집계 트리거**

Run:
```powershell
python skills\dashboard\scripts\aggregate.py $VERIFY_DIR
```
Expected: 종료 코드 0. 이후 `$VERIFY_DIR\.hamstern\mom-hamster\mom.md` 파일이 생성되어 있고 비어있지 않음.

```powershell
Get-Content "$VERIFY_DIR\.hamstern\mom-hamster\mom.md" | Select-Object -First 20
```
Expected: 의미 있는 집계 본문 (최소한 session_TEST 의 turn 1 본문 일부 포함).

만약 `aggregate.py` 가 실패하거나 빈 mom.md 를 만들면 → verification.md 에 "FAIL — mom 집계 동작 불량" 기록 + 후속 task 후보 등록 + 다음 step 으로 진행.

- [ ] **Step 6: decisions.md 확정 경로 검증**

Run (POST 시뮬레이션):
```powershell
$body = @{
    decision = "검증 더미 결정"
    category = "Architecture"
    background = "verification step 6"
    source_session = "TEST"
} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:7777/api/pin/boss" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing
```
Expected: `{"status": "ok"}` 응답.

```powershell
Get-Content "$VERIFY_DIR\.hamstern\boss-hamster\decisions.md"
```
Expected: `# 프로젝트 결정사항` 헤더 + `## Architecture` 섹션 + `- 검증 더미 결정` 항목 포함.

- [ ] **Step 7: `/hams:remind` 환기 경로 검증 (간이)**

`/hams:remind` 는 단순히 `decisions.md` 내용을 출력하는 skill 이므로, 직접 파일 가독성으로 갈음:

```powershell
Get-Content "$VERIFY_DIR\.hamstern\boss-hamster\decisions.md" | Out-String
```
Expected: Step 6 에서 기록한 결정사항이 그대로 읽힘.

verification.md 에 "/hams:remind 가 읽을 본문이 정상 생성됨" 기록.

- [ ] **Step 8: 서버 종료 + 검증 디렉토리 정리**

Run:
```powershell
Stop-Process -Id $SERVER_PID -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $VERIFY_DIR
```

- [ ] **Step 9: Write `docs/plans/2026-05-23-cleanup-verification.md`**

`docs/plans/2026-05-23-cleanup-verification.md` 신규 파일을 작성하고, Step 1–7 의 결과를 다음 체크리스트 형태로 기록:

```markdown
# Hamstern Plugin Cleanup Verification — 2026-05-23

> Sub-project A (`docs/discussions/2026-05-23-hamstern-cleanup-design.md`) 의 Task 8 검증 결과.
> 실행 환경: Windows / PowerShell / Python 3.x

## 검증 결과

| # | 항목 | 결과 | 비고 |
|---|------|------|------|
| 1 | 임시 디렉토리 + baby 더미 파일 생성 | ✅ / ❌ | $VERIFY_DIR 경로 |
| 2 | `server.py --port 7777` 기동 + listening | ✅ / ❌ | |
| 3 | GET / · /api/baby · /api/mom · /api/decisions · /api/analyze/status → 200 | ✅ / ❌ | |
| 4 | /api/baby 가 session_TEST.md 인식 | ✅ / ❌ | |
| 5 | aggregate.py → mom.md 생성 | ✅ / ❌ | |
| 6 | POST /api/pin/boss → decisions.md 기록 | ✅ / ❌ | |
| 7 | decisions.md 내용 가독 (/hams:remind 환기 본문) | ✅ / ❌ | |

## 발견된 후속 작업 (실패 항목이 있을 시)

- (없음 / 또는 각 항목별 후속 task 후보)

## 결론

(전체 흐름 무결성 평가 — 1-2 문장)
```

각 줄의 `✅ / ❌` 를 실제 결과로 교체.

- [ ] **Step 10: Commit verification log**

Run:
```powershell
git add docs/plans/2026-05-23-cleanup-verification.md
git commit -m "test(verify): dashboard baby->mom->boss handoff verification log"
```

---

## Definition of Done

- [ ] Task 1–7 의 모든 step 완료, `python -m pytest hooks/ -v` 그린
- [ ] Task 8 의 verification.md 에 6단계 결과 기록, 실패 항목이 있으면 후속 task 후보로 명시
- [ ] `Select-String -Path "hooks\*.py","skills\**\*.py","skills\**\*.md","skills\**\*.sh",".claude-plugin\*.json" -Pattern "cmux|app[-_]running"` 결과 0 건
- [ ] git log 에 8 개의 commit (Task 1, 2, 3, 4, 5, 6, 8 = 7개 + 0번 검증은 commit 없음; Task 6 의 README 가 단일 commit 이면 8개 미만일 수 있음 — 정확한 수는 실행 시 결정)

## Out of Scope (이 plan 에서 처리하지 않음)

- 룰 시스템 (`why` / `rule`) 의 통합/리팩토링
- diary 스킬의 accumulated complexity
- 멀티 플랫폼 도달성 (→ Sub-project B 별도 brainstorming)
- 글로벌 영역 (`~/.hamstern/`) 처리
- 새로운 기능 추가
- 대시보드 검증 중 발견된 신규 버그 수정 (→ 별도 후속 task 분리)
