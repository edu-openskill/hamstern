---
name: context-save
description: |
  현 세션의 작업 컨텍스트를 다음 세션이 이어갈 수 있는 핸드오프 문서로 저장.
  결정사항과 세션의 상세 narrative를 함께 보존. /compact의 압축력 + gstack의 구조화 + ADR 스타일 풍부한 결정 기록의 결합.
  --full 플래그로 전체 세션 narrative(시간순, 사용자 발언 인용 포함)까지 저장.
  사용법:
    /hams:context-save                # 기본 5섹션 저장
    /hams:context-save "제목"          # 제목 지정
    /hams:context-save --full          # ⑥ 세션 상세까지 추가 (deeptalk 같은 사고흐름 보존용)
    /hams:context-save --no-parent     # 이전 세션 자동 link 끊기
    /hams:context-save --yes           # 결정 후보 확인 단계 skip
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# /hams:context-save

현 세션의 작업 컨텍스트를 다음 세션 / 다른 컴퓨터 / 미래 자신이 이어갈 수 있게 저장.

## 설계 철학 (왜 이 구조인가)

세 함정을 피한다:

| 함정 | 결과 |
|------|------|
| literal transcript 저장 | restore 시 컨텍스트 윈도우가 다 차서 작업 못함 |
| 결정 한 줄만 저장 (옛 record) | 결정에 도달한 사고·맥락·뉘앙스가 사라짐 |
| 순수 narrative만 (gstack 모방) | 결정의 "왜·대안·함의"가 압축에 묻혀 다음 세션이 재발굴 필요 |

**해법: 한 단락 narrative + ADR-style 풍부한 결정 = handoff 가능한 최소 컨텍스트.**
`--full` 모드에서는 시간순 detailed narrative까지 ⑥에 추가 (deeptalk처럼 사고 흐름 자체가 가치인 세션 보존용).

## 파일 형식 (5 섹션 + 옵션 ⑥)

```markdown
---
status: in-progress | completed
project: {name}
session_id: 20260530-114500-design-talk
timestamp: 2026-05-30T11:45:00Z
duration: 02:43
mode: default | full
related_artifacts:
  - 경로 1
  - 경로 2
parent_session: 20260530-100000-init   # 자동 (있으면), --no-parent로 끊기
---

# Session: {title}

## ① 맥락 요약
{1~3 단락. /compact 스타일의 압축 narrative.
"무엇을 작업했고, 어디 분기점이 있었고, 지금 어디 있는가" 명사 위주.
다음 세션이 이 단락만 읽고도 이어 작업 가능해야 함.}

## ② 결정사항 (ADR-style)

### D1. {결정 제목}
- **결정**: {무엇을 정했는가 — 구체적으로}
- **논의 맥락**: {이 결정에 도달하기 전 무엇을 논의했는가 — 압축}
- **왜 이것이고 대안이 아닌가**: {비교 대안 + 왜 그 길은 안 가는가}
- **함의**: {다음 작업에 무엇을 의미하는가 — 파일 변경·룰 추가 등}
- **참조**: {관련 artifacts·외부 링크·이전 결정 ID}

### D2. ...

## ③ 미정 사항
- {미정 항목} (왜 미정인가)

## ④ 다음 작업
1. {구체적·행동 가능한 진입점 — 가이드: "X 파일에 Y 추가" 같은 동사형 권장}
2. ...

## ⑤ 참조
- 갱신/생성된 artifacts (`_workspace/series-bible.md` 등)
- 외부 링크
- parent_session: 이전 세션 ID (frontmatter 중복이지만 가독성용)

# --full 모드일 때 추가:
## ⑥ 세션 상세
{시간순 5~15 단락 narrative. 대화의 결정적 순간 + 사용자 발언 인용 + 사고 분기점.
이 섹션은 model이 읽어도 좋고 사람이 읽어도 좋도록 prose로 작성.}
```

## Claude 실행 절차

### Step 1: active project + 인자 파싱

```bash
TITLE=""
FULL=0
YES=0
NO_PARENT=0
for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    --yes) YES=1 ;;
    --no-parent) NO_PARENT=1 ;;
    *) [ -z "$TITLE" ] && TITLE="$arg" ;;
  esac
done

ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
[ ! -f "$ACTIVE_CONFIG" ] && { echo "❌ active project 없음. /hams:link or /hams:init 먼저." >&2; exit 1; }
UUID=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['uuid'])")
NAME=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['name'])")
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
PROJ_DIR="$HAMSTERN_DATA/projects/$UUID"
SESS_DIR="$PROJ_DIR/sessions"
mkdir -p "$SESS_DIR"
```

### Step 2: parent_session 자동 감지

`--no-parent` 없으면, sessions/ 디렉토리에서 가장 최근 파일을 찾아 그 session_id를 parent로 설정.

```bash
PARENT=""
if [ "$NO_PARENT" = "0" ]; then
  # filename YYYYMMDD-HHMMSS 정렬, 가장 최근 1개
  LATEST=$(find "$SESS_DIR" -maxdepth 1 -name "*.md" -type f 2>/dev/null | sort -r | head -1)
  if [ -n "$LATEST" ]; then
    PARENT=$(basename "$LATEST" .md)
  fi
fi
```

### Step 3: Distill — 5 섹션 생성 (현 세션 대화에서)

지금까지의 대화를 바탕으로 다음 섹션들을 작성:

**① 맥락 요약 (1~3 단락)** — 가장 중요한 새 섹션
- /compact 스타일
- 작업 정체성 + 사고의 결정적 분기점 + 현재 위치
- 명사 위주, 압축적, deictic 표현 금지 (구체 참조로)
- 목표: 다음 세션이 이 단락만 읽고도 즉시 이어 작업 가능

**② 결정사항 (ADR 5필드)**
- 각 결정마다: 결정 / 논의 맥락 / 왜 대안이 아닌가 / 함의 / 참조
- 한 줄 요약 금지. 결정당 한 단락 + 메타데이터.
- 카테고리는 Architecture / Other 등으로 머릿단에 표기 (옛 record와 동일)

**③ 미정 사항**
- 명확히 미정인 것만. "왜 미정"이 가장 중요.

**④ 다음 작업 (번호 매김)**
- 첫 항목은 동사형·구체적 권장 (강제는 X, 가이드)
- 예: "series-bible.md에 4층 모델 다이어그램 추가"
- 안 좋은 예: "시리즈 작업 계속"

**⑤ 참조**
- 이 세션이 갱신·생성·참조한 파일 경로
- parent_session ID (있으면)

`--full` 모드일 때 추가:

**⑥ 세션 상세 (5~15 단락)**
- 시간 순서 narrative
- 결정적 순간 + 사용자 발언 인용
- prose 형식, 압축 X (deeptalk 보존용)

### Step 4: 사용자 확인 (--yes 없으면)

만든 결정/미정/다음 작업 후보 목록을 사용자에게 보여주고 drop할 항목 받기.

```
=== 후보 ===
[Decisions]
D1. ...
D2. ...
[Open]
O1. ...
[Next]
N1. ...

drop할 번호를 쉼표로 (없으면 enter):
```

### Step 5: 파일 작성

`$SESS_DIR/{SESSION_ID}.md`에 위 형식으로 저장. `SESSION_ID`는 timestamp + title slug:

```bash
TS=$(date -u +%Y%m%d-%H%M%S)
# title sanitize
RAW="${TITLE:-untitled}"
TITLE_SLUG=$(printf '%s' "$RAW" | tr '[:upper:]' '[:lower:]' | tr -s ' \t' '-' | tr -cd 'a-z0-9.-' | cut -c1-60)
TITLE_SLUG="${TITLE_SLUG:-untitled}"
SESSION_ID="${TS}-${TITLE_SLUG}"
SESS_PATH="$SESS_DIR/$SESSION_ID.md"
# collision 방지
if [ -e "$SESS_PATH" ]; then
  SUFFIX=$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom 2>/dev/null | head -c 4)
  SESSION_ID="${TS}-${TITLE_SLUG}-${SUFFIX}"
  SESS_PATH="$SESS_DIR/$SESSION_ID.md"
fi
```

### Step 6: decisions.md 갱신 (결정사항만 append)

각 D 결정의 ADR 5필드 중 **"결정"과 "이유(=왜 대안이 아닌가)"** 만 추려서 카테고리별 append. Jaccard 0.7 dedup. session marker 포함.

**마커 형식:** `<!-- session: {SESSION_ID}#{D번호} -->` — `#{D번호}` 는 이 결정이 그 세션 ②결정사항의 **몇 번째 ADR(D1, D2…)** 인지(1-based). 대시보드가 결정 클릭 시 세션 distill 의 정확한 `### D{n}` 블록으로 스크롤하는 데 쓴다. (`#` 뒤 숫자는 `\S+?` 한 토큰 안이라 remove.py 의 마커 strip 과 호환. 공백 넣지 말 것.)

```markdown
## {카테고리}
- {결정1} — {왜 이것이고 대안이 아닌가 요약} <!-- session: {SESSION_ID}#1 -->
- {결정2} — {…} <!-- session: {SESSION_ID}#2 -->
```

`{D번호}` 는 sessions/{id}.md ②결정사항의 D 순번과 **반드시 일치**시킨다 (카테고리 그룹핑과 무관하게 ADR 작성 순서 기준). 전체 ADR detail은 sessions/{id}.md에만 보존.

### Step 7: decisions-log.md append-only 이력

```markdown
## {YYYY-MM-DD HH:MM} · session {SESSION_ID}
+ [결정] {D1 제목}
+ [결정] {D2 제목}
+ [미정] {O1}
+ [다음] {N1}
```

### Step 8: _index.json + git commit + push

(record와 동일)

### Step 9: 사용자 보고

```
✅ CONTEXT SAVED
════════════════════════════════════════
프로젝트:    {project}
제목:        {title}
Session ID:  {SESSION_ID}
Mode:        {default | full}
Parent:      {parent_session or "none"}
파일:        {SESS_PATH}
Decisions:   {N}건 → decisions.md 갱신
Next steps:  {M}건
════════════════════════════════════════
다음 세션 시작 시 /hams:context-resume 으로 이어가기.
```

## 이전 버전과의 호환

- 옛 `record` 스킬은 deprecated. context-save가 모든 기능 + 더 풍부함.
- record로 저장된 sessions 파일도 context-resume이 그대로 읽음 (frontmatter mode 필드 없으면 'legacy'로 처리).
- decisions.md 포맷은 동일 (append 호환).

## 작성 자체 검증 가이드

자체 검증을 위해 이 스킬로 저장한 세션 자체에 다음이 있는지 확인:
- [ ] ① 맥락 요약이 한 단락에 작업 정체·분기점·현재 위치 모두 포함하는가
- [ ] ② 각 결정이 ADR 5필드 모두 채워졌는가
- [ ] ② 결정의 "왜 대안이 아닌가"가 한 줄 이상 구체적인가
- [ ] ④ 다음 작업 첫 항목이 동사형·구체적인가
- [ ] ⑤ 참조에 갱신된 artifacts가 모두 나열되었는가
- [ ] (--full시) ⑥ 세션 상세가 시간순이고 사용자 인용 포함하는가
- [ ] parent_session이 자동 연결되었는가 (해당시)
