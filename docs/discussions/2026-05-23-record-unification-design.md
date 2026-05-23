# Record-Unified Simplification — Sub-project C

**Date:** 2026-05-23
**Status:** Approved design, ready for plan
**Sub-project:** C (of A+B+C+...). A 완료 (cleanup). B 완료 (record 신설). C 는 record 를 **단일 capture 진입점** 으로 격상시키고 hooks·start·stop·mom 개념 전체를 제거. D 는 후속 — dashboard 의 github.io static + edit UI 재설계.

## 배경

Sub-B 에서 record 를 도입하며 "manual 이 universal" 통찰을 얻었다 — hook (CLI 전용) 보다 record (CLI + Desktop) 가 더 광범위하게 동작. 그 통찰을 끝까지 밀면 자연스러운 귀결: **hook 자체가 불필요**.

추가로 사용자 멘탈모델 정정:
- baby/mom/boss 3-tier 는 hook 의 turn-level capture 를 가정한 구조 — record (session-level) 에는 과잉
- 진짜 필요한 것은 2-tier: **세션 기록 (per session) + 결정사항 (cross-session 누적)**
- record 한 번 호출 = 세션 distill 1회 → 두 파일에 동시 쓰기 (sessions/{id}.md 의 full distill + decisions.md 의 결정만 append)

## 목표

`/hams:record` 를 hamstern 의 단일 capture 진입점으로 통일한다. hooks 전체, start/stop 라이프사이클, mom-hamster 개념을 제거하고 폴더 구조를 평탄화한다. 결과: 코드 50%+ 감축 + cross-platform 100% 호환 + 마커·race condition·silent failure 위험 0.

## 원칙

- **단일 진입점** — write 는 `/hams:record` 만. 다른 어떤 스킬·hook 도 sessions/ 또는 decisions.md 에 쓰지 않는다.
- **원자적 이중 쓰기** — 한 번 record = sessions/{id}.md + decisions.md 동시 갱신. 둘 사이 일관성 유지.
- **자동 라이프사이클** — `.hamstern/` 디렉토리는 record 첫 호출 시 자동 생성. `/hams:start` 같은 명시적 활성화 단계 없음.
- **자동 마이그레이션 (idempotent)** — 기존 사용자의 baby/mom/boss 구조는 record 첫 호출 시 새 구조로 자동 이전. 안전 백업 후 mv.
- **편집은 별 영역** — record 는 SAVE 만. 결정사항 토글·삭제·수정은 `/hams:audit-decisions` (재검토) 또는 Sub-D 의 신규 dashboard (편집 UI) 가 담당.

## 비범위 (Out of scope)

- **Sub-D**: 새 dashboard 의 github.io static 호스팅, 브라우저 토글·편집 UI, 크로스 머신 동기화
- 룰 시스템 (`why`/`rule`) 구조 변경
- diary 스킬
- skill-picker/skill-creator/registry-collector 변경 (capture 와 무관)
- 글로벌 영역 (`~/.hamstern/`, `~/.claude/hams-diary.json`)

## Before / After 구조

### Before (Sub-B 직후)
```
.hamstern/
  baby-hamster/{session_id}.md    ← hook auto (UserPromptSubmit 매 턴 append)
  mom-hamster/mom.md              ← Stop hook 자동 집계
  boss-hamster/
    decisions.md                  ← dashboard pin OR record (Sub-B)
    decisions-log.md              ← record append
  .disabled                       ← /hams:stop 마커
  .deeptalk-running               ← deeptalk/rule/why/skill-creator 가 hook 침묵용으로 set
```

### After (Sub-C)
```
.hamstern/
  sessions/{session_id}.md        ← record only (세션별 full distill)
  decisions.md                    ← record append (cross-session 결정만)
  decisions-log.md                ← record append-only 이력
```

마커 파일 0개. mom 폴더 없음. baby/boss 명칭 없음.

## `/hams:record` 의 새 동작

### Step 1 — 경로 해석 + 자동 마이그레이션
```
ROOT = git rev-parse --show-toplevel 2>/dev/null || pwd
mkdir -p $ROOT/.hamstern/sessions    # 첫 호출 시 자동 생성

# 자동 마이그레이션 (idempotent, 안전 백업)
if [ -d $ROOT/.hamstern/boss-hamster ] || [ -d $ROOT/.hamstern/baby-hamster ] || [ -d $ROOT/.hamstern/mom-hamster ]:
  cp -r $ROOT/.hamstern $ROOT/.hamstern.bak.{ISO timestamp}    # 안전망
  mv $ROOT/.hamstern/baby-hamster/*.md → $ROOT/.hamstern/sessions/   (있으면)
  mv $ROOT/.hamstern/boss-hamster/decisions.md → $ROOT/.hamstern/decisions.md   (있으면)
  mv $ROOT/.hamstern/boss-hamster/decisions-log.md → $ROOT/.hamstern/decisions-log.md   (있으면)
  rm -rf $ROOT/.hamstern/mom-hamster   (있으면 — 정보는 sessions 에 다 들어감)
  rm -rf $ROOT/.hamstern/baby-hamster $ROOT/.hamstern/boss-hamster   (빈 폴더 정리)
  echo "마이그레이션 완료. 백업: .hamstern.bak.{ts}/"
```

FS 쓰기 실패 → Step 5 텍스트 폴백 (Sub-B 와 동일 패턴).

### Step 2 — Distill (Sub-B 와 동일)
현재 세션 컨텍스트에서 결정/실패·폐기/열린질문 후보 5–15 개 추출.

### Step 3 — 사용자 확인 (Sub-B 와 동일)
`AskUserQuestion` 또는 출력 폴백, `--yes` 옵션.

### Step 4 — 원자적 이중 쓰기

**(a) sessions/{session_id}.md — full distill 저장**

기존 파일 있으면 갱신 (같은 session id 면 in-place replace), 없으면 새로 생성. 포맷:

```markdown
# Session {session_id}

_기록: {ISO timestamp}_

## 결정
- {결정 1} (이유: ...)
- {결정 2} (이유: ...)

## 실패·폐기
- {시도} → 폐기: {이유}

## 열린 질문
- {미정 사항}
```

**(b) decisions.md — 결정만 append (Sub-B 의 Step 4 알고리즘 그대로)**

결정 카테고리별 (`## {Architecture|Performance|UI|Testing|Deployment|Other}`) append. 같은 `<!-- session: {id} -->` 마커는 갱신, Jaccard > 0.7 은 skip. decisions-log.md 에 timestamp 블록 append.

두 쓰기는 같은 record 호출에서 sequential (원자적 — 한 쪽 성공 + 다른 쪽 실패면 다음 호출 시 idempotent 로 복구).

### Step 5 — 텍스트 폴백 (Sub-B 와 동일)
FS 쓰기 차단 시 동일 마크다운 두 블록 (sessions/{id}.md + decisions 갱신분) 을 채팅 출력.

## 삭제 목록 (전부)

### 코드
- `hooks/` 전체 디렉토리 (`_gate.py`, `user_prompt.py`, `stop.py`, `test_gate.py`, `test_baby_record.py`, `test_all_hooks_gated.py`)
- `skills/start/` 전체
- `skills/stop/` 전체
- `skills/dashboard/scripts/aggregate.py`

### 문서·SKILL.md 의 step
- `skills/deeptalk/SKILL.md` — `.deeptalk-running` 마커 set/unset 단계 제거
- `skills/rule/SKILL.md` — 동일
- `skills/why/SKILL.md` — 동일
- `skills/skill-creator/SKILL.md` — 동일

### 마켓플레이스
- `.claude-plugin/marketplace.json` — `./skills/start`, `./skills/stop` 두 항목 제거

## 수정 목록

| 파일 | 변경 |
|------|------|
| `skills/record/SKILL.md` | Step 1 에 자동 마이그레이션 로직 추가. Step 4 에 sessions/{id}.md 쓰기 (이중 쓰기) 추가. 본문 전반 새 구조 반영. |
| `skills/record/test_record_format.py` | dual-write 케이스 추가 (sessions/{id}.md 의 결정/실패/열린질문 포맷 검증 + decisions.md 와의 일관성) |
| `skills/remind/SKILL.md` | path 갱신: `boss-hamster/decisions.md` → `decisions.md` |
| `skills/audit-decisions/SKILL.md` | path 갱신: 동일 + `baby-hamster/*.md` → `sessions/*.md` |
| `skills/dashboard/server.py` | `/api/baby` → `/api/sessions`, `/api/mom` 제거, `/api/decisions` 의 path 갱신, `_handle_boss_pin`/`_handle_boss_unpin` 의 path 갱신 (편집 endpoint 는 유지 — Sub-D 가 재설계할 때까지 로컬에서 동작 보존) |
| `skills/dashboard/SKILL.md` | mom 관련 안내 제거, baby → sessions 용어 갱신, fallback 안내 (aggregate.py 제거되었으니 그 부분 삭제) |
| `skills/dashboard/static/*` | UI 가 `/api/sessions` 사용하도록 갱신 (server.py 와 동일 path 변경 반영) |
| `docs/conventions.md` | 3-tier → 2-tier 전면 개정 |
| `README.md` | hooks 섹션, start/stop 섹션, mom/baby/boss 언급 전부 제거; record 가 모든 capture 를 담당하는 새 워크플로우 문서화; 신규 changelog |

## 자동 마이그레이션 안전장치

- 마이그레이션 전에 `.hamstern.bak.{ISO timestamp}/` 로 전체 백업
- mv 작업은 conditional (해당 파일·폴더 존재할 때만)
- 한 번 마이그레이션되면 이후 호출은 no-op (이미 sessions/ + decisions.md 존재)
- 마이그레이션 실패 시 (권한 등) record 진행 중단 + 에러 메시지 출력 + 사용자 수동 복구 안내
- 백업 폴더는 사용자가 확인 후 수동 삭제 (자동 정리 안 함)

## 테스트 전략 (3-Layer, Sub-B 와 동일 패턴)

**Layer 1 — 정적 검증**
- `skills/record/SKILL.md` frontmatter 파싱
- `docs/conventions.md` 의 새 섹션 (2-tier 구조) 존재
- `skills/dashboard/server.py` 가 `boss-hamster|baby-hamster|mom-hamster` 참조 0건
- `.claude-plugin/marketplace.json` 에서 start/stop 제거 + record 등록 확인

**Layer 2 — pytest**
- `skills/record/test_record_format.py` 의 케이스 확장:
  - dual-write: 같은 distill 이 sessions/{id}.md + decisions.md 양쪽에 동기화됨
  - sessions/{id}.md 포맷: 결정/실패·폐기/열린질문 세 섹션 정확
  - sessions/{id}.md idempotent (같은 session id 두 번 호출 시 갱신)
  - 마이그레이션 시뮬레이션: old 구조 모사 → record 호출 → new 구조로 변환 + 백업 폴더 생성

**Layer 3 — Manual 검증** (사용자가 새 CLI 세션에서)
1. 신규 프로젝트에서 record 첫 호출 → sessions/{id}.md + decisions.md 자동 생성
2. 옛 구조 (`.hamstern/{baby,mom,boss}-hamster/`) 가 있는 프로젝트에서 record 첫 호출 → 자동 마이그레이션 + 백업 폴더 생성 + 새 구조에 쓰기
3. 같은 세션에서 두 번째 record → sessions/{id}.md 갱신 (중복 X), decisions.md append + dedup
4. `/hams:remind` → 새 path 의 decisions.md 정상 환기
5. `/hams:audit-decisions` → 새 path 정상 동작 (sessions/*.md + decisions.md 읽기)
6. `/hams:dashboard` → 새 path 의 sessions/decisions 정상 표시, 편집 endpoint 작동

## 위험 매트릭스

| 위험 | 가능성 | 영향 | 완화 |
|---|---|---|---|
| 자동 마이그레이션이 옛 데이터 손상 | 중간 | 사용자 데이터 영구 손실 | 마이그레이션 전 `.hamstern.bak.{ts}/` 전체 백업 (안전망) + git 추적 권장 안내 |
| dashboard path 갱신 누락으로 일시 깨짐 | 낮음 | 로컬 dashboard 동작 불가 | 같은 sub-project 안에서 server.py + static/ + SKILL.md 모두 갱신, Task 단위로 commit + 그린 게이트 |
| 기존 hook 사용자가 record 호출 안 해서 기록 누락 | 중간 | 세션 캡쳐 안 됨 | README + 새 changelog 에 명시: hook 자동 캡쳐는 제거됨, record 수동 호출 필수. 마일스톤마다 호출 권장 |
| 마이그레이션 후 보존된 baby 의 turn-level 디테일 손실 | 낮음 | 옛 raw 로그가 sessions 와 다른 포맷 | 백업 (`.hamstern.bak.{ts}/baby-hamster/`) 가 영구 보존. 필요시 사용자가 수동 참조 |
| .deeptalk-running 마커 제거가 deeptalk/rule/why/skill-creator 의 핵심 행동에 영향 | 낮음 | 마커 set 단계가 사라져 다른 동작 변화 | 그 마커는 hook 침묵 전용 — hook 제거됨으로 마커 자체 무의미. 단순 step 삭제만 |

## 롤백

- 한 작업 = 한 commit. Sub-A/B 와 동일 정책
- 자동 마이그레이션 commit 이전이면 git revert 로 path 변경 무효화
- 마이그레이션 후 백업 (`.hamstern.bak.{ts}/`) 이 영구 보존 — 사용자가 옛 구조로 수동 복원 가능
- Sub-A 와 Sub-B 의 commits 은 그대로 유지 (history)

## Definition of Done

- [ ] hooks/ 디렉토리 전체 삭제됨 (`Test-Path hooks` → False)
- [ ] skills/start/, skills/stop/ 디렉토리 전체 삭제됨
- [ ] skills/dashboard/scripts/aggregate.py 삭제됨
- [ ] `skills/record/SKILL.md` 의 Step 1 에 마이그레이션 로직 + Step 4 dual-write 명시
- [ ] `skills/record/test_record_format.py` 의 dual-write + 마이그레이션 케이스 그린
- [ ] `skills/remind/SKILL.md`, `skills/audit-decisions/SKILL.md`, `skills/dashboard/SKILL.md`, `skills/dashboard/server.py`, `skills/dashboard/static/*` 의 path 갱신 완료
- [ ] `skills/deeptalk/SKILL.md`, `skills/rule/SKILL.md`, `skills/why/SKILL.md`, `skills/skill-creator/SKILL.md` 의 `.deeptalk-running` set/unset 단계 삭제
- [ ] `docs/conventions.md` 새 2-tier 구조로 전면 개정
- [ ] `.claude-plugin/marketplace.json` 에서 start, stop 제거
- [ ] `README.md` 의 hooks/start/stop/mom 관련 섹션 제거 + 새 워크플로우 문서화 + 신규 changelog 항목
- [ ] `pytest skills/record/` 그린 (hooks/ 는 사라졌으니 test 대상에서 제외)
- [ ] `Select-String -Path "skills\**\*.md","skills\**\*.py","skills\**\*.html","docs\conventions.md" -Pattern "baby-hamster|boss-hamster|mom-hamster|deeptalk-running|\.disabled"` 결과 0 건 (사용자 README 의 changelog history 만 예외)
- [ ] Layer 3 manual 검증 6단계 verification.md 작성 (시나리오 1-6, 슬래시 명령 시나리오는 사용자 첫 호출 시 갱신)

## 다음 단계

Sub-D — Dashboard 재설계:
- github.io static + 크로스 머신 viewer
- 브라우저에서 결정 토글·편집 UI
- 방향: 정적 사이트 + Claude 세션에서 audit/edit (diary 스킬과 같은 패턴)
- record 가 commit·push 하면 GitHub Pages 자동 빌드 → 모든 컴에서 최신 dashboard 보임

Sub-D 는 별도 brainstorming → spec → plan → implementation 사이클.
