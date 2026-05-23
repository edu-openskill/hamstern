# Record-Unified Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sub-project C spec (`docs/discussions/2026-05-23-record-unification-design.md`) 를 단계별로 실행 — hooks/start/stop/mom 전체 제거, record 의 atomic dual-write 추가, 자동 마이그레이션, 모든 의존 파일 path 갱신, README 재작성.

**Architecture:** 삭제(Phase A) → record 업데이트(Phase B) → 의존 파일 path 갱신(Phase C) → 검증(Phase D). 각 task = 한 commit. TDD: record 의 신규 로직은 test_record_format.py 에 의사 알고리즘 + 케이스로 회귀 보호.

**Tech Stack:** Python 3 stdlib (pytest), markdown (SKILL.md 들), bash/PowerShell (cleanup), git (commit 단위).

**Spec:** `docs/discussions/2026-05-23-record-unification-design.md` (commit `cff9270`)

---

## File Structure

**삭제 (전체 디렉토리/파일)**

| 경로 | 종류 |
|------|------|
| `hooks/` (전체 디렉토리) | `_gate.py`, `user_prompt.py`, `stop.py`, `test_gate.py`, `test_baby_record.py`, `test_all_hooks_gated.py`, `__pycache__/` |
| `skills/start/` (전체) | `SKILL.md` |
| `skills/stop/` (전체) | `SKILL.md` |
| `skills/dashboard/scripts/aggregate.py` | 파일 (`scripts/` 폴더는 빈 상태로 둠 — 향후 다른 스크립트 가능성) |

**수정 (path 갱신 + 본문 변경)**

| 파일 | 핵심 변경 |
|------|----------|
| `skills/record/SKILL.md` | Step 1 에 자동 마이그레이션 + Step 4 dual-write (sessions/{id}.md + decisions.md) |
| `skills/record/test_record_format.py` | dual-write 함수 + 마이그레이션 시뮬레이션 + 케이스 4개 추가 |
| `skills/remind/SKILL.md` | path: `boss-hamster/decisions.md` → `decisions.md`, `mom-hamster/mom.md` → 제거 (mom 모드 삭제) |
| `skills/audit-decisions/SKILL.md` | path: 위와 동일 + `baby-hamster/*.md` → `sessions/*.md` |
| `skills/dashboard/server.py` | `/api/mom` 라우트 삭제, `/api/analyze*` 라우트 삭제, `/api/baby` → `/api/sessions`, `_handle_boss_pin`/`_handle_boss_unpin` 의 path 갱신, `_handle_analyze` 함수 통째 삭제, `aggregate.py` 임포트 제거 |
| `skills/dashboard/static/index.html` | `/api/mom`/`/api/baby` fetch 갱신, mom 패널·analyze 버튼·card UI 제거, sessions 패널·decisions 패널·× 제거 버튼만 유지 |
| `skills/dashboard/SKILL.md` | mom 안내·aggregate 안내 삭제, baby → sessions 용어, "Stop hook 자동 갱신" 표현 제거 |
| `skills/deeptalk/SKILL.md` | `.deeptalk-running` 마커 set/unset 단계 (line 28-31, 84-85, 138-149) 삭제 |
| `skills/rule/SKILL.md` | `.deeptalk-running` 마커 set/unset 단계 (line 44-49, 75-78 근방) 삭제 |
| `skills/why/SKILL.md` | `.deeptalk-running` 마커 단계 삭제 (있다면) |
| `skills/skill-creator/SKILL.md` | `.deeptalk-running` 마커 단계 (line 39-43, 85-87, 102-107, 121-122) 삭제 |
| `docs/conventions.md` | 3-tier → 2-tier 전면 개정 (sessions/ + decisions.md, mom·boss·baby 명칭 제거) |
| `.claude-plugin/marketplace.json` | skills 배열에서 `./skills/start`, `./skills/stop` 두 항목 삭제 |
| `README.md` | "🔒 후크 활성화 조건" 섹션 (line 23-58) 통째 삭제, 신규 changelog 항목 추가 |

**신규 (1개)**

| 파일 | 책임 |
|------|------|
| `docs/plans/2026-05-23-record-unification-verification.md` | Task 11 manual 검증 결과 |

---

## Task 0 — 사전 점검

- [ ] **Step 0.1: Baseline 그린 확인**

Run (PowerShell):
```powershell
cd C:\Users\ssarm\workspace\hamstern\hamstern-plugin
python -m pytest hooks/ skills/record/ -q
```
Expected: `24 passed` (hooks 18 + record 6 from Sub-B).

- [ ] **Step 0.2: 작업 상태 확인**

Run:
```powershell
git status -sb
git branch --show-current
```
Expected: `main` 브랜치. Sub-A/B 의 dirty/untracked 파일 (`skills/why/SKILL.md` modified, `record-handoff-redesign.md` 등) 그대로 유지.

---

## Task 1 — 자동화 인프라 일괄 삭제 (hooks + start + stop + aggregate)

**Files:**
- Delete: `hooks/` (전체 디렉토리)
- Delete: `skills/start/` (전체)
- Delete: `skills/stop/` (전체)
- Delete: `skills/dashboard/scripts/aggregate.py`

이 task 는 단일 commit 으로 묶음 — 모두 "자동화 메커니즘 제거" 라는 동일 의도.

- [ ] **Step 1: 디렉토리/파일 일괄 삭제**

Run (PowerShell):
```powershell
git rm -r hooks/
git rm -r skills/start/
git rm -r skills/stop/
git rm skills/dashboard/scripts/aggregate.py
```

- [ ] **Step 2: scripts/ 디렉토리가 빈 상태인지 확인 + .gitkeep 추가 (선택)**

Run:
```powershell
Get-ChildItem skills/dashboard/scripts/ -ErrorAction SilentlyContinue
```

비어 있으면 (또는 디렉토리 자체가 사라졌으면) 그대로 진행. 향후 다른 스크립트가 들어갈 자리 보존 위해 명시적 `.gitkeep` 은 만들지 않음 (YAGNI — 필요해지면 그때 추가).

- [ ] **Step 3: 회귀 확인**

Run:
```powershell
python -m pytest skills/record/ -q
```
Expected: `6 passed`. hooks 테스트는 사라졌으니 더 이상 실행되지 않음.

- [ ] **Step 4: Commit**

```powershell
git commit -m "feat(simplify): remove hooks + start/stop skills + aggregate.py (Sub-C)"
```

---

## Task 2 — `.deeptalk-running` 마커 단계 제거 (4 SKILL.md)

**Files:**
- Modify: `skills/deeptalk/SKILL.md` (마커 set/unset 단계 + 마커 누수 안전망 섹션)
- Modify: `skills/rule/SKILL.md` (마커 set/unset 단계)
- Modify: `skills/why/SKILL.md` (마커 set/unset 단계 — 있다면)
- Modify: `skills/skill-creator/SKILL.md` (마커 set/unset 단계 + Common Mistakes 의 마커 언급)

hooks 가 사라졌으니 마커는 더 이상 baby-hamster 침묵 효과가 없다 (애초에 baby-hamster 도 사라짐). 마커 자체가 무의미해짐.

- [ ] **Step 1: `skills/deeptalk/SKILL.md` 편집**

해당 파일에서 다음 블록·라인 삭제 (정확한 라인은 시점 따라 변동 — 패턴으로 식별):

1. Step 0 근방의 마커 set:
   ```bash
   mkdir -p .hamstern && touch .hamstern/.deeptalk-running
   ```
   이 코드블록 + 직전 설명 1-2줄 함께 삭제.

2. 종료 절차의 마커 제거 step:
   ```
   1. 마커 제거: `rm -f .hamstern/.deeptalk-running`
   ```
   이 줄 + 같은 종료 절차 블록 안 다른 마커 언급도 함께 정리. 종료 절차 자체는 유지하되 마커 제거 부분만 빼고 후속 번호 재정렬.

3. "마커 누수 안전망" 섹션 (line 147 근방, `## 마커 누수 안전망` 헤더부터 그 다음 헤더 전까지) 통째 삭제.

수정 후 grep 으로 검증:
```powershell
Select-String -Path skills/deeptalk/SKILL.md -Pattern "deeptalk-running"
```
Expected: 0 results.

- [ ] **Step 2: `skills/rule/SKILL.md` 편집**

다음 블록 삭제 (line 44-49, 75-78 근방):
```bash
mkdir -p .hamstern && touch .hamstern/.deeptalk-running   # 시작
# ...작업...
rm -f .hamstern/.deeptalk-running                          # 종료 (성공/취소/오류 모두)
```

그리고 단독 등장하는 다음 패턴도:
```bash
mkdir -p .hamstern && touch .hamstern/.deeptalk-running
```

수정 후 grep:
```powershell
Select-String -Path skills/rule/SKILL.md -Pattern "deeptalk-running"
```
Expected: 0 results.

- [ ] **Step 3: `skills/why/SKILL.md` 편집 (있다면)**

`Select-String -Path skills/why/SKILL.md -Pattern "deeptalk-running"` 로 매치 확인. 매치가 있으면 위와 동일 패턴으로 삭제. 매치가 없으면 이 step 은 no-op.

> 주의: `skills/why/SKILL.md` 는 무관한 사용자 작업이 이미 dirty 상태로 진행 중일 수 있음. 수정 시 기존 변경과 충돌하지 않게, `.deeptalk-running` 관련 줄만 정확히 식별해서 삭제.

- [ ] **Step 4: `skills/skill-creator/SKILL.md` 편집**

다음 위치 정리:
- line 39-43 근방의 마커 set 블록 통째 삭제 (Step 0 인스트럭션)
- line 85-87 의 취소 분기 마커 제거 명령 → "취소 — 종료. 아무것도 저장하지 않음." 으로 단순화
- line 102-107 의 "Step 6 마커 제거 (필수, 모든 종료 경로 공통)" 블록 통째 삭제
- line 121-122 의 Common Mistakes "`.deeptalk-running` 마커 정리 누락" 항목 통째 삭제

수정 후 grep:
```powershell
Select-String -Path skills/skill-creator/SKILL.md -Pattern "deeptalk-running"
```
Expected: 0 results.

- [ ] **Step 5: 전체 검증**

Run:
```powershell
Select-String -Path "skills\**\SKILL.md" -Pattern "deeptalk-running"
```
Expected: 0 results.

- [ ] **Step 6: Commit**

```powershell
git add skills/deeptalk/SKILL.md skills/rule/SKILL.md skills/skill-creator/SKILL.md
# why/SKILL.md 는 사용자 dirty 상태이므로 add 하지 않음. 만약 step 3 에서 본 sub-project 변경분만 별도로 stage 가능하면 git add -p 사용.
git commit -m "refactor(skills): drop .deeptalk-running marker (hooks removed in Sub-C)"
```

> 만약 `skills/why/SKILL.md` 에 마커 참조가 있고 사용자 dirty 변경과 분리하기 어려우면, 이 task 에서는 deeptalk/rule/skill-creator 만 정리하고 why 정리는 별도 commit 으로 사용자가 dirty 정리 후 수행 — 그 경우 verification.md 에 후속 task 로 기록.

---

## Task 3 — `.claude-plugin/marketplace.json` 갱신 (start/stop 제거)

**Files:**
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: skills 배열에서 `./skills/start`, `./skills/stop` 두 항목 제거**

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
        "./skills/deeptalk",
        "./skills/record"
      ]
    }
  ]
}
```

(13개 → 11개. 순서는 start, stop 제외하고 나머지 그대로.)

- [ ] **Step 2: JSON validation + skills count**

Run:
```powershell
python -c "import json; m = json.load(open('.claude-plugin/marketplace.json')); s = m['plugins'][0]['skills']; print('count:', len(s)); print('has start:', './skills/start' in s); print('has stop:', './skills/stop' in s); print('has record:', './skills/record' in s)"
```
Expected: `count: 11`, `has start: False`, `has stop: False`, `has record: True`.

- [ ] **Step 3: Commit**

```powershell
git add .claude-plugin/marketplace.json
git commit -m "feat(marketplace): drop start/stop skills (Sub-C — record handles lifecycle)"
```

---

## Task 4 — `skills/record/SKILL.md` 갱신 (마이그레이션 + dual-write)

**Files:**
- Modify: `skills/record/SKILL.md` — Step 1 본문 + Step 4 본문 + 다른 진입점과의 관계 섹션

가장 중요한 변경. record 가 단일 진입점으로 격상 + 자동 마이그레이션 + dual-write.

- [ ] **Step 1: SKILL.md 의 Step 1 (경로 해석 & 저장소 보장) 을 다음으로 교체**

기존 Step 1 본문 전체를 아래로 교체:

````markdown
### Step 1 — 경로 해석 + 자동 마이그레이션 + 저장소 보장

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT=$(pwd)
echo "resolved root: $ROOT"
```

사용자에게 resolved root 를 echo 해서 잘못된 경우 즉시 abort 가능하게 한다.

#### 자동 마이그레이션 (idempotent, 안전 백업)

옛 구조 (`baby-hamster/`, `mom-hamster/`, `boss-hamster/`) 가 존재하면 첫 record 호출 시 자동 이전:

```bash
NEEDS_MIGRATE=0
for d in baby-hamster mom-hamster boss-hamster; do
  [ -d "$ROOT/.hamstern/$d" ] && NEEDS_MIGRATE=1
done

if [ "$NEEDS_MIGRATE" = "1" ]; then
  TS=$(date -u +%Y%m%dT%H%M%S)
  BACKUP="$ROOT/.hamstern.bak.$TS"
  cp -r "$ROOT/.hamstern" "$BACKUP"
  echo "백업 생성: $BACKUP"

  mkdir -p "$ROOT/.hamstern/sessions"
  if [ -d "$ROOT/.hamstern/baby-hamster" ]; then
    mv "$ROOT/.hamstern/baby-hamster"/*.md "$ROOT/.hamstern/sessions/" 2>/dev/null
    rmdir "$ROOT/.hamstern/baby-hamster" 2>/dev/null
  fi
  if [ -f "$ROOT/.hamstern/boss-hamster/decisions.md" ]; then
    mv "$ROOT/.hamstern/boss-hamster/decisions.md" "$ROOT/.hamstern/decisions.md"
  fi
  if [ -f "$ROOT/.hamstern/boss-hamster/decisions-log.md" ]; then
    mv "$ROOT/.hamstern/boss-hamster/decisions-log.md" "$ROOT/.hamstern/decisions-log.md"
  fi
  rm -rf "$ROOT/.hamstern/mom-hamster" "$ROOT/.hamstern/boss-hamster" 2>/dev/null
  echo "마이그레이션 완료. 옛 데이터는 $BACKUP 에 보존."
fi
```

마이그레이션 실패 시 (권한 등) record 진행 중단 + 에러 메시지 출력. 사용자가 백업 디렉토리로 수동 복구 가능.

#### 저장소 보장

```bash
mkdir -p "$ROOT/.hamstern/sessions" 2>/dev/null
```

`mkdir` 가 실패하면 (sandbox, EACCES 등) → **Step 5 (텍스트 폴백)** 으로.
성공하면 → Step 2 로.
````

- [ ] **Step 2: SKILL.md 의 Step 4 (병합 기록) 을 다음으로 교체**

기존 Step 4 본문 전체를 아래로 교체:

````markdown
### Step 4 — 원자적 이중 쓰기 (sessions/{id}.md + decisions.md)

한 번 record 호출 = 두 파일에 동시 쓰기. 둘은 sequential 이지만 다음 호출이 idempotent 라 부분 실패도 자동 복구.

#### (a) `sessions/{session_id}.md` — full distill 저장

기존 파일이 있고 같은 session_id 면 in-place 갱신 (replace), 없으면 새로 생성. 포맷:

```markdown
# Session {session_id}

_기록: {ISO timestamp}_

## 결정
- {결정 1} (이유: {왜})
- {결정 2} (이유: {왜})

## 실패·폐기
- {시도} → 폐기: {이유}

## 열린 질문
- {미정 사항}
```

빈 카테고리는 헤더만 남기거나 헤더도 생략 가능 (양쪽 다 acceptable, 일관성만 유지).

#### (b) `decisions.md` — 결정 부분만 카테고리별 append

각 채택된 결정 후보에 대해:

1. **세션 마커 매칭**: 같은 `<!-- session: {id} -->` 마커가 이미 있으면 그 항목을 **갱신**.
2. **Jaccard 매칭**: 새 항목 텍스트 vs 기존 항목 텍스트의 Jaccard 유사도 > 0.7 → **skip**.
3. **신규**: 위 두 케이스 아니면 해당 카테고리 (`## {Architecture|Performance|UI|Testing|Deployment|Other}`) 섹션 끝에 **append**. 카테고리 섹션이 없으면 새로 생성.

쓰기 시 `_마지막 업데이트: ...` 라인을 현재 ISO timestamp 로 갱신.

실패·폐기와 열린 질문은 decisions.md 에는 쓰지 않는다 (sessions/{id}.md 에만 보존). decisions.md 는 "현재 유효한 결정의 집합" 만 보유.

#### (c) `decisions-log.md` — append-only 이력

```markdown
## {YYYY-MM-DD HH:MM} · session {id}
+ [결정] 포터블 경로는 git-root → pwd 폴백
+ [실패] 환경변수 기반 환경 판단 → 폐기
+ [열림] decisions.md hot 영역 상한 결정 방식
```

`decisions-log.md` 가 없으면 첫 줄에 `# Decisions Log\n<!-- append-only. 수동 편집 금지. -->\n` 추가 후 블록 append.
````

- [ ] **Step 3: SKILL.md 의 "다른 진입점과의 관계" 섹션 갱신**

기존 섹션 전체를 다음으로 교체:

```markdown
## 다른 진입점과의 관계

- **`/hams:record` 가 hamstern 의 단일 capture 진입점**. hook (이전 CLI 자동 캡쳐) 은 Sub-C 에서 제거됨. start/stop 라이프사이클도 없음 — record 첫 호출 시 `.hamstern/sessions/` 가 자동 생성됨.
- **/hams:remind** 는 record 가 쓴 `decisions.md` 를 그대로 환기 — 포맷 호환성이 핵심.
- **/hams:audit-decisions** 는 record 가 쓴 `decisions.md` 와 `sessions/*.md` 를 재검토.
- **/hams:dashboard** 는 read + 편집 (toggle/remove) — record 가 쓴 데이터 위에서 작동. Sub-D 가 github.io static + 브라우저 편집 UI 로 재설계 예정.
```

- [ ] **Step 4: Step 5 (텍스트 폴백) 의 출력 구조 갱신**

기존 Step 5 의 fallback 마크다운 예시를 다음으로 교체:

````markdown
### Step 5 — 텍스트 폴백 (FS 쓰기 차단 시)

```
⚠️ 파일 시스템 쓰기 불가 환경입니다 (예: Claude Desktop sandbox).
아래 마크다운을 CLI 세션에서 {project_root}/.hamstern/ 에 직접 병합하세요.

=== sessions/{session_id}.md (전체 교체) ===
# Session {session_id}

_기록: {ISO timestamp}_

## 결정
- ...

## 실패·폐기
- ...

## 열린 질문
- ...

=== decisions.md (병합용) ===
(전체 decisions.md 내용을 Step 4(b) 규칙대로 합성해 출력)

=== decisions-log.md (append 블록) ===
## {ts} · session {id}
+ [결정] ...
+ [실패] ...
+ [열림] ...
```

세 블록 모두 포맷 동일 → 사용자가 복붙하면 CLI 의 record 호출과 같은 저장소로 수렴.
````

- [ ] **Step 5: Frontmatter 의 description 갱신**

기존:
```yaml
description: |
  지금 세션의 결정·실패·열린질문을 정리해 프로젝트 결정 저장소(decisions.md)에 기록.
  CLI·Desktop 양쪽 동작, FS 쓰기 불가 시 텍스트 폴백.
  사용법:
    /hams:record         # 후보 확인 모드 (기본)
    /hams:record --yes   # 후보 자동 채택 (긴 세션 끝)
```

→ 다음으로 교체:
```yaml
description: |
  hamstern 의 단일 capture 진입점 — 지금 세션을 sessions/{id}.md 에 저장 + 결정사항을 decisions.md 에 누적.
  CLI·Desktop 양쪽 동작, FS 쓰기 불가 시 텍스트 폴백.
  옛 baby/mom/boss 구조는 첫 호출 시 자동 마이그레이션.
  사용법:
    /hams:record         # 후보 확인 모드 (기본)
    /hams:record --yes   # 후보 자동 채택 (긴 세션 끝)
```

- [ ] **Step 6: Commit**

```powershell
git add skills/record/SKILL.md
git commit -m "feat(record): atomic dual-write (sessions + decisions) + auto-migration (Sub-C)"
```

---

## Task 5 — `skills/record/test_record_format.py` 갱신 (dual-write + 마이그레이션 케이스)

**Files:**
- Modify: `skills/record/test_record_format.py` — 신규 함수 + 4개 테스트 추가

기존 6개 케이스 (merge_decision, append_log 검증) 는 그대로 유지. Sub-C 의 신규 기능 (sessions/{id}.md 쓰기 + 자동 마이그레이션) 에 대한 회귀 보호 추가.

- [ ] **Step 1: 파일에 다음 함수 + 테스트 4개를 append**

`skills/record/test_record_format.py` 의 맨 끝 (마지막 테스트 `test_log_append_only_preserves_existing_blocks` 다음) 에 다음을 append:

```python


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
```

- [ ] **Step 2: Run the new tests**

Run:
```powershell
python -m pytest skills/record/test_record_format.py -v
```
Expected: 10 PASS (기존 6 + 신규 4).

- [ ] **Step 3: Commit**

```powershell
git add skills/record/test_record_format.py
git commit -m "test(record): dual-write + auto-migration cases (Sub-C)"
```

---

## Task 6 — `docs/conventions.md` 전면 개정 (3-tier → 2-tier)

**Files:**
- Modify: `docs/conventions.md` (전체 재작성)

- [ ] **Step 1: 파일 전체를 다음 내용으로 교체**

```markdown
# Hamstern Plugin Conventions

> 모든 hamstern 스킬·hook 이 따르는 공통 규약. 신규 스킬 추가 시 이 문서를 먼저 읽고 따른다.

## 1. 표준 저장소 레이아웃

```
{project_root}/.hamstern/
  sessions/{session_id}.md   # 세션별 distill (결정 + 실패·폐기 + 열린 질문)  ← record 가 작성
  decisions.md               # 현재 결정사항 (카테고리별, hot)                ← record 가 append
  decisions-log.md           # append-only 전체 이력 (cold)                  ← record 가 append
{project_root}/.claude/rules/{topic}.md (+references/)  # 영구 룰 (자동 로드)
```

`{project_root}` = `git rev-parse --show-toplevel` 결과, 실패 시 `pwd`.

> 옛 3-tier 구조 (`baby-hamster/`, `mom-hamster/`, `boss-hamster/`) 는 Sub-C 에서 제거됨. record 첫 호출 시 자동 마이그레이션 (`.hamstern.bak.{ts}/` 백업 후 새 구조로 mv).

## 2. 경로 해석 의사코드

모든 스킬은 다음 두 함수를 본문 첫 단계에 호출한다:

```
resolve_root():
  try:
    r = $(git rev-parse --show-toplevel 2>/dev/null)
    if r is empty: r = $(pwd)
  except: r = $(pwd)
  return r

ensure_store(r):
  try:
    mkdir -p {r}/.hamstern/sessions
    return OK
  except (no FS, EACCES, ENOENT, sandbox):
    return FALLBACK_TEXT

store_paths(r):
  return {
    sessions:  {r}/.hamstern/sessions/,
    decisions: {r}/.hamstern/decisions.md,
    log:       {r}/.hamstern/decisions-log.md
  }
```

## 3. 능력 프로브 패턴 (FS-try + Text-fallback)

환경 식별 변수 (`CLAUDE_CODE_REMOTE` 등) 에 **의존하지 않는다**. 항상 FS 쓰기를 시도하고 실패 시 텍스트 폴백:

```
try:
  ensure_store(r)
  write sessions/{id}.md
  write decisions.md
  write decisions-log.md
on failure:
  output the same markdown to chat
  instruct user to paste into CLI session
```

이 패턴은 Claude Code CLI 에서는 FS 모드, Claude Desktop App sandbox 에서는 텍스트 폴백으로 자연스럽게 분기된다.

## 4. `sessions/{session_id}.md` 포맷

```markdown
# Session {session_id}

_기록: {ISO timestamp}_

## 결정
- {결정 내용} (이유: {왜})

## 실패·폐기
- {시도 내용} → 폐기: {이유}

## 열린 질문
- {미정 사항}
```

규칙:
- 헤더 `# Session {id}` 고정, `_기록: ...` 라인은 매 record 호출마다 갱신
- 같은 session_id 로 재호출 시 in-place replace (append 아님 — 세션은 단일 distill)
- 빈 카테고리는 헤더만 남기거나 헤더도 생략 가능 (일관성만 유지)

## 5. `decisions.md` 포맷

```markdown
# 프로젝트 결정사항

_마지막 업데이트: {ISO timestamp}_

## {카테고리: Architecture | Performance | UI | Testing | Deployment | Other}
- {결정 내용} (이유: {왜}) <!-- session: {id} -->
```

규칙:
- 헤더 `# 프로젝트 결정사항` 고정
- `_마지막 업데이트: ...` 매 쓰기마다 갱신
- `## {카테고리}` 는 위 6개 중 하나
- 항목 끝 `<!-- session: {id} -->` 마커로 idempotent 재호출 시 갱신 매칭
- 중복 판정: Jaccard 유사도 > 0.7
- **실패·폐기와 열린 질문은 decisions.md 에 쓰지 않는다** — sessions/{id}.md 에만 보존. decisions.md 는 "현재 유효한 결정의 집합" 만.

## 6. `decisions-log.md` 포맷 (append-only)

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

## 7. 진입점 단일화 (Sub-C 이후)

| 진입점 | 역할 |
|--------|------|
| `/hams:record` | **유일한 capture 진입점**. sessions/{id}.md + decisions.md + decisions-log.md 에 atomic dual-write. |
| `/hams:remind` | 읽기 전용. `decisions.md` 를 현재 세션에 환기. |
| `/hams:audit-decisions` | 읽기 + 갱신. `decisions.md` 와 `sessions/*.md` 를 재검토하고 사용자 승인 시 `decisions.md` 갱신. |
| `/hams:dashboard` | UI. `sessions/*.md` + `decisions.md` 표시 + toggle/remove. Sub-D 에서 github.io static + 편집 UI 로 재설계. |

write 는 record 만, 다른 스킬은 reader 또는 reader+editor. hook 은 Sub-C 에서 제거됨 — 자동 캡쳐 없음.
```

- [ ] **Step 2: Verify section headers exist**

Run:
```powershell
$content = Get-Content docs/conventions.md -Raw -Encoding utf8
foreach ($h in '# Hamstern Plugin Conventions','## 1. 표준 저장소 레이아웃','## 2. 경로 해석 의사코드','## 3. 능력 프로브','## 4. `sessions/{session_id}.md` 포맷','## 5. `decisions.md` 포맷','## 6. `decisions-log.md` 포맷','## 7. 진입점 단일화') {
  "{0,-50} {1}" -f $h, $(if ($content.Contains($h)) {'OK'} else {'MISSING'})
}
```
Expected: 모두 OK.

또 옛 명칭 잔존 확인:
```powershell
Select-String -Path docs/conventions.md -Pattern "baby-hamster|mom-hamster|boss-hamster"
```
Expected: 0 results.

- [ ] **Step 3: Commit**

```powershell
git add docs/conventions.md
git commit -m "docs(conventions): rewrite for 2-tier flat structure (Sub-C)"
```

---

## Task 7 — `skills/remind/SKILL.md` + `skills/audit-decisions/SKILL.md` path 갱신

**Files:**
- Modify: `skills/remind/SKILL.md` — path 변경 + mom 모드 제거
- Modify: `skills/audit-decisions/SKILL.md` — path 변경

- [ ] **Step 1: `skills/remind/SKILL.md` 편집**

mom 모드는 mom-hamster 가 사라지므로 함께 제거. 결과적으로 인자 없는 `/hams:remind` 만 남음.

frontmatter description 갱신:

기존:
```yaml
description: |
  과거 세션 컨텍스트를 현재 세션에 환기. /clear 후 또는 다른 세션의 작업 맥락이 필요할 때 명시적으로 호출.
  CLAUDE.md 안 건드림 — 호출한 그 세션에만 영향.
  사용법:
    /hams:remind            # boss-hamster 결정사항(decisions.md) 로드 (기본)
    /hams:remind mom        # mom-hamster 세션 요약(mom.md) 로드 — ✅ 확정 전 자연 컨텍스트
```

→ 다음으로 교체:
```yaml
description: |
  과거 세션의 결정사항을 현재 세션에 환기. /clear 후 또는 다른 세션의 작업 맥락이 필요할 때 명시적으로 호출.
  CLAUDE.md 안 건드림 — 호출한 그 세션에만 영향.
  사용법:
    /hams:remind            # .hamstern/decisions.md 환기
```

본문에서:
- "두 가지 모드" 표 → 단일 모드 안내로 단순화 (mom 행 제거)
- path 모든 곳: `.hamstern/boss-hamster/decisions.md` → `.hamstern/decisions.md`
- `.hamstern/mom-hamster/mom.md` 언급 + 분기 로직 모두 제거
- "Claude 실행 절차" 의 "1. 인자 분기" 단계는 인자 없는 단일 경로로 단순화
- "파일이 없을 때" 의 mom.md 부재 케이스 삭제, decisions.md 부재 안내만 유지
- "두 세션 워크플로우" 다이어그램에서 mom 단계 제거

수정 후 grep:
```powershell
Select-String -Path skills/remind/SKILL.md -Pattern "boss-hamster|mom-hamster|baby-hamster|/hams:remind mom"
```
Expected: 0 results.

- [ ] **Step 2: `skills/audit-decisions/SKILL.md` 편집**

본문 line 118-119 근방 "입력 데이터":

기존:
```
1. `{project}/.hamstern/boss-hamster/decisions.md` — 현재 확정 결정사항
2. `{project}/.hamstern/baby-hamster/t{n}_*.md` — 터미널 대화 기록
```

→ 다음으로 교체:
```
1. `{project}/.hamstern/decisions.md` — 현재 확정 결정사항
2. `{project}/.hamstern/sessions/*.md` — 세션별 distill (결정/실패/열린질문)
```

line 130-132 근방 "출력 데이터":

기존:
```
{project}/.hamstern/boss-hamster/
├─ decisions.md (재생성)
```

→ 다음으로 교체:
```
{project}/.hamstern/
└─ decisions.md (재생성)
```

수정 후 grep:
```powershell
Select-String -Path skills/audit-decisions/SKILL.md -Pattern "boss-hamster|baby-hamster|mom-hamster"
```
Expected: 0 results.

- [ ] **Step 3: Commit**

```powershell
git add skills/remind/SKILL.md skills/audit-decisions/SKILL.md
git commit -m "refactor(skills): update remind+audit-decisions paths (boss/baby/mom → flat)"
```

---

## Task 8 — Dashboard 갱신 (server.py + static + SKILL.md)

**Files:**
- Modify: `skills/dashboard/server.py` — mom/analyze 라우트 제거, path 갱신
- Modify: `skills/dashboard/static/index.html` — UI 단순화 (mom 패널·analyze 버튼·card UI 제거)
- Modify: `skills/dashboard/SKILL.md` — 안내 단순화

- [ ] **Step 1: `skills/dashboard/server.py` 편집**

다음 변경 적용:

1. **상단의 aggregate.py 임포트 (있다면) 제거** — 현재 server.py 가 aggregate.py 를 직접 import 하진 않지만, 만약 어딘가 참조하면 제거.

2. **`do_GET` 메서드 (line 42-66 근방) 수정**:
   - `/api/mom` 분기 (line 49-51) 통째 삭제
   - `/api/baby` 분기 (line 55-61) 를 `/api/sessions` 로 변경, 내부 path 도 `baby-hamster` → `sessions`:
     ```python
     elif path == "/api/sessions":
         sessions_dir = root / ".hamstern" / "sessions"
         files = []
         if sessions_dir.exists():
             for f in sorted(sessions_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
                 files.append({"name": f.name, "content": f.read_text(encoding="utf-8")})
         self._json({"files": files})
     ```
   - `/api/decisions` 분기 (line 52-54) 의 path 갱신:
     ```python
     elif path == "/api/decisions":
         f = root / ".hamstern" / "decisions.md"
         self._json({"content": f.read_text(encoding="utf-8") if f.exists() else ""})
     ```
   - `/api/analyze/status` 분기 (line 62-64) 통째 삭제

3. **`do_POST` 메서드 수정**:
   - `/api/analyze` 분기 통째 삭제
   - `/api/pin/mom` 분기 통째 삭제
   - `/api/pin/boss` 분기는 유지하되 `_handle_boss_pin` 의 path 갱신 (아래 5번)

4. **`_handle_analyze` 메서드 (line 89-147 근방) 통째 삭제**

5. **`_handle_boss_pin` (line 149-187 근방) 수정**:
   - `boss_dir = root / ".hamstern" / "boss-hamster"` → `decisions_dir = root / ".hamstern"`
   - `decisions_file = boss_dir / "decisions.md"` → `decisions_file = decisions_dir / "decisions.md"`
   - `log_file = boss_dir / "decisions-log.md"` → `log_file = decisions_dir / "decisions-log.md"`
   - `boss_dir.mkdir(parents=True, exist_ok=True)` → `decisions_dir.mkdir(parents=True, exist_ok=True)` (이미 .hamstern 은 record 가 만들지만 dashboard 단독 호출도 safe)
   - 변수명 통일: `decisions_dir` 로

6. **`_handle_boss_unpin` (line 189-215 근방) 수정**:
   - 동일하게 `boss_dir` → `decisions_dir`, path 갱신

7. **상단 import 정리**: `threading`, `subprocess` 가 더 이상 안 쓰이면 제거. (analyze 의 백그라운드 Opus 호출 제거되므로 둘 다 unused 가능)

수정 후 검증:
```powershell
Select-String -Path skills/dashboard/server.py -Pattern "boss-hamster|baby-hamster|mom-hamster|/api/mom|/api/baby|/api/analyze|_handle_analyze"
```
Expected: 0 results.

```powershell
python -c "import py_compile; py_compile.compile('skills/dashboard/server.py', doraise=True); print('compile OK')"
```
Expected: `compile OK`.

- [ ] **Step 2: `skills/dashboard/static/index.html` 편집**

JavaScript 의 `load()` 함수 (line 85-96 근방) 수정:

기존:
```javascript
async function load() {
  const [mom, decisions, baby] = await Promise.all([
    fetch('/api/mom').then(r => r.json()).catch(() => ({content:''})),
    fetch('/api/decisions').then(r => r.json()).catch(() => ({content:''})),
    fetch('/api/baby').then(r => r.json()).catch(() => ({files:[]})),
  ]);
  document.getElementById('mom-content').textContent = mom.content || '(없음)';
  document.getElementById('decisions-content').textContent = decisions.content || '';
  renderDecisions(decisions.content);
  renderBaby(baby.files || []);
  checkStatus();
}
```

→ 다음으로 교체:
```javascript
async function load() {
  const [decisions, sessions] = await Promise.all([
    fetch('/api/decisions').then(r => r.json()).catch(() => ({content:''})),
    fetch('/api/sessions').then(r => r.json()).catch(() => ({files:[]})),
  ]);
  document.getElementById('decisions-content').textContent = decisions.content || '';
  renderDecisions(decisions.content);
  renderSessions(sessions.files || []);
}
```

`renderBaby` 함수 (line 98-106) → `renderSessions` 로 이름 변경 + 본문 단순화 (sessions 는 모두 record 작성이라 type 구분 불필요):

```javascript
function renderSessions(files) {
  const el = document.getElementById('sessions-list');
  if (!files.length) { el.innerHTML = '<div class="empty">없음</div>'; return; }
  el.innerHTML = files.map(f => {
    const short = f.name.replace(/^(session_)/, '').replace(/\.md$/, '').substring(0, 20);
    return `<div class="session-item"><span>${short}</span></div>`;
  }).join('');
}
```

`renderCards` 함수 (line 121-138) 통째 삭제 — analyze 결과 카드 표시. record 가 분석을 안 하므로 cards 개념 자체 사라짐.

`toggleMomPin` 함수 (line 140-148) 통째 삭제.

`confirmDecision` 함수 (line 150-155) 통째 삭제 — 이건 cards 의 ✅ 버튼이었음. record 가 직접 쓰므로 dashboard 의 "확정" 액션 없음.

`runAnalyze` 함수 (line 163-180) 통째 삭제.

`checkStatus` 함수 (line 182~) 통째 삭제.

`deleteDecision` (line 157-161) 은 유지. (× 버튼으로 결정 제거 — 편집 endpoint).

HTML body 수정 (line 80 이전):
- `<div id="mom-content">` 패널 통째 삭제
- `<div id="baby-list">` → `<div id="sessions-list">` 로 id 변경, surrounding label "Baby" → "Sessions"
- `<div id="cards">` 패널 통째 삭제
- "재분석" / "🔍 분석" 버튼 통째 삭제
- `<div id="analyze-status">` 통째 삭제

전체 결과: dashboard 가 단순 viewer + 결정 삭제 UI 만 남음.

> 주의: index.html 은 single-file SPA 라서 HTML + CSS + JS 가 한 파일에 있음. CSS 도 mom/cards/analyze 관련 클래스가 있으면 함께 삭제 (사용 안 되는 dead CSS).

수정 후 검증:
```powershell
Select-String -Path skills/dashboard/static/index.html -Pattern "/api/mom|/api/baby|/api/analyze|baby-list|mom-content|renderCards|renderBaby|runAnalyze|toggleMomPin|confirmDecision|checkStatus"
```
Expected: 0 results.

- [ ] **Step 3: `skills/dashboard/SKILL.md` 편집**

본문 정리:

1. "## 책임 분리" 섹션:
   - "**mom.md 집계** (baby → mom concat+dedup) → **Stop hook이 세션 종료 시 자동 실행**" 줄 삭제
   - "**Analyze (Opus 분석)** + **2단계 핀** + **decisions.md 확정** → 이 대시보드의 역할" → "**decisions.md 표시** + **결정 항목 toggle/remove** → 이 대시보드의 역할 (Sub-D 에서 github.io static + 편집 UI 로 재설계)"
   
2. "## 기능" 섹션:
   - "Baby MDs" → "Sessions" (record 가 쓴 sessions/*.md 목록)
   - "Mom MD + Audit" 항목 통째 삭제
   - "Decisions" 유지

3. "## 2단계 핀" 섹션 통째 삭제 — 핀 흐름 (mom-pin → boss-pin) 이 사라짐. dashboard 는 record 가 쓴 데이터를 표시·삭제만.

4. "## Fallback (mom.md가 비어있거나 stale 의심 시)" 섹션 통째 삭제 — aggregate.py 가 사라졌고 mom 개념 없음.

5. "## 데이터" 섹션:
   - `.hamstern/baby-hamster/*.md` → `.hamstern/sessions/*.md` (record 가 작성)
   - `.hamstern/mom-hamster/mom.md` 줄 통째 삭제
   - `.hamstern/boss-hamster/decisions.md` → `.hamstern/decisions.md`

수정 후 grep:
```powershell
Select-String -Path skills/dashboard/SKILL.md -Pattern "boss-hamster|baby-hamster|mom-hamster|Stop hook|aggregate"
```
Expected: 0 results.

- [ ] **Step 4: Commit**

```powershell
git add skills/dashboard/server.py skills/dashboard/static/index.html skills/dashboard/SKILL.md
git commit -m "refactor(dashboard): drop mom/analyze flow, paths → flat (Sub-C)"
```

---

## Task 9 — README.md 갱신

**Files:**
- Modify: `README.md` — "🔒 후크 활성화 조건" 섹션 통째 삭제 + 신규 changelog 항목 추가

- [ ] **Step 1: "🔒 후크 활성화 조건 (`/hams:start`)" 섹션 통째 삭제**

`README.md` 의 `# 🔒 후크 활성화 조건 (\`/hams:start\`)` 헤더부터 다음 `---` 구분선까지 통째로 삭제. 이 섹션은 hooks · /hams:start · /hams:stop 의 설명인데 셋 다 사라졌으므로 통째로 무의미.

> 참고: Sub-A 가 이미 cmux 공존 sub-section 을 삭제해서 섹션이 단축된 상태. Sub-C 는 그 섹션 통째.

- [ ] **Step 2: README 의 "명령 한눈에" 표에서 start/stop 행 삭제**

상단의 명령 표 (line 7-19 근방) 에서 다음 두 행 삭제:
```
| `/hams:start` | 현재 프로젝트에서 햄스턴 활성화 |
| `/hams:stop` | 일시 비활성 (데이터 보존) |
```

대신 같은 위치에 record 행 추가 (없으면):
```
| `/hams:record` | 단일 capture 진입점 — 세션을 sessions/{id}.md 저장 + 결정사항 decisions.md 누적 |
```

(record 행이 이미 표에 있으면 위치만 적절히, 없으면 dashboard 다음 줄에 삽입.)

- [ ] **Step 3: 신규 changelog 항목 추가 (changelog 영역 최상단)**

`## 📝 변경 내역 (Changelog)` 헤더와 blockquote 다음, 현재 최상단 항목 (`### 2026-05-23 — 멀티 플랫폼 핸드오프`) **위에** 다음 신규 entry 삽입:

```markdown
### 2026-05-23 — record 단일 진입점 + 평탄화 (hooks/start/stop/mom 제거)

- **자동화 인프라 전체 제거** — `hooks/` 디렉토리 (UserPromptSubmit + Stop hook + `_gate.py` + 모든 테스트) 통째 삭제. `/hams:start`, `/hams:stop` 스킬 삭제. `skills/dashboard/scripts/aggregate.py` 삭제. `.disabled`, `.deeptalk-running` 마커 개념 폐기.
- **3-tier → 2-tier 평탄화** — `baby-hamster/`, `mom-hamster/`, `boss-hamster/` 개념 폐기. 새 구조는 `.hamstern/sessions/{id}.md` + `.hamstern/decisions.md` + `.hamstern/decisions-log.md` 만.
- **`/hams:record` 가 단일 capture 진입점** — atomic dual-write: 한 번 호출 = 세션 distill 1회 → sessions/{id}.md 의 full distill (결정+실패+열린질문) + decisions.md 의 결정만 append. CLI · Desktop 양쪽 동작.
- **자동 마이그레이션** — record 첫 호출 시 옛 baby/mom/boss 구조 감지 → `.hamstern.bak.{ts}/` 전체 백업 → 새 구조로 mv (idempotent).
- **의존 스킬 path 갱신** — `/hams:remind`, `/hams:audit-decisions`, `/hams:dashboard` 의 path 가 새 평탄 구조 따름. dashboard 의 mom/analyze/cards 흐름 제거 (record 가 분석을 안 하므로). 편집 endpoint (× 결정 제거) 는 유지.
- **마커 사용 스킬 정리** — `/hams:deeptalk`, `/hams:rule`, `/hams:why`, `/hams:skill-creator` 의 `.deeptalk-running` 마커 set/unset 단계 모두 삭제 (마커는 hook 침묵용이었는데 hook 자체 없으니 무의미).
- **마켓플레이스** — `.claude-plugin/marketplace.json` 의 skills 배열에서 `./skills/start`, `./skills/stop` 제거 (13 → 11).
- **공통 규약 문서** — `docs/conventions.md` 가 2-tier 구조로 전면 개정.
- **Sub-D 로 deferred** — Dashboard 의 github.io static 호스팅 + 브라우저 토글·편집 UI + 크로스 머신.
```

- [ ] **Step 4: 그 외 README 영역 정리**

다음 위치에서 hooks/start/stop/mom 언급 정리:
- "## 명령 한눈에" 표 (Step 2 에서 처리)
- "/hams:remind" 섹션 내 mom 모드 언급 제거 (record 단일 진입점 반영)
- "Rules System" 섹션 내 `.deeptalk-running` 마커 언급 (있다면) 제거

`/hams:diary` 섹션은 record 와 무관하므로 그대로 유지.

수정 후 검증 (changelog history 제외):
```powershell
Select-String -Path README.md -Pattern "hooks/user_prompt|hooks/stop\.py|/hams:start|/hams:stop|baby-hamster|mom-hamster|boss-hamster" | Where-Object { $_.LineNumber -lt 400 }
```
Expected: 0 results (400 미만은 live 본문, 그 이상은 changelog history).

- [ ] **Step 5: Commit**

```powershell
git add README.md
git commit -m "docs(readme): remove hooks/start/stop sections, add Sub-C changelog"
```

---

## Task 10 — 최종 그린 게이트

**Files:** (검증만)

- [ ] **Step 1: 전체 테스트 그린**

Run:
```powershell
python -m pytest skills/record/ -v
```
Expected: 10 PASS (6 기존 + 4 신규).

hooks/ 디렉토리가 사라졌으므로 pytest 대상이 record 만.

- [ ] **Step 2: 활성 코드의 옛 구조 참조 0건 확인**

Run:
```powershell
Select-String -Path "skills\**\*.md","skills\**\*.py","skills\**\*.html","docs\conventions.md",".claude-plugin\*.json" -Pattern "baby-hamster|mom-hamster|boss-hamster|deeptalk-running|aggregate\.py|/hams:start|/hams:stop"
```
Expected: 0 results.

README.md 의 changelog history 는 별도 (history 보존 의도).

- [ ] **Step 3: 마켓플레이스 구조 OK**

Run:
```powershell
python -c "import json; m = json.load(open('.claude-plugin/marketplace.json')); s = m['plugins'][0]['skills']; print('count:', len(s)); print('valid:', len(s)==11 and './skills/start' not in s and './skills/stop' not in s and './skills/record' in s)"
```
Expected: `count: 11`, `valid: True`.

- [ ] **Step 4: 디렉토리 삭제 확인**

Run:
```powershell
foreach ($p in 'hooks','skills/start','skills/stop','skills/dashboard/scripts/aggregate.py') {
  "{0,-40} {1}" -f $p, $(if (Test-Path $p) {'STILL EXISTS'} else {'GONE'})
}
```
Expected: 모두 `GONE`.

- [ ] **Step 5: No commit** — 다음 Task 로.

---

## Task 11 — Manual 검증 (Layer 3) + verification log

**Files:**
- Create: `docs/plans/2026-05-23-record-unification-verification.md`

> 주의: Sub-B 와 마찬가지로 `/hams:record` 슬래시 명령은 사용자가 새 CLI 세션에서 직접 트리거해야 검증 가능. 자동화 세션 안에서는 발화 불가. verification.md 는 "보류" 상태로 작성하고 사용자가 첫 사용 시 결과 갱신.

- [ ] **Step 1: 사전 준비 — 옛 구조를 가진 검증 디렉토리 생성 (마이그레이션 테스트 용)**

이 step 은 마이그레이션 시나리오를 위한 fixture 생성. PowerShell 에서 직접 실행 가능 (슬래시 명령 아님):

```powershell
$VERIFY_DIR = "$env:TEMP\record-unif-verify-$(Get-Random)"
New-Item -ItemType Directory -Path "$VERIFY_DIR\.hamstern\baby-hamster" -Force | Out-Null
New-Item -ItemType Directory -Path "$VERIFY_DIR\.hamstern\mom-hamster" -Force | Out-Null
New-Item -ItemType Directory -Path "$VERIFY_DIR\.hamstern\boss-hamster" -Force | Out-Null
"old session 1" | Out-File -Encoding utf8 "$VERIFY_DIR\.hamstern\baby-hamster\session_old.md"
"# 프로젝트 결정사항`n## Architecture`n- old <!-- session: old -->`n" | Out-File -Encoding utf8 "$VERIFY_DIR\.hamstern\boss-hamster\decisions.md"
"# Decisions Log`n" | Out-File -Encoding utf8 "$VERIFY_DIR\.hamstern\boss-hamster\decisions-log.md"
"mom aggregate" | Out-File -Encoding utf8 "$VERIFY_DIR\.hamstern\mom-hamster\mom.md"
cd $VERIFY_DIR
git init -q
git add -A; git commit -qm "init with old structure"
echo "VERIFY_DIR=$VERIFY_DIR"
$VERIFY_DIR | Out-File -Encoding utf8 "$env:TEMP\verify_dir.txt"
```

- [ ] **Step 2: Write `docs/plans/2026-05-23-record-unification-verification.md`**

`docs/plans/2026-05-23-record-unification-verification.md` 신규 파일 작성:

```markdown
# Record Unification Verification — 2026-05-23

> Sub-project C (`docs/discussions/2026-05-23-record-unification-design.md`) 의 Task 11 검증 결과.
> 환경: Windows 11 / PowerShell / Python 3.x

## 검증 상태: 슬래시 명령 시나리오는 사용자 실행 보류

`/hams:record` 는 슬래시 명령이라 자동화 세션 안에서는 트리거 안 됨. 시나리오 1-7 은 사용자가 새 Claude Code CLI 세션에서 첫 사용 시 수행하고 결과를 아래 표에 갱신.

## 사전 준비

Step 1 의 PowerShell 블록으로 옛 구조 갖춘 `$VERIFY_DIR` 생성됨. `Get-Content $env:TEMP\verify_dir.txt` 로 경로 복원.

## 시나리오 결과

| # | 시나리오 | 결과 | 비고 |
|---|----------|------|------|
| 1 | 신규 프로젝트에서 record 첫 호출 → sessions/{id}.md + decisions.md 자동 생성 | 보류 | 빈 디렉토리에서 첫 호출 |
| 2 | 옛 구조 디렉토리에서 record 첫 호출 → 자동 마이그레이션 + 백업 폴더 생성 | 보류 | $VERIFY_DIR 에서 시도. `.hamstern.bak.{ts}/` 생성 확인 |
| 3 | 같은 세션 두 번째 record → sessions/{id}.md 갱신 (in-place), decisions.md append + dedup | 보류 | 추가 결정 후 재호출 |
| 4 | `/hams:remind` → 새 path 의 decisions.md 정상 환기 | 보류 | record 후 호출 |
| 5 | `/hams:audit-decisions` → 새 path 정상 동작 (sessions/*.md + decisions.md 읽기) | 보류 | |
| 6 | `/hams:dashboard` → 새 path 의 sessions/decisions 정상 표시, × 결정 제거 작동 | 보류 | server.py 실행 후 브라우저 |
| 7 | FS 쓰기 차단 시 텍스트 폴백 (Desktop sandbox 시뮬레이션) | 보류 | `Set-Acl` 로 차단 후 호출 |

## 사전 사실 (이미 인라인 검증된 항목)

- ✅ pytest 10/10 PASS (skills/record/test_record_format.py — 기존 6 + 신규 4) — Task 10
- ✅ `.claude-plugin/marketplace.json` 13 → 11 (start, stop 제거, record 유지) — Task 10
- ✅ hooks/, skills/start/, skills/stop/, dashboard/scripts/aggregate.py 모두 삭제 확인 — Task 10
- ✅ 활성 코드·문서에 옛 구조 (baby/mom/boss-hamster, deeptalk-running, /hams:start, /hams:stop) 참조 0건 — Task 10
- ✅ server.py 컴파일 OK — Task 8 Step 1

## 발견된 후속 작업

- (사용자 검증 시 실패 항목 발견되면 여기 기록)
- 시나리오 2 의 자동 마이그레이션이 사용자 환경에서 백업 위치를 잘 만드는지 첫 확인 시 주목

## 결론

Sub-C 의 모든 정적·회귀·구조 검증은 통과. 슬래시 명령 + 마이그레이션 실행 검증 (시나리오 1-7) 은 사용자 첫 사용 시점에 수행해 본 표에 결과 기록.
```

- [ ] **Step 3: Commit verification log**

```powershell
git add docs/plans/2026-05-23-record-unification-verification.md
git commit -m "test(verify): record unification + migration verification log (CLI scenarios deferred)"
```

- [ ] **Step 4: 정리 (선택)**

```powershell
$VERIFY_DIR = Get-Content "$env:TEMP\verify_dir.txt"
# Remove-Item -Recurse -Force $VERIFY_DIR -ErrorAction SilentlyContinue
# Remove-Item "$env:TEMP\verify_dir.txt" -ErrorAction SilentlyContinue
```

사용자가 시나리오 2 직접 검증 시 $VERIFY_DIR 가 필요하니 자동 정리는 주석 처리. 사용자가 검증 끝나면 수동 정리.

---

## Definition of Done

- [ ] Task 1–9 의 모든 step 완료, `python -m pytest skills/record/ -v` 그린 (10/10)
- [ ] Task 10 의 4가지 검증 (pytest, 옛 참조 grep, marketplace, 디렉토리 삭제) 모두 ✅
- [ ] Task 11 의 verification.md 작성 + commit
- [ ] git log 에 신규 commit: Task 1, 2, 3, 4, 5, 6, 7, 8, 9, 11 = 10개 (Task 0, 10 = no commit)
- [ ] `Test-Path hooks` → False, `Test-Path skills/start` → False, `Test-Path skills/stop` → False
- [ ] hooks/ 가 사라졌으므로 `python -m pytest` 의 default discovery 는 skills/record/ 만 (root pytest 호출 시도 → record 만 실행)

## Out of Scope (이 plan 에서 처리하지 않음)

- Sub-D: Dashboard 의 github.io static 호스팅, 브라우저 토글·편집 UI, 크로스 머신
- 룰 시스템 (`why`/`rule`) 의 본질적 구조 변경 (Sub-C 는 마커 set/unset step 만 정리)
- diary 스킬
- 글로벌 영역 (`~/.hamstern/`, `~/.claude/hams-diary.json`)
- 새로운 capture 모드 (e.g., `/hams:record --partial`)
