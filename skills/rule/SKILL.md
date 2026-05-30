---
name: rule
description: 영구 적용할 프로젝트 룰 관리 — 등록(add)·조회(list)·수정(edit)·삭제(remove)·잠정 why-룰 격상(promote).
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# /hams:rule

프로젝트 영구 룰 관리 멀티커맨드 스킬. 사용자가 확신하는 원칙을 `.claude/rules/`에 직접 등록하거나, 기존 룰을 조회/수정/제거/격상한다.

자세한 데이터 스키마·포맷·경로 규약은 [`docs/conventions.md`](../../docs/conventions.md) 참조 (룰 2-경로 영구/잠정은 §9).

> **`project_root`**: 현재 git 루트 디렉토리 (`git rev-parse --show-toplevel` 결과). git 외부면 `cwd`.
>
> **두 가지 메모리 위치:**
> - `{project_root}/.claude/rules/{topic}.md` — 포인터 (Claude Code 자동 로드, 5~7줄)
> - `{project_root}/.claude/rules/references/{topic}/` — 본문 (rule.md, examples.md, [선택] mockup.html, history.md, lazy)

## 서브커맨드 라우팅

호출 시 첫 인자로 서브커맨드를 받는다. 인자 없이 호출되면 도움말 출력 후 종료.

| 인자 | 동작 |
|------|------|
| `add` | 현재 대화 컨텍스트에서 룰을 추출해 신규 등록 → §`add` 절 |
| `list` | 현재 등록된 모든 룰을 표로 출력 → §`list` 절 |
| `edit {topic}` | 지정 룰의 포인터 + references 파일을 표시 후 사용자 지시대로 수정 → §`edit` 절 |
| `remove {topic}` | 지정 룰 전체 삭제 (포인터 + references 폴더) → §`remove` 절 |
| `promote {topic}` | `.hamstern/why/rules/{topic}.md` 를 영구 룰로 수동 격상 → §`promote` 절 |
| (없음 또는 `help`) | 위 표 출력 후 종료 |

서브커맨드 식별 후 해당 절의 워크플로우만 실행한다. 다른 절은 무시.

## 공통 동작

### 템플릿 위치

플레이스홀더 채우기 패턴은 `{plugin_root}/skills/rule/templates/` 의 5개 파일 사용. SKILL.md 기준 상대 경로로는 `./templates/` (같은 디렉터리).

### topic 식별자 규칙

- 영어 kebab-case 명사구
- 도메인을 직관적으로 표현
- 예: `ui-alignment`, `table-header-layout`, `data-collection`, `naming-consistency`
- snake_case·camelCase·공백·한글 금지

신규 등록 시 Claude가 자동으로 topic을 제안하되, 사용자가 거부할 수 있어야 함.

---

## §add — 대화 컨텍스트에서 신규 룰 등록

호출 즉시 다음 단계를 순서대로 수행한다.

### Step A1: 컨텍스트 추출

현재 세션의 다음 정보를 분석한다.

- 사용자 발화 (최근 N턴 — 최소 패턴이 도출되기 시작한 지점부터)
- 대화 중 등장한 코드 스니펫 (Bash/Edit/Write/Read 결과 또는 사용자가 붙여넣은 코드)
- 사용자가 강조한 제약·원칙 (예: "왼쪽엔 검색, 오른쪽엔 정렬", "캐시 먼저 확인", "이름은 동사+명사")
- 작업 도메인 (어떤 파일/컴포넌트/모듈에서 패턴이 도출됐나)

다음을 도출:
- **원칙 후보** — 한 문장
- **적용 트리거 후보** — 어떤 작업/키워드에서 발동
- **타입 후보** — 코드 / 디자인 / 둘 다 (Step A2 판정 휴리스틱)
- **결과물 후보** — 코드 스니펫(올바른/잘못된)과/또는 HTML 마크업

컨텍스트가 비어 있어 위 정보를 추출할 수 없으면, 폴백:
> "최근 대화에서 패턴을 추출할 수 없습니다. 어떤 원칙을 등록할지 직접 알려주세요."
이후 사용자가 자유 텍스트로 원칙·트리거·예시를 제공 → Step A3로 진행.

### Step A2: 타입 자동 판정 (휴리스틱)

다음 키워드/신호 비율로 결정:

| 신호 | 타입 |
|------|------|
| HTML 태그, CSS 속성, className, Tailwind, layout, flex, grid, padding, margin, color, font, 정렬, 여백, mockup, UI, 컴포넌트 시각 배치 | 디자인 |
| function, async, await, return, API, fetch, query, algorithm, 데이터 흐름, validation, 상태 관리, 캐시, 검증 로직 | 코드 |
| 양쪽 신호 모두 강함 (예: 디자인 시스템 + 함수 시그니처) | 둘 다 |

기본값: 모호하면 **코드**.

판정 결과는 1차 초안에 명시적으로 표시 → 사용자가 거부 가능.

### Step A3: 1차 초안 미리보기

다음 형식으로 초안을 화면에 출력한다 (파일은 아직 안 만듦):

```
다음 룰을 만들려고 합니다:

  topic       : table-header-layout
  원칙        : 테이블 헤더는 좌상=검색/필터, 우상=정렬/액션으로 분리한다
  적용 트리거 : Table/DataGrid/List 컴포넌트 작성 시
  타입        : 디자인 (mockup.html 포함)
  결과물      : 
    ✅ 좋은 예시 — ProjectsTable.tsx 의 헤더 패턴 (코드 + HTML mockup)
    ❌ 나쁜 예시 — 정렬이 좌측·검색이 중앙인 배치

이 내용으로 진행할까요?
```

### Step A4: 검수 루프 (`AskUserQuestion`)

옵션 4개:

1. **이대로 진행** → Step A5
2. **수정할 게 있어요** → 사용자가 자유 텍스트로 수정 지시 → Step A1~A3 다시 (영향받는 부분만 갱신, 그대로인 건 유지) → 다시 Step A4
3. **타입 변경** → "코드 / 디자인 / 둘 다" 중 선택 → A3 재출력 → A4 재진행
4. **취소** → 마커 OFF 후 종료. 아무것도 저장하지 않음.

검수 루프는 최대 5회까지 (사용자가 5회 이후에도 미확정이면 "현재 초안으로 저장 / 취소" 양자택일로 좁힘).

### Step A5: 적용 범위 질문 (`AskUserQuestion`)

```
적용 범위를 선택하세요:
1. 전역 (모든 작업에서 항상 로드)
2. 특정 경로 한정 (예: src/components/**, src/api/**)
```

옵션 2 선택 시 후속 질문: "어떤 경로 글로브를 사용할까요? (쉼표로 여러 개 가능)" → 사용자 입력을 그대로 paths frontmatter에 넣음.

### Step A6: topic 식별자 결정

Step A3 초안의 topic을 그대로 쓰되, 다음 충돌 검사:

```bash
ls .claude/rules/{topic}.md 2>/dev/null
```

존재하면 `AskUserQuestion`:
1. 덮어쓰기
2. 새 이름 (사용자 입력)
3. 취소 → 마커 OFF, 종료

### Step A7: 파일 생성

순서:

```bash
mkdir -p .claude/rules/references/{topic}
```

각 파일 생성 (Read로 템플릿 읽고, 플레이스홀더 치환 후 Write):

#### 1. 포인터 `.claude/rules/{topic}.md`

`./templates/pointer.md` 읽기. 다음 플레이스홀더 치환:

- `{{paths_frontmatter}}` →
  - 전역이면 빈 문자열 `""`
  - 특정 경로면 다음 (마지막 빈 줄 1개 포함):
    ```
    ---
    paths:
      - "src/components/**"
    ---
    
    ```
  - 글로브 여러 개면 `paths:` 아래에 `  - "..."` 라인 여러 개.
- `{{title}}` → 한국어 원칙명
- `{{principle}}` → 한 문장 원칙
- `{{trigger}}` → 트리거 텍스트
- `{{references_list}}` → 단일 다중 라인 블록. 타입에 따라:
  - **코드 타입**:
    ```
      1. references/{topic}/rule.md
      2. references/{topic}/examples.md
    ```
    (`{topic}` 도 실제 값으로 치환)
  - **디자인 타입 또는 둘 다**:
    ```
      1. references/{topic}/rule.md
      2. references/{topic}/mockup.html
      3. references/{topic}/examples.md
    ```

치환 완료 후 Write.

#### 2. rule.md `.claude/rules/references/{topic}/rule.md`

`./templates/rule.md` 읽기. 치환:

- `{{title}}` → 한국어 원칙명
- `{{date}}` → 시스템 오늘 날짜 (`date +%F` 결과 또는 YYYY-MM-DD)
- `{{trigger_context}}` → Step A1에서 도출한 작업 도메인 한 줄 (예: "ProjectsTable.tsx 헤더 작업 중")
- `{{surface_cause}}` → 표면 증상 (사용자 강조 표현 그대로)
- `{{root_cause}}` → 원칙 수준 원인 (Claude 추론)
- `{{principle}}` → 한 문장 원칙
- `{{rationale}}` → 사용자가 언급한 근거 (없으면 비움 — 빈 문자열로 치환, 헤딩 `## 근거`는 유지)

치환 후 Write.

#### 3. examples.md `.claude/rules/references/{topic}/examples.md`

`./templates/examples.md` 읽기. 치환:

- `{{title}}` → 원칙명
- `{{lang}}` → 코드 추출에서 추론 (`tsx`, `ts`, `py`, `java`, …)
- `{{good_example}}` → 컨텍스트에서 도출한 올바른 패턴 코드
- `{{bad_example}}` → 잘못된 패턴 코드 (없으면 빈 문자열로 치환 → 헤딩과 코드 펜스가 빈 블록으로 남되 markdown은 깨지지 않음)
- `{{flow_section}}` → 코드 타입에서 흐름 다이어그램 있으면 다음 형태 문자열, 없으면 `""`:
  ```
  ## 흐름 (텍스트 다이어그램)
  
      요청 → 검증 → 처리 → 응답
  ```
- `{{found_in_section}}` → 다음 한 줄로 시작 (등록 시점 표기):
  ```
  ## 발견된 실제 사례
  - {파일경로} ({YYYY-MM-DD}) — 등록 시점
  ```
  파일경로는 컨텍스트에서 도출한 작업 도메인의 대표 파일 (예: `src/components/ProjectsTable.tsx`).

치환 후 Write.

#### 4. mockup.html `.claude/rules/references/{topic}/mockup.html` (디자인/둘 다 타입에만)

`./templates/mockup.html` 읽기. 치환:

- `{{title}}` → 원칙명
- `{{principle}}` → 원칙 한 문장
- `{{custom_css}}` → 룰별 CSS (필요 시 — 예: `.table-header { display: flex; justify-content: space-between; }`). 필요 없으면 빈 문자열.
  - **주의**: 사용자 제공 CSS에 `</style>` 시퀀스가 있으면 반드시 제거하거나 escape (HTML 안전성).
- `{{good_html}}` → 컨텍스트의 좋은 HTML 마크업
- `{{bad_html}}` → 잘못된 HTML 마크업 (없으면 빈 문자열)

치환 후 Write.

코드 타입이면 mockup.html을 만들지 않는다.

#### 5. history.md `.claude/rules/references/{topic}/history.md`

`./templates/history.md` 읽기. 치환:

- `{{title}}` → 원칙명
- `{{date}}` → YYYY-MM-DD
- `{{registration_path}}` → `"/hams:rule add (수동 등록)"`
- `{{discovery_log}}` → 한 줄 (등록 시점 진입):
  ```
  - **{date}** — {file_or_context}: 등록 시점 1차 패턴 도출
  ```
- `{{recurrence_log}}` → `(아직 없음)`

치환 후 Write.

### Step A8: 완료 메시지

출력:

```
✅ 룰 등록 완료
   포인터    : .claude/rules/{topic}.md
   본문      : .claude/rules/references/{topic}/
   적용 범위 : {전역 / paths: ...}
   타입      : {코드 / 디자인 / 둘 다}

▶ 다음 세션부터 자동으로 컨텍스트에 로드됩니다.
```

### Step A9: 자가검증

작성 직후 다음을 확인:
- `.claude/rules/{topic}.md` 가 5~10줄 사이인가? (포인터는 짧아야 함. paths frontmatter 포함 시 약간 더 길 수 있음)
- 디자인/둘 다 타입이면 `mockup.html` 이 실제로 존재하는가? (`test -f`)
- `references/{topic}/` 안에 `rule.md`, `examples.md`, `history.md` 가 있는가?
- 포인터의 frontmatter 가 paths 옵션 선택과 일치하는가? (전역이면 frontmatter 없음, 특정 경로면 `paths:` 항목 존재)
- 포인터의 `{{references_list}}` 가 코드 타입이면 2단계, 디자인/둘 다 타입이면 3단계 번호인가?

검증 실패 시 사용자에게 어떤 검증이 실패했는지 보고 + 작성한 파일 경로를 알려주고 마커 OFF 후 종료 (수동 정정 가능).

## §list — 등록된 룰 목록 출력

### Step L1: 룰 파일 수집

```bash
ls .claude/rules/*.md 2>/dev/null
```

대상은 `.claude/rules/` 직속 `.md` 파일만 (references/ 하위는 제외). 셸 글로브 `*.md` 는 직속만 매칭하므로 references/ 하위 파일은 자동으로 제외됨.

파일이 없으면 다음 메시지 출력 후 종료:

```
📂 등록된 룰이 없습니다.
   새 룰 등록    : /hams:rule add
   why로 시작    : /hams:why "...문제 설명..."
```

### Step L2: 각 포인터 파싱

각 파일에 대해 Read 호출하여 다음 추출:

- 파일명 → topic (확장자 제거)
- 본문에서 `## ` 헤더 라인 → 원칙명 (한국어 title)
- `**원칙:**` 라인 → 원칙 한 문장
- `**적용 트리거:**` 라인 → 트리거 텍스트
- frontmatter `paths:` 존재 여부 → 적용 범위 (전역 / paths 글로브 목록)
  - frontmatter가 없으면 → "전역"
  - `paths:` 항목이 있으면 → 글로브 모두 콤마로 연결 (예: `src/components/**, src/api/**`)

### Step L3: 표 출력

다음 형식으로 출력 (마크다운 표):

```
📋 등록된 룰 ({n}건)

| topic | 원칙 | 트리거 | 적용 범위 |
|-------|------|--------|-----------|
| table-header-layout | 헤더는 좌상=검색, 우상=정렬 | Table 작성 시 | 전역 |
| api-cache-first | API 호출 전 캐시 확인 | fetch/query 작업 시 | src/api/** |

상세 보기 : /hams:rule edit {topic}
삭제      : /hams:rule remove {topic}
```

원칙·트리거가 60자를 초과하면 60자에서 truncate하고 `…` 추가. topic·적용 범위는 truncate하지 않음 (식별자/경로는 정확해야 함).

## §edit — 룰 수정

### Step E1: topic 인자 검증

호출: `/hams:rule edit {topic}`

`{topic}` 인자가 없으면:
```
사용법: /hams:rule edit {topic}
현재 룰 목록은 /hams:rule list
```
출력 후 종료.

### Step E2: 파일 존재 확인

```bash
test -f .claude/rules/{topic}.md && test -d .claude/rules/references/{topic}
```

둘 중 하나라도 없으면:
```
❌ {topic} 룰을 찾을 수 없습니다.
   등록된 룰    : /hams:rule list
   잠정 룰 격상 : /hams:rule promote {topic}
```

### Step E3: 모든 관련 파일 표시

다음을 모두 Read 하여 사용자에게 코드 블록으로 노출:

- `.claude/rules/{topic}.md` (포인터)
- `.claude/rules/references/{topic}/rule.md`
- `.claude/rules/references/{topic}/examples.md`
- `.claude/rules/references/{topic}/mockup.html` (있을 때만 — `test -f` 로 확인)
- `.claude/rules/references/{topic}/history.md`

각 파일을 별도 코드 블록(언어 태그 포함: `markdown`, `html`)으로 출력하여 한눈에 보이게 한다. 그 다음 묻는다:

```
어디를 어떻게 수정할까요?
예) "원칙 문장을 'X'로 바꿔줘", "examples에 좋은 예시 코드 추가해줘", "paths를 src/api/**로 좁혀줘"
```

### Step E4: 사용자 지시 적용

사용자 응답을 받아 정확한 Edit 도구 호출로 변환. 한 번에 여러 파일 수정 가능. 모호한 지시(예: "그 부분 좀 더 명확하게")가 있으면:

> "다음을 수정합니다: ... 진행할까요?"

`AskUserQuestion`으로 1회 확인 후 진행.

### Step E5: 완료 메시지

```
✅ 룰 수정 완료
   수정된 파일:
     - .claude/rules/{topic}.md
     - .claude/rules/references/{topic}/rule.md (예시)
```

수정된 파일만 나열 (수정 안 한 파일은 메시지에 포함하지 않음).

## §remove — 룰 삭제

### Step R1: topic 인자 검증

호출: `/hams:rule remove {topic}`

`{topic}` 인자가 없으면 §edit Step E1 와 동일하게 사용법 출력 후 종료.

### Step R2: 존재 확인 + 삭제 대상 표시

```bash
test -f .claude/rules/{topic}.md
```

존재하지 않으면:
```
❌ {topic} 룰이 없습니다.
   현재 룰 목록 : /hams:rule list
```

존재하면 다음 출력 (mockup.html 유무는 `test -f` 로 확인하여 메시지에 반영):

```
다음을 삭제합니다:
  - .claude/rules/{topic}.md (포인터)
  - .claude/rules/references/{topic}/ (폴더 전체)
    └ rule.md, examples.md, [mockup.html], history.md
```

### Step R3: 확인 (`AskUserQuestion`)

옵션 2개:
1. 삭제 진행
2. 취소

### Step R4: 삭제

승인 시:

```bash
rm .claude/rules/{topic}.md
rm -rf .claude/rules/references/{topic}/
```

### Step R5: 완료 메시지

```
🗑️  {topic} 룰 삭제 완료
   포인터 + references 폴더 모두 제거됨
```

(연관된 `.hamstern/why/rules/{topic}.md` 가 있어도 건드리지 않음 — 그건 별개 자산이며, 사용자가 명시적으로 `/hams:rule promote` 로 다시 격상할 수 있어야 한다.)

## §promote — .hamstern/why/rules/ 에서 수동 격상

`/hams:why` 가 매칭하지 못했지만 사용자가 "이건 격상해야겠다" 싶을 때 명시적으로 트리거.

### Step P2: topic 인자 검증

호출: `/hams:rule promote {topic}`

`{topic}` 인자가 없으면:
```
사용법: /hams:rule promote {topic}
잠정 룰 목록 확인:
  ls .hamstern/why/rules/
```
출력 후 마커 OFF, 종료.

### Step P3: 원본 존재 확인

```bash
test -f .hamstern/why/rules/{topic}.md
```

없으면:
```
❌ .hamstern/why/rules/{topic}.md 가 없습니다.
   확인: ls .hamstern/why/rules/
```
마커 OFF, 종료.

### Step P4: 이미 격상됐는지 확인

원본 파일 첫 5줄에 `> 격상됨` 패턴이 있으면:
```
ℹ️  {topic} 은 이미 격상되었습니다.
   현재 위치: .claude/rules/{topic}.md
```
마커 OFF, 종료.

### Step P5: 원본 읽기 + 자동 분류

`.hamstern/why/rules/{topic}.md` 의 내용을 Read 하여 다음을 추출:

- `**표면 원인:**` 라인 → surface_cause
- `**근본 원인:**` 라인 → root_cause
- `**원칙:**` 라인 → principle
- `**트리거:**` 라인 → trigger_context (등록 당시 발견 계기)
- `**발견:**` 라인 → 첫 발견 날짜

타입 판정: 원본에 코드 스니펫이 있는지 확인.
- HTML/CSS/JSX 마크업이 있으면 → **디자인**
- 일반 코드만 있으면 → **코드**
- 둘 다 → **둘 다**
- 아무 코드도 없으면 → **코드** (기본)

### Step P6: 적용 범위 질문 (`AskUserQuestion`)

§add Step A5와 동일:
```
적용 범위를 선택하세요:
1. 전역 (모든 작업에서 항상 로드)
2. 특정 경로 한정 (예: src/components/**, src/api/**)
```

옵션 2면 후속 질문으로 글로브 입력 받음.

### Step P7: 파일 생성

§add Step A7 의 파일 생성 5개와 동일하지만 **입력 소스가 다름**:

- 원칙·표면 원인·근본 원인·trigger_context 는 `.hamstern/why/rules/{topic}.md` 에서 추출한 값 사용 (Step P5)
- `examples.md` 의 코드 예시는 원본에 코드 스니펫이 있으면 사용. 없으면 빈 문자열 치환 후 사용자에게 안내:
  ```
  ⚠️  좋은 예시 코드를 추가하려면 /hams:rule edit {topic} 를 사용하세요.
  ```
- `mockup.html` 은 디자인/둘 다 타입에서만 생성. 원본에 HTML 마크업이 있으면 사용, 없으면 placeholder 메시지를 `{{good_html}}` 에 넣음 (`<p>예시 마크업을 /hams:rule edit {topic} 로 추가해주세요.</p>`).
- `history.md` 의 치환:
  - `{{registration_path}}` → `"/hams:rule promote (수동 격상)"`
  - `{{discovery_log}}` → 원본의 발견 정보를 옮김 (Step P5의 `**발견:**` 날짜 + trigger_context)
  - `{{recurrence_log}}` → 원본에 재발 이력이 있으면 그것을 옮김, 없으면 `(아직 없음)`

치환 규칙(빈 문자열 처리, paths frontmatter 형식 등)은 §add Step A7 의 규칙을 그대로 따름.

### Step P8: 원본에 격상 마커 추가

`.hamstern/why/rules/{topic}.md` 의 맨 위에 다음 한 줄을 Edit으로 삽입한다.

삽입 위치:
- 파일에 frontmatter (---)가 있으면 frontmatter 종료(--- 닫기) 다음 빈 줄 뒤
- frontmatter가 없으면 첫 번째 헤딩(## 등) 직전

삽입할 줄:
```
> 격상됨 → .claude/rules/{topic}.md ({YYYY-MM-DD})
```

날짜는 시스템 오늘 날짜 (`date +%F`).

### Step P9: 완료 메시지

```
🚀 {topic} 영구 룰로 격상
   포인터    : .claude/rules/{topic}.md
   본문      : .claude/rules/references/{topic}/
   원본 마커 : .hamstern/why/rules/{topic}.md (격상됨 표시)

▶ 다음 세션부터 자동으로 컨텍스트에 로드됩니다.
```

### Step P10: 자가검증

§add Step A9 와 동일:
- `.claude/rules/{topic}.md` 가 5~10줄 사이?
- 디자인/둘 다 타입이면 `mockup.html` 존재?
- `references/{topic}/` 안에 rule.md, examples.md, history.md 존재?
- 포인터의 frontmatter 가 paths 옵션 선택과 일치?
- 원본 `.hamstern/why/rules/{topic}.md` 에 `> 격상됨` 라인이 추가됐나? (Step P8 검증)

검증 실패 시 어떤 검증이 실패했는지 보고 + 작성한 파일 경로 알려주고 마커 OFF 후 종료.

## Common Mistakes

- **`/hams:rule add` 호출 시 컨텍스트가 비어 있는데도 진행** → 1차 초안이 의미 없는 placeholder가 됨. 컨텍스트 부족 시 폴백 메시지 출력 후 사용자에게 직접 정보 요청 (Step A1 참고).
- **topic을 한국어/snake_case로 생성** → kebab-case 영문 명사구 강제. `테이블헤더` ❌ → `table-header-layout` ✅.
- **포인터에 본문을 다 욱여넣음** → 토큰 부채. 포인터는 5~10줄, 자세한 건 `references/{topic}/`. 본문은 lazy load 되도록.
- **mockup.html을 코드 타입 룰에도 생성** → 불필요. Step A2 타입 판정 결과를 따른다 — 코드 타입은 mockup 없음.
- **paths frontmatter 글로브 인용 부호 누락** → `paths:` 의 글로브는 따옴표 필수 (`"src/components/**"`). 따옴표 빼면 YAML 파서 에러. 단일 따옴표/이중 따옴표 모두 가능하나 일관되게.
- **promote 시 원본 그대로 두고 격상 마커도 안 박음** → 다음 호출 시 "이미 격상됐는지" 판단 불가 (Step P4). Step P8 필수.
- **edit/remove 가 references 폴더 빠뜨림** → edit는 references 까지 모두 표시·수정 대상, remove는 폴더 전체 `rm -rf`.
- **list 가 references/*.md 도 룰로 표시** → `.claude/rules/*.md` 셸 글로브는 직속만 매칭함을 확인. 재귀하려면 `**` 필요. references/ 하위는 자동 제외됨.
- **mockup.html 의 `{{custom_css}}` 에 사용자 입력 그대로 주입** → `</style>` 시퀀스가 있으면 style 블록을 깨뜨리고 그 뒤가 raw HTML로 렌더됨. Step A7 #4 의 안전성 주의 참고.
