# hamstern 재설계 플랜 — 핸드오프/캡처 일관화 (상세판)

> 작성: 2026-05-22 · 성격: **계획 전용**(코드 미구현, CLI에서 단계별 실행용 명세)
> 목표: 캡처·결정 핸드오프를 **CLI·Cowork 일관 동작**(챗은 우아한 폴백) + 결정 저장소 **무한 성장 방지**(계층 메모리). v1.0 = **명시적 호출(수동)**, 자동화는 경험 후.

## 이 플랜을 CLI(Claude Code)에서 쓰는 법
1. `cd <hamstern-plugin repo>` 후 Claude Code 실행.
2. 이 파일을 컨텍스트로 주고 **Phase 0 → 1**부터 순서대로. 각 Phase의 "검수 기준"을 통과하면 다음 Phase.
3. 각 Phase는 독립 배포 가능하게 설계됨. 결정/이유는 `/hams:why` 또는 `/hams:record`(생성 후)로 남길 것.
4. 변경은 작은 커밋으로(= 결정 히스토리). 결정은 사람이 소유, 에이전트는 diff 제안.

---

## 0. 설계 원칙 (모든 Phase 공통, 위반 시 리뷰 반려)

P1. **일관성 = 같은 저장소(경로·포맷)**, "같은 캡처 방식"이 아님. 입구 셋(hook=CLI자동 / record=어디서나 수동 / dashboard=정리·확정) → 종착지 하나: `{project_root}/.hamstern/boss-hamster/decisions.md`(+`decisions-log.md`).
P2. **포터블 경로:** project_root = `git rev-parse --show-toplevel` → 실패 시 `pwd`. 쓰기는 **project_root 하위에만**(Cowork 샌드박스는 마운트 밖 차단). 번들 자산은 `{baseDir}`(스킬 상대경로). 마크다운 SKILL.md에서 `${CLAUDE_PLUGIN_ROOT}`·절대경로 **금지**.
P3. **환경감지 = 능력 프로브.** "CLI/Cowork/챗" 구분 env 변수는 미문서. 파일 쓰기를 try → 실패(FS 없음, EACCES/ENOENT)면 **텍스트 폴백**. `CLAUDE_CODE_REMOTE`는 원격 표시일 뿐 서피스 구분 아님 → 의존 금지.
P4. **타입으로 분리:** 불변식 → 룰/테스트, 사건/결정 → 계층 메모리, 열린 질문 → 작은 hot 목록.
P5. **사람이 소유:** 결정/강등은 사람 확인, AI는 diff만. 강등 = 이동(삭제 아님, 되돌림 가능).
P6. **hook ≠ record:** hook(dumb python)=원본 append(baby/mom), record(모델 필요)=증류 결정(decisions.md). 서로 호출하지 않음, *저장소 포맷*만 공유.
P7. **배포:** 단일 `.claude-plugin/marketplace.json`(존재). 서피스별 매니페스트 없음.

### 표준 저장소 레이아웃 (확정)
```
{project_root}/.hamstern/
  boss-hamster/
    decisions.md        # HOT: 현재 상태(카테고리별, 상한 있음)   ← record/dashboard 공동
    decisions-log.md    # COLD: append-only 전체 이력 = 결정 히스토리
    decisions-index.md  # INDEX: 아카이브 1줄 요약(날짜·토픽·포인터)  (Phase 3 신규)
  baby-hamster/         # 원본 턴 로그 (hook 전용, CLI)
  mom-hamster/          # 요약 (aggregate, CLI)
  why/
    rules/{topic}.md    # 잠정 룰
    tests.md            # 테스트 경로 기록 (why 라우팅, 이미 도입)
{project_root}/.claude/rules/{topic}.md (+references/)   # 영구 룰(자동 로드)
```

### 공통 의사코드 — 경로/프로브 (Phase 0 산출, 모든 스킬이 참조)
```
resolve_root():
  r = $(git rev-parse --show-toplevel) ; if fail: r = $(pwd)
  return r
ensure_store(r):
  try mkdir -p r/.hamstern/boss-hamster
  on fail (no FS) -> FALLBACK_TEXT mode
store_paths(r): decisions=r/.hamstern/boss-hamster/decisions.md ; log=...decisions-log.md ; index=...decisions-index.md
```

---

## Phase 0 — 공통 규약/코어 (행동 변화 없음)

**목표:** 모든 스킬이 쓸 포터블 규약·헬퍼 확정.

**변경 파일**
- 신규 `skills/_core/PATHS.md` (또는 `docs/conventions.md`): 위 표준 레이아웃 + 경로/프로브 의사코드 + 포맷 스펙을 한 곳에 문서화.
- (선택) 신규 `skills/_core/store.sh`: `resolve_root`, `ensure_store`, `append_log`, `merge_decision` 같은 공유 bash 헬퍼. *주의:* 챗 폴백을 위해 핵심 I/O는 모델의 Read/Write 도구로도 가능해야 함 — `store.sh`는 CLI/Cowork 가속용, 필수 의존 아님.

**검수 기준**
- [ ] resolve_root가 git repo와 비-git 디렉토리 둘 다에서 올바른 경로 반환.
- [ ] FS 없는 환경 시뮬레이션 시 FALLBACK_TEXT로 분기.
- [ ] 문서에 decisions.md/log/index 포맷 예시 포함.

---

## Phase 1 — `record` 스킬 (수동 베이스라인) ★ v1.0 핵심

**목표:** 어디서나 도는 수동 캡처로 Cowork 공백을 메움. dashboard와 같은 저장소.

**신규 파일:** `skills/record/SKILL.md` (+ 선택 `skills/record/record.sh`)

**SKILL.md frontmatter**
```
name: record
description: 지금 세션의 결정·실패·열린질문을 정리해 프로젝트 결정 저장소(decisions.md)에 기록 — CLI·Cowork 동작, 챗은 텍스트 폴백
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
```

**동작 단계(SKILL.md 본문에 명시)**
1. `resolve_root()` → `ensure_store()`. 실패 시 5번(텍스트 폴백).
2. **distill:** 현재 세션(에이전트 컨텍스트)에서 ① 결정(+이유) ② 실패·폐기(이유) ③ 열린 질문 후보 추출. *원본 턴 로그는 만들지 않음*(그건 hook).
3. **확인:** 후보를 사용자에게 표로 제시(`AskUserQuestion` 또는 출력 후 확인). 헛것 방지. (옵션 `--yes`로 생략 가능하나 기본은 확인)
4. **병합 기록:**
   - `decisions.md` 읽기 → 카테고리별 병합(같은 항목 **중복 제거**; 세션 마커로 같은 세션 재호출 시 갱신 = idempotent).
   - `decisions-log.md`에 타임스탬프 블록 **append**.
5. **텍스트 폴백(챗):** FS 쓰기 불가 시 동일 마크다운을 채팅 출력 → 사용자 복붙. (포맷 동일 → 나중에 같은 저장소로 수렴)

**decisions.md 포맷 (dashboard 호환)**
```
# 프로젝트 결정사항
## {카테고리}
- {결정} (이유: {왜})
## 실패·폐기 (왜 안 했나)
- {시도} → 폐기: {이유}
## 열린 질문
- {미정 사항}
```
**decisions-log.md 블록**
```
## {YYYY-MM-DD HH:MM} · session {id}
+ [결정] {…}
+ [실패] {…}
+ [열림] {…}
```

**엣지/안전장치**
- idempotent: 세션 id 마커로 재호출 = 추가 아닌 갱신. CLI에서 hook과 병행 시 내용 중복 제거.
- `.hamstern/` 부재 시 자체 생성(= start 미실행도 동작).
- 마일스톤마다 호출 권장(긴 세션 끝 1회만 하면 compaction 손실).

**검수 기준**
- [ ] CLI·Cowork에서 동일 입력 → 동일 decisions.md 결과.
- [ ] 같은 세션 2회 호출 → 중복 항목 없음(갱신).
- [ ] FS 차단 시 텍스트 폴백 출력.
- [ ] 기록된 항목이 dashboard에서 그대로 읽힘(포맷 호환).

---

## Phase 2 — `why`/`rule` 라우팅 완성

**목표:** 교훈을 "테스트(검증 가능) vs 룰(판단)"로 라우팅 → 룰/결정 무한 증식 방지.

**상태:** `why/SKILL.md`에 **Step 4.5 라우팅 + Step 5-T(테스트 경로) 이미 적용 완료.**

**변경 파일:** `skills/rule/SKILL.md`
- `/hams:rule add` 진입부에 **라우팅 가드** 한 단계 추가: "이 규칙이 기계로 검증 가능한가?" → 가능하면 "테스트로 빼는 게 낫습니다"(Step 5-T 동일 안내, `.hamstern/why/tests.md` 기록) 제안, 판단이면 기존 룰 생성 진행.
- `why`의 라우팅 문구와 일관되게.

**검수 기준**
- [ ] `/hams:rule add`에서 검증 가능한 규칙 입력 시 테스트 경로를 먼저 제안.
- [ ] 판단형 규칙은 기존대로 `.claude/rules/`에 생성.

---

## Phase 3 — 결정 저장소 계층 메모리 (무한 성장 방지)

**목표:** "지금 필요한 것만 hot, 나머지는 cold로 옮기고 필요 시 회수."

**신규/변경**
- 신규 `decisions-index.md` 유지(아카이브 단서).
- `record`에 강등 제안 추가, 또는 신규 `skills/compact/SKILL.md`(`/hams:compact`).

**강등(demotion) 알고리즘 (사람 확인·되돌림 가능)**
```
on record/compact:
  if size(decisions.md) > BUDGET:           # BUDGET = 토픽당 N개 or 총 토큰/마일스톤(Phase3에서 실측 확정)
    candidates = decisions where (오래됨 AND not 열린질문 AND not 룰화됨)
    superseded = decisions marked "→ 대체됨"
    propose diff: move (candidates + superseded) → cold
    on user confirm:
      append moved items to decisions-log.md (이미 있으면 유지)
      add 1-line each to decisions-index.md (날짜·토픽·로그 포인터)
      remove from decisions.md (열린질문은 절대 제거 금지)
```
**index 라인 포맷**
```
- {YYYY-MM-DD} {topic}: {한 줄 요약}  → log#{anchor or 날짜블록}
```
**회수(just-in-time)**
- 세션 시작: hot(decisions.md) + index만 로드.
- 토픽 닿으면: index 스캔 → 관련 항목을 `grep`으로 cold(log)에서 끌어옴.

**안전장치**
- 강등 = 이동(삭제 아님): log+index 보존 → 되돌림 가능.
- index 품질(제목·태그)이 회수 성패 좌우 → distill 시 토픽 태깅 신경.
- v1: **자동 강등 금지**, 항상 diff 제안 후 사람 확인.

**검수 기준**
- [ ] 상한 초과 시 강등 diff가 제안됨.
- [ ] 강등 후 decisions.md는 상한 내, 항목은 index→log로 회수 가능.
- [ ] 열린 질문은 강등되지 않음.

---

## Phase 4 — 청중별 3 사이트 분리 (DRY)

**목표:** 공개범위로 가른 세 목적지, 캡처 코어·발행 엔진 공유.

| 스킬 | 청중/공개 | 내용 | 목적지 |
|---|---|---|---|
| `diary`(기존) | 공개 독자 | 다듬은 산문 | 공개 repo + Pages + giscus |
| `dashboard`(기존) | 나+팀+AI(비공개) | 결정사항 | `.hamstern/.../decisions.md` |
| `chat`(신규) | 나(비공개) | 대화 다이제스트 | diary 파이프라인 → **비공개 repo** |

**신규 파일:** `skills/chat/SKILL.md`
- record 코어 재사용으로 대화 distill → diary 빌드 파이프라인(템플릿/posts.json/MD→HTML)을 **비공개 repo·미니 템플릿**으로 점프.
- 정의는 "claude.ai 앱"이 아니라 "**비공개 대화 정리**"(어디서나 트리거, 챗은 텍스트 폴백 → 발행은 FS 있는 곳에서).

**수정:** `skills/diary/SKILL.md` — 설정 `~/.claude/hams-diary.json`(홈)은 Cowork 샌드박스 차단. → 프로젝트 내 설정으로 옮기거나 "Cowork 미지원" 명시 + 폴백.

**검수 기준**
- [ ] 세 목적지가 분리(공개/핸드오프/개인 비공개).
- [ ] `chat`이 record 코어·diary 파이프라인을 재사용(중복 구현 없음).
- [ ] diary 설정이 Cowork에서 깨지지 않거나 명확히 안내됨.

---

## Phase 5 — 자동화 (보류, 경험 기반)

**원칙:** v1(0~4) 사용 후 "무엇을 자동화할지"를 데이터로 결정. 섣부른 자동화 금지.

**후보(미착수)**
- hook을 CLI 자동 트리거(원본 baby/mom)로 정리·유지.
- 호스트측 **transcript-watcher 데몬**: `~/.claude/projects`(CLI), `…/local-agent-mode-sessions/.../.claude/projects`(Cowork)의 jsonl을 tail → record 코어로 무인 캡처. ⚠️ 내부 경로/포맷 의존(취약), 컴패니언 설치·자동시작·권한·프라이버시 고려. 챗은 불가.
- GitHub Actions로 Pages 자동 빌드.
- 테스트 치팅 방지(에이전트가 테스트 약화 못 하게)를 stop hook 게이트로.

---

## 교차 수정 항목
- diary 홈-경로 → 프로젝트 내 (Phase 4).
- `rule` 라우팅 가드 (Phase 2).
- 모든 신규/수정 스킬: 능력 프로브 + 텍스트 폴백, `{baseDir}`, git-root 경로 (Phase 0 규약).

## 열린 질문
- `record` hot 상한 기준(개수 vs 토큰 vs 마일스톤) — Phase 3 실측 후 확정.
- chat 비공개 repo 1개 고정 vs 프로젝트별 — Phase 4에서.
- 테스트 치팅 방지 강제 위치(hook 게이트) — Phase 5.
- (별개 프로젝트) 강의 게임 메타포: 스타크래프트 vs 포켓몬.

## 권장 착수 순서
**Phase 0 → 1** (= v1.0 핵심) → **2** → **3** → **4** → (경험 후) **5**.

## 의존성 그래프
```
0 ──> 1 ──> 3
 └──> 2      
 └──> 4 (chat은 1의 코어 + diary 의존)
5 는 1~4 사용 경험 후
```
