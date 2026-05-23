# Multi-Platform Session Handoff — Sub-project B

**Date:** 2026-05-23
**Status:** Approved design, ready for plan
**Sub-project:** B (of A+B+...). A 완료 (`docs/discussions/2026-05-23-hamstern-cleanup-design.md`). B 는 record-handoff-redesign 의 Phase 0+1 만 채택. Phase 2-5 는 추후 Sub-project C/D/... 로 분리.

## 배경

Sub-project A 의 cleanup 으로 hooks 가 정리되었으나, hook 자체는 **Claude Code CLI 전용** 이다 (Anthropic 공식 docs + 이슈 #45514 확인). Claude Desktop App 은:

- ❌ Hook 지원 없음 (issue tracked, 미해결)
- ❌ 로컬 세션 로그 없음 (서버사이드만 저장)
- ❌ `cwd` 컨셉 없음 (앱은 working directory 가 없음)
- ✅ `~/.claude/skills/` 공유 → 슬래시 명령은 동작
- ✅ MCP 서버 동작 가능하나 request-response only (관찰형 X)

이 제약 안에서 "세션 핸드오프" 를 달성하려면 **자동 캡쳐 (hook)** 가 아닌 **수동 캡쳐 (사용자가 슬래시 명령 트리거)** 진입점이 필요하다.

`docs/plans/2026-05-22-record-handoff-redesign.md` 에 작성된 `record` 스킬 설계가 정확히 이 문제를 푼다. Sub-project B 는 그 설계의 **Phase 0 + Phase 1 만** 채택해 멀티 플랫폼 핸드오프 문제만 해결한다.

## 목표

`record` 스킬을 신설해, Claude Desktop App 과 Claude Code CLI 양쪽에서 동일하게 동작하는 **수동 세션 캡쳐 진입점** 을 제공한다. 캡쳐된 결정사항은 기존 `decisions.md` 저장소에 통합되어 `/hams:remind` 가 양쪽에서 동일하게 환기한다.

## 원칙 (record-handoff-redesign.md 의 P1-P7 중 본 sub-project 적용분)

- **P1 일관성** — 세 입구 (hook 자동 / record 수동 / dashboard 정리) → 종착지 하나 `{project_root}/.hamstern/boss-hamster/decisions.md`
- **P2 포터블 경로** — `git rev-parse --show-toplevel` → 실패 시 `pwd`. 절대경로·`${CLAUDE_PLUGIN_ROOT}` 금지
- **P3 능력 프로브** — 환경변수로 환경 판단 X. FS 쓰기 try → 실패 시 텍스트 폴백
- **P6 hook ≠ record** — hook (Python, raw turn append) ≠ record (모델 distill, 결정만). 서로 호출 안 함, 포맷만 공유

## 비범위 (Out of scope)

- Phase 2: `why`/`rule` 라우팅 가드
- Phase 3: 결정 저장소 hot/cold 계층화 + 강등
- Phase 4: `chat` 신규 스킬 (3 청중 분리), `diary` 홈 경로 이동
- Phase 5: 자동화 (transcript-watcher 데몬)
- hooks 자체 추가 변경 (Sub-project A 에서 cmux/중복 정리 끝, 추가 변경 없음)
- 글로벌 영역 (`~/.hamstern/`, `~/.claude/hams-diary.json`) 처리

## 아키텍처

### 데이터 흐름 (After)

```
                                 .hamstern/boss-hamster/decisions.md
                                                ▲
                              ┌─────────────────┼─────────────────┐
                              │                 │                 │
              CLI Stop hook   │     /hams:dashboard ✅ pin       │  /hams:record  (수동)
              ─ baby/mom 집계  │     ─ Opus 분석 + 사용자 핀         │  ─ 모델 distill + 사용자 확인
                              │                                   │
                          (자동/CLI)                          (수동/CLI+Desktop)
                                                                  │
                                                       FS 실패 시 ↓
                                                       채팅 출력 (사용자 복붙)
```

### 신규 파일

| 파일 | 책임 |
|------|------|
| `docs/conventions.md` | 표준 저장소 레이아웃 + 경로 해석 의사코드 + 포맷 스펙. Sub-project A 의 결과물 (`.hamstern/{baby,mom,boss}-hamster/` + `decisions.md`) 을 공식 문서화. |
| `skills/record/SKILL.md` | `/hams:record` 슬래시 명령. 5-step 본문 + 두 포맷 스펙 inline. |
| `skills/record/test_record_format.py` | Layer 2 포맷 호환성 회귀 테스트 (hooks/ 의 sister-test 컨벤션과 동일). |
| `docs/plans/2026-05-24-record-verification.md` | Layer 3 manual 검증 노트 (작업 완료 후 생성). |

### 신규 마켓플레이스 등록

`.claude-plugin/marketplace.json` 의 skills 배열에 `./skills/record` 추가. (단순 1줄 변경, 변경 파일 5개째)

## Phase 0 — `docs/conventions.md`

**내용:**
- 표준 저장소 레이아웃 (`.hamstern/{baby,mom,boss}-hamster/`, `decisions.md`, `decisions-log.md`)
- 경로 해석 의사코드:
  ```
  resolve_root():
    r = $(git rev-parse --show-toplevel 2>/dev/null) ; if fail: r = $(pwd)
    return r
  ensure_store(r):
    try mkdir -p r/.hamstern/boss-hamster
    on fail (no FS, EACCES, ENOENT) -> FALLBACK_TEXT mode
  store_paths(r):
    decisions = r/.hamstern/boss-hamster/decisions.md
    log       = r/.hamstern/boss-hamster/decisions-log.md
  ```
- 능력 프로브 패턴: FS try → text fallback. 환경 식별 변수 (`CLAUDE_CODE_REMOTE` 등) 에 의존 금지.
- `decisions.md` / `decisions-log.md` 포맷 예시 (record 가 사용하는 그대로)

**선택 (이번에 안 함):** `skills/_core/store.sh` — 공유 bash 헬퍼. 채팅 폴백에서 못 쓰므로 CLI 가속용. record 본문에 inline 으로 처리, 다른 스킬에 같은 헬퍼 수요 생기면 그때 추출 (YAGNI).

## Phase 1 — `skills/record/SKILL.md`

### Frontmatter

```yaml
---
name: record
description: 지금 세션의 결정·실패·열린질문을 정리해 프로젝트 결정 저장소(decisions.md)에 기록 — CLI·Desktop 동작, FS 불가 시 텍스트 폴백
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---
```

### 동작 (5 단계)

**Step 1 — 경로 해석 & 저장소 보장**

`resolve_root` + `ensure_store` 호출. FS mkdir 실패 시 Step 5 (텍스트 폴백) 으로.

**Step 2 — Distill (모델이 현재 세션 컨텍스트에서 추출)**

세 종류 분리해 후보 추출:
- ① 결정 — 이번 세션에 확정한 것 + 이유 한 줄
- ② 실패·폐기 — 시도했다 버린 것 + 이유 한 줄
- ③ 열린 질문 — 미정 상태 그대로 남은 것

원본 턴 로그는 **만들지 않음** (그건 hook 의 baby 영역).

**Step 3 — 사용자 확인 (헛것 방지)**

`AskUserQuestion` 로 카테고리별 후보 표 제시 → keep/drop. `--yes` 옵션 시 skip. Desktop 에서 `AskUserQuestion` 불안정 가능성 → "출력 후 응답 대기" 폴백 패턴도 SKILL.md 본문에 명시.

**Step 4 — 병합 기록 (idempotent)**

```
read existing decisions.md (없으면 빈 템플릿)
for each kept candidate:
  if 같은 session_id 마커 존재 → 갱신 (replace)
  else if Jaccard(decision, existing) > 0.7 → skip (dashboard 와 동일 임계)
  else → append to category
write decisions.md
append timestamp block to decisions-log.md (append-only)
```

세션 마커: `<!-- session: {id} -->` 라인을 결정 항목에 inline 부착.

**Step 5 — 텍스트 폴백 (FS 차단 시)**

```
⚠️ 파일 시스템 쓰기 불가 환경입니다 (예: Claude Desktop sandbox).
아래 마크다운을 CLI 세션에서
{project_root}/.hamstern/boss-hamster/decisions.md 에 병합하세요.

(decisions.md 포맷 마크다운)
(decisions-log.md 포맷 블록)
```

포맷 동일 → 사용자가 복붙하면 동일 저장소로 수렴.

### 포맷 스펙

**`decisions.md`:**
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

**`decisions-log.md` (append-only):**
```markdown
## {YYYY-MM-DD HH:MM} · session {id}
+ [결정] {…}
+ [실패] {…}
+ [열림] {…}
```

### 사용 패턴

```
세션 진행 중 또는 마무리 시:
  /hams:record               # 확인 모드 (기본)
  /hams:record --yes         # 후보 자동 채택 (긴 세션 끝)

장기 세션은 마일스톤마다 호출 권장 (compaction 손실 방지)
```

## 테스트 전략 (3-Layer)

**Layer 1 — 정적 검증**
- `skills/record/SKILL.md` frontmatter 파싱 가능 (`name`, `description`, `allowed-tools` 존재)
- `docs/conventions.md` 의 의사코드 + 포맷 예시 존재
- `aggregate.py` 가 record 가 쓸 `decisions.md` 포맷 (dashboard 와 동일) 을 깨뜨리지 않는지 회귀 확인

**Layer 2 — pytest (`skills/record/test_record_format.py`)**
포맷 호환성 위주 — Step 4 의 의사코드를 Python 변환한 가벼운 검증:
- 신규 카테고리 항목 → 새 `## {category}` 섹션 생성
- 기존 카테고리에 새 항목 → 같은 섹션 끝에 append
- 같은 session id 두 번 → 갱신 (중복 X)
- Jaccard > 0.7 매칭 → skip
- `decisions-log.md` append-only (기존 라인 보존)
- 텍스트 폴백 모드 → 두 마크다운 블록을 표준 출력 반환

helper module 은 두지 않음 (YAGNI) — SKILL.md 의 의사코드만 따르는 test-only 보조 함수로 처리.

**Layer 3 — Manual 검증 (`docs/plans/2026-05-24-record-verification.md`)**

1. CLI 세션에서 `/hams:record` → 후보 추출 → 확인 → `decisions.md` 기록 ✅/❌
2. 같은 세션 두 번째 호출 → 중복 없음 ✅/❌
3. FS 쓰기 차단 시뮬레이션 (`chmod -w` 등) → 텍스트 폴백 출력 ✅/❌
4. `/hams:dashboard` 가 record 항목 정상 표시 ✅/❌
5. `/hams:remind` 가 record 가 쓴 `decisions.md` 정상 환기 ✅/❌
6. **Claude Desktop App 환경에서 동일 시나리오** — Skills 가 Desktop 에서 정확히 어떻게 보이는지, Bash·Write 가 실제 동작하는지, 안 되면 텍스트 폴백 경로 실제 발화 확인 ✅/❌

단계 6 이 핵심 멀티 플랫폼 검증. Desktop 환경 접근 불가하거나 시간 부족하면 **CLI 검증 (1-5) 까지만 통과시키고 Desktop 검증은 후속 task 로 분리** — 사용자가 첫 사용 시점에 확인.

## 위험 매트릭스

| 위험 | 가능성 | 영향 | 완화 |
|---|---|---|---|
| Desktop App 에서 Bash/Write tool 이 실제로 안 됨 | 중간 | record FS 모드 실패 | 텍스트 폴백 (P3) 가 정확히 그 경우용 안전망 |
| hook 자동 캡쳐 (CLI) + record 수동 호출 충돌 | 낮음 | 같은 결정이 baby 와 decisions 양쪽에 | hook=raw turn / record=distilled decision 분리. dashboard dedup 이 추가 안전망 |
| 사용자가 distill 단계에서 모델 오인지 결과 무비판 채택 | 중간 | 잘못된 결정 기록 | Step 3 확인 단계 + `--yes` 디폴트 아님 |
| `decisions.md` 포맷이 dashboard 와 미세하게 어긋남 | 낮음 | dashboard 가 못 읽거나 record 가 dashboard 결과 깨뜨림 | Layer 1 회귀 + Layer 3 단계 4 |
| `git rev-parse` 실패 → `pwd` 폴백이 잘못된 위치에 저장 | 낮음 | 다른 디렉토리에 `.hamstern/` 생성 | record 호출 첫 줄에 resolved root 사용자에게 echo, 사용자가 잘못된 경우 abort 가능 |

## 롤백

- 한 작업 = 한 commit (Sub-project A 와 동일 정책)
- record 도입은 신규 파일이므로 기존 흐름 영향 0 — 문제 시 commit 단위 revert
- `docs/conventions.md` 는 문서만 — 행동 변화 0
- 마켓플레이스 등록 1줄도 단순 git revert 로 안전 복원

## Definition of Done

- [ ] `docs/conventions.md` 작성, 의사코드 + 포맷 예시 포함
- [ ] `skills/record/SKILL.md` 작성, frontmatter + 5-step 본문 + 두 포맷 스펙 포함
- [ ] `.claude-plugin/marketplace.json` 에 `./skills/record` 등록
- [ ] Layer 1 정적 검증 통과 (frontmatter 파싱 + dashboard 포맷 호환성)
- [ ] Layer 2 `pytest skills/record/test_record_format.py` 그린
- [ ] Layer 3 단계 1-5 (CLI 시나리오) `verification.md` 에 모두 ✅
- [ ] Layer 3 단계 6 (Desktop 시나리오) 통과 또는 명시적 후속 task 로 분리
- [ ] 기존 `pytest hooks/` 18/18 PASS 유지 (회귀 없음)
- [ ] `grep -r "/hams:record" skills/` 결과: `skills/record/SKILL.md` + README changelog 외에 다른 스킬이 record 를 직접 호출하지 않음 (P6 hook ≠ record)

## 다음 단계

Sub-project B 완료 후 → 추후 별도 sub-project 로 진행 가능한 후보 (record-handoff-redesign.md 의 나머지 Phase):
- **C**: Phase 2 (`rule add` 라우팅 가드 — 검증 가능한 룰은 테스트로 우선 제안)
- **D**: Phase 3 (결정 저장소 hot/cold 계층화 + 강등)
- **E**: Phase 4 (`chat` 스킬 신설, `diary` 홈 경로 이동)
- **F**: Phase 5 (자동화 — transcript-watcher 데몬 등)

각각 별도 brainstorming → spec → plan → implementation 사이클.
