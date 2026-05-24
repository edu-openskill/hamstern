# 햄스턴 플러그인 (hamstern-plugin)

Claude Code 세션의 결정사항을 자동 추적하고, 웹 대시보드로 시각화하며, 로컬 마크다운을 GitHub Pages 블로그로 발행하는 플러그인.

## 명령 한눈에

| 명령 | 동작 |
|---|---|
| `/hams:dashboard` | 로컬 dashboard serve (모든 프로젝트 동작). `--publish` 시 gh-pages |
| `/hams:record` | 단일 capture 진입점 — 세션을 sessions/{id}.md 저장 + 결정사항 decisions.md 누적 |
| `/hams:remind` | 결정사항(`decisions.md`) 을 현재 세션에 환기 — 자동 주입 없음, 필요할 때만 |
| `/hams:diary` | 로컬 `.md` / `.html` → GitHub Pages 블로그 게시 (멀티-프로파일, 검색 기본 ON, 댓글은 `/hams:diary giscus` 셋업 후) |
| `/hams:diary option` | 한 화면 사용법·플래그·현재 설정 표시 (read-only) |
| `/hams:audit-decisions` | 과거 결정사항의 타당성 재검토 |
| `/hams:why` | 현상의 근본 원인 추론 — 재발 시 영구 룰로 격상 제안 |
| `/hams:rule` | 프로젝트 영구 룰 관리 (add/list/edit/remove/promote) — `.claude/rules/` |

> 슬래시 명령어는 모두 콜론(`/hams:<name>`) 표기 — Claude Code 공식 plugin skill invocation 표준.

---

# `/hams:remind` — 결정사항 환기 (자동 주입 안 함)

`/clear` 후 결정사항이 필요해지는 시점에 **명시적으로** `/hams:remind` 를 친다. 그러면 `.hamstern/decisions.md` 본문이 그 세션에 출력되고, Claude 가 이후 응답에서 이를 따른다.

## 왜 자동 주입을 안 하는가

- `/clear` = 진짜 컨텍스트 비우기. 거기에 자동으로 뭔가 채워넣으면 GC 효과가 반감된다.
- 모든 작업이 결정사항을 필요로 하지는 않음 — 가벼운 질문엔 빈 컨텍스트가 더 빠르고 정확하다.
- 사용자가 출력을 눈으로 보면서 "지금 이 결정들이 적용 중" 인지 의식적으로 인지하는 게 통제력에 더 낫다.

따라서 `SessionStart` 훅으로의 자동 주입은 더 이상 동작하지 않는다. CLAUDE.md 도 건드리지 않는다 — 결정사항은 호출한 그 세션에만 들어간다 (다른 터미널 영향 없음).

## 운영 패턴

```
[/clear]            ← 진짜 컨텍스트 비우기. 깨끗.
[/hams:remind]      ← 필요해지면 결정사항 환기. 호출한 세션에만 영향.
```

## 어텐션의 본질에 대한 짧은 메모

Claude 의 어텐션은 어떤 토큰만 골라 비우는 식의 GC 가 안 된다. 진짜 GC 는 호스트 측 `/clear` 또는 `/compact`. `/hams:remind` 는 그 위에 "필요할 때만 결정사항을 다시 보여주기" 라는 보조 도구.

---

# Rules System (`/hams:why` + `/hams:rule`)

프로젝트의 반복되는 실수를 영구 원칙으로 전환하는 2단계 시스템.

## 메모리 위치 (Claude Code 기본 동작)

| 경로 | 자동 로드 | 용도 |
|------|----------|------|
| `.claude/rules/{topic}.md` | ✅ session_start (eager) | 포인터 (5~7줄, 항상 컨텍스트 보유) |
| `.claude/rules/references/{topic}/*.md,html` | ❌ lazy | 본문 (트리거 매칭 시 Claude가 능동적으로 Read) |
| `.hamstern/why/rules/{topic}.md` | ❌ | 잠정 보관소 (격상 전 단계) |

## 두 가지 등록 경로

### 경로 1 — 진단형 `/hams:why`

1회차: 문제 진단 → 근본 원인 도출 → `.hamstern/why/rules/` 잠정 저장.
2회차(같은 원칙 재발): 자동 격상 제안 → 승인 시 `.claude/rules/` 로 영구 이전.

```bash
/hams:why "테이블 헤더에서 검색·정렬 위치가 매번 다른 문제"
# → 근본 원인 분석 → 잠정 저장
# (나중에)
/hams:why "또 테이블 헤더 정렬이 좌측에 있어서 사용자 헤맴"
# → 매칭 → "격상하시겠습니까?" → 승인 → 영구 룰
```

### 경로 2 — 직접 등록 `/hams:rule add`

사용자가 대화 중 도출한 패턴을 즉시 영구화. 진단 불확실성 우회.

```bash
# 패턴이 뚜렷한 작업을 끝낸 직후
/hams:rule add
# → 컨텍스트에서 자동 추출 → 1차 초안 → 검수 → .claude/rules/ 직행
```

## 룰 관리 명령

| 명령 | 동작 |
|------|------|
| `/hams:rule add` | 대화 컨텍스트에서 신규 룰 등록 |
| `/hams:rule list` | 현재 등록된 룰 목록 출력 |
| `/hams:rule edit {topic}` | 포인터 + references 표시 후 사용자 지시대로 수정 |
| `/hams:rule remove {topic}` | 룰 + references 폴더 전체 삭제 |
| `/hams:rule promote {topic}` | `.hamstern/why/rules/` 의 잠정 룰을 수동 격상 |

## 타입 분기 (코드 vs 디자인)

`/hams:rule add` 가 컨텍스트 키워드 휴리스틱으로 자동 판정:

- **코드 타입** → `examples.md` 만 생성 (코드 + 텍스트 다이어그램)
- **디자인 타입** → `examples.md` (JSX) + `mockup.html` (브라우저로 시각 확인)
- **둘 다** → 위 모두 생성

판정 결과는 1차 초안에 표시되며 사용자가 거부/변경 가능.

## 적용 범위 (paths)

격상·등록 시 두 가지 옵션:

- **전역** — 모든 작업에서 항상 컨텍스트에 로드
- **특정 경로** — `paths:` frontmatter 글로브 (예: `src/components/**`)로 매칭되는 경로 작업 시에만 lazy 로드

특정 경로 한정은 룰이 많아질 때 토큰 비용 관리에 유용.

## 파일 구조 예시

```
.claude/rules/
├── table-header-layout.md            # 포인터 (디자인 룰)
├── api-cache-first.md                # 포인터 (코드 룰)
└── references/
    ├── table-header-layout/
    │   ├── rule.md                   # 표면/근본 원인
    │   ├── examples.md               # JSX 코드
    │   ├── mockup.html               # 시각 확인용
    │   └── history.md                # 발견·재발 이력
    └── api-cache-first/
        ├── rule.md
        ├── examples.md
        └── history.md
```

## 설계 원칙

- **CLAUDE.md 절대 안 건드림** — `.claude/rules/*.md` 자동 로드 활용
- **포인터 작게, 본문은 lazy** — 토큰 부채 방지
- **사용자 확신 → 직접 등록, 진단 결과 → 격상 사다리** — 불확실성에 따른 분기

자세한 설계 배경: [`docs/discussions/2026-04-26-why-rule-promotion-design.md`](docs/discussions/2026-04-26-why-rule-promotion-design.md)

---

# /hams:diary — 로컬 마크다운으로 운영하는 개인 블로그

`로컬에서 마크다운으로 글을 쓰고`, 명령 하나로 **GitHub Pages 개인 블로그**에 정리·게시하는 도구. 강사·연구자·개발자가 자기 글을 한 곳에 모아 운영하기 좋다.

> 핵심 가치: **글은 로컬 `.md` 파일에 살아있고, 블로그는 그 출력물**. 자기 글을 자기 컴퓨터에서 통제하면서 GitHub Pages 의 무료 호스팅·CDN·이력 관리만 빌려 쓴다.

## Quick start (3 step)

```bash
# 1. 타겟 레포 한 번만 설정
/hams:diary config repo https://github.com/myuser/my-blog.git

# 2. 첫 글 게시 — 디자인 템플릿 + 블로그 제목을 묻고 빌드
/hams:diary publish ./hello-world.md 일상

# 3. 브라우저가 자동으로 http://localhost:8765 를 열어준다
#    → ✅ 게시 / ✏️ 수정 / ❌ 취소
```

## 3가지 명령

명령은 단순하다 — `publish`(게시) · `edit`(편집) · `config`(설정).

### `publish` — 글 올리기

```bash
/hams:diary publish {input} [category] [flags]
```

| input 형태 | 동작 |
|-----------|------|
| `./post.md` | 마크다운 1개 |
| `./simulator.html` | HTML 1개 (라이트/다크 어댑터 자동 주입) |
| `./drafts/` | 폴더 안 모든 `.md`+`.html` 일괄 (중복 자동 skip) |
| `"*.md"` | 글롭 일괄 |
| `--rebuild all` | 로컬 원본 없이 사이트의 기존 글 재테마 |

**플래그**: `--no-theme` · `--overwrite` · `--draft` · `--preview-port N` · `--rebuild [slug\|all\|--category name]`

### `edit` — 글 고치기

```bash
/hams:diary edit {slug}
#  → 에디터로 _src/{slug}.{ext} 자동 오픈
#  → 미리보기 + 자동 재빌드 watcher
#  → 만족하면 ✅ 게시 / ❌ 취소
```

오타 1개 고치고 게시까지 30초.

### `config` — 설정 한 곳

```bash
/hams:diary config show                       # 현재 설정 보기
/hams:diary config repo {github-url}          # 타겟 레포 (1회 필수)
/hams:diary config template {1-5|name}        # 사이트 디자인 변경
/hams:diary config search {on|off}            # Pagefind 풀텍스트 검색
/hams:diary config comments {on|off}          # giscus 댓글 (on=대화형)
/hams:diary config blog-title "{제목}"        # 블로그 제목 변경
```

## 5가지 사이트 디자인 템플릿

| # | name | 톤 | 적합한 콘텐츠 |
|---|------|-----|---------------|
| 1 | `minimal` | 흰 배경 · 세리프 · 단일 컬럼 | 텍스트 노트, 에세이 |
| 2 | `tech` (default) | 다크 히어로 · 그라데이션 카드 · 카테고리 필터 | 시뮬레이터 · 도식 · 도구 |
| 3 | `lecture` | 주차/회차 번호 · 사이드 목차 | 정규 강의 시리즈 |
| 4 | `notebook` | Jupyter풍 좌측 TOC · monospace 헤딩 | 튜토리얼 · 실습 |
| 5 | `magazine` | 큰 히어로 · 에디토리얼 그리드 · 세리프 | 포트폴리오 · 쇼케이스 |

## 동작 흐름

```
인자 파싱
   ↓
레포 clone/pull → 워크트리 생성
   ↓
(첫 배포면) 템플릿 복사 + {{BLOG_*}} 치환
   ↓
posts.json 갱신 (중복은 skip / --overwrite 면 교체)
   ↓
MD → HTML 변환  /  HTML → 어댑터 주입
   ↓
─────────────  여기까지 로컬, push 0회  ─────────────
   ↓
python -m http.server 8765 (백그라운드)
   ↓
기본 브라우저 자동 오픈 → http://localhost:8765
   ↓
"이 모습으로 게시할까요?"
   ✅ 게시 → commit · push · PR · squash merge → 워크트리 정리
   ✏️ 수정 → 피드백 받아 재빌드 (또는 워크트리 안내 후 종료)
   ❌ 취소 → 서버 종료 + 워크트리·브랜치 삭제 + 종료
```

## 자주 쓰이는 예시

```bash
# 일기/노트 1개 게시
/hams:diary publish ./2026-04-26-회고.md 일상

# 인터랙티브 시뮬레이터 게시 (라이트/다크 어댑터 자동 주입)
/hams:diary publish ./sse-simulator.html 기술

# 폴더 일괄 게시 — 안에 있는 모든 .md/.html
/hams:diary publish ./drafts/ 일상

# 같은 폴더 다시 실행하면 중복은 자동 skip
# 한 개만 갱신하고 싶으면:
/hams:diary publish ./sse-simulator.html 기술 --overwrite

# 디자인을 노트북 스타일로 변경
/hams:diary config template notebook

# 푸시는 안 하고 워크트리만 남겨 직접 손보기
/hams:diary publish ./draft.md 일상 --draft

# ✏️ 기존 포스트 편집 — 에디터 자동 오픈 + 저장하면 즉시 재빌드
/hams:diary edit hello-world

# 검색은 기본 ON — 별도 설정 불필요. 끄려면:
/hams:diary config search off

# 댓글은 enabled-기본 ON 이지만 giscus.app 의 4개 값 등록해야 실제 노출:
/hams:diary config comments on   # 대화형 — giscus.app 의 4개 값 입력
```

> **편집 모드 전제**: 배포 시점에 원본을 `_src/{slug}.{ext}` 로 백업해 두는 포맷으로 게시된 포스트만 편집 가능. 옛 포맷 포스트는 `publish ... --overwrite` 로 한 번 재배포 후부터.

## 🔍 검색 · 💬 댓글 (둘 다 기본 ON)

DB·서버 추가 없이 두 가지가 기본 ON 으로 동작한다. 검색은 즉시 노출, 댓글은 giscus 4개 값 등록 시 노출.

### 검색 (Pagefind, 기본 ON)

빌드 시점에 모든 포스트의 풀텍스트 인덱스를 정적 파일(`pagefind/`)로 출력. 브라우저가 필요한 인덱스 조각만 fetch 해서 검색. **Algolia·Elasticsearch 같은 외부 서비스 불필요**.

```bash
# 별도 설정 없이 publish 하면 자동으로 검색이 뜬다 — Node.js 18+ 만 필요
/hams:diary publish ./new.md 일상

# 끄려면:
/hams:diary config search off
```

홈 화면에 검색창이 자동으로 생기고, 본문 안 단어로 즉시 결과 매칭.

### 댓글 (giscus, 기본 OFF — `/hams:diary giscus` 한 번 실행으로 셋업)

각 포스트가 GitHub Discussion 1개에 매핑. 학생이 GitHub 계정으로 댓글 달면 곧바로 Discussion 에 글이 쌓임. **Disqus 광고·자체 DB 불필요**.

**왜 디폴트 OFF 인가** — 댓글을 켜려면 GitHub 레포의 Discussions 활성화 + giscus GitHub App 설치 + 4 개 data-* 값 추출이 필요한데, publish 첫 호출에서 이걸 묻고 시작하면 사용자가 중간에 막혀 포기하기 쉽다. 그래서 디폴트는 OFF, 댓글이 필요해진 사용자만 별도 진입점 `/hams:diary giscus` 를 한 번 실행해서 마법사로 끝낸다.

```bash
/hams:diary giscus                 # 댓글 셋업 마법사 — 약 1분
# 흐름:
# ① Discussions 활성화 — PAT 있으면 자동, 없으면 1 클릭
# ② giscus GitHub App 설치 — 1 클릭 (GitHub 정책상 항상 필수)
# ③ 4 값 추출 — repo·repoId·category=Announcements 자동 / categoryId 는 PAT 있으면 자동, 없으면 1 값 복사
# ④ ~/.claude/hams-diary.json 에 저장
# ⑤ 기존 글 즉시 적용? → publish --rebuild all 위임

/hams:diary config comments off    # 끄기 (이미 단 댓글은 GitHub 에 그대로 보존)
```

설정 끝나면 publish/edit/--rebuild 모두 자동으로 댓글 블록 포함 — **OS prefers-color-scheme 무시, 블로그 테마 토글과 동기**. iframe 첫 페인트부터 정확 (script 동적 생성 + iframe ready hook + toggle 콜백).

### 의존성 한눈에

| 기능 | 추가 필요 |
|------|-----------|
| 검색 | Node.js 18+ (브라우저 측은 0 dep) |
| 댓글 | GitHub Discussions 활성화 + giscus 앱 설치 |

## HTML 시뮬레이터에 주입되는 것

다크 전용으로 작성된 HTML 시뮬레이터도 그대로 던져넣으면 다음이 자동 처리된다.

- **시뮬레이터 자체 폭 보존 (디폴트)** — 어댑터가 시뮬레이터 스타일을 손대지 않음. 자체 `.container { max-width: ...; margin: 0 auto }` 가 있으면 가운데 정렬, 없으면 풀너비 (작성자 의도 그대로)
- **`--fit-viewport`** (반응형 시뮬레이터용) — 시뮬레이터의 자체 max-width 를 풀어 viewport 너비를 채움. 자식 요소들도 함께 늘어나는 반응형 레이아웃에 적합
- **`--scale-up`** (고정폭 시뮬레이터용) — CSS transform: scale 로 시뮬레이터 전체를 viewport 에 맞게 확대. 고정 픽셀 레이아웃이라 max-width 만 풀면 빈 공간만 늘어나는 경우에 사용. 폰트·여백 모두 비례 확대
- **라이트/다크 토글** — `localStorage('blog-theme')` 으로 블로그 테마와 동기화
- **원본 톤 자동 감지** — 빌드 시점에 원본 HTML 의 dominant background 를 보고 `light` / `dark` 로 분류 (`data-osd-source-theme`). 라이트 톤 원본(예: 베이지)도 자동 인식
- **양방향 변환** — 원본 톤과 사용자 선택 테마가 다를 때만 `filter: invert + hue-rotate` 적용. 다크 원본 ↔ 라이트 모드, 라이트 원본 ↔ 다크 모드 모두 자동 변환되고, 톤이 같으면 원본 색상 그대로 유지 (이미지/SVG/캔버스는 역-필터로 원색 유지)
- **상단 플로팅 바** — `← 목록`, `테마` 토글 버튼 (`z-index: 2147483647`)

원본 그대로 배포하고 싶다면 `--no-theme` 사용.

## 설정 파일

`~/.claude/hams-diary.json` 한 곳에 모든 설정이 저장된다 — 여러 블로그(레포)를 named profile로 운영.

```json
{
  "active": "default",
  "profiles": {
    "default": {
      "repo": "https://github.com/myuser/tech-blog.git",
      "template": "tech",
      "blogTitle": "기술 노트",
      "pagesUrl": "https://mycustom.domain/"
    },
    "diary": {
      "repo": "https://github.com/myuser/diary.git",
      "template": "minimal",
      "blogTitle": "일상"
    }
  }
}
```

- `active` — 현재 활성 프로파일 이름. publish/edit는 이걸 사용
- `pagesUrl` 은 선택 — 비워두면 `https://{owner}.github.io/{repo}/` 로 자동 추론
- 옛 flat 형태(`{repo, template, ...}`)는 첫 호출 시 자동으로 `default` 프로파일로 변환됨 (`.bak` 백업 후)
- 프로파일 전환은 `/hams:diary config profile use {name}`. 한 번만 임시 override는 publish/edit 시 `--profile {name}` 플래그

## 더 자세한 동작·확장 백로그

전체 내부 체크리스트, 에러 처리, 강의자료 향후 확장 항목(시리즈 그룹핑·공개 토글·선수 학습 링크·slide 모드·자동 ToC·댓글) 은 [`skills/diary/SKILL.md`](skills/diary/SKILL.md) 참조.

---

## 📝 변경 내역 (Changelog)

> 버전 관리는 git commit SHA 로 한다 (`/plugin update hams` 가 매 커밋마다 새 버전으로 인식). 아래는 사용자 관점의 굵직한 변화만 정리.
>
> ⚠️ 옛 항목의 명령어 예시(`--enable-search`, `--rebuild-remote`, `--edit` 등 단독 플래그 형태)는 **폐기된 표기**입니다. 현재 사용법은 위 본문 또는 `/hams:diary option` 참조.

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

### Sub-project D — Dashboard static gh-pages + browser edit UI (2026-05-23)

- 로컬 Python HTTP 서버 (`skills/dashboard/server.py`) 와 `static/` 디렉터리 제거.
- `/hams:dashboard` 가 `skills/dashboard/build.py` 로 `.hamstern/*.md` → `docs/data/` 번들 + commit·push + `https://edu-openskill.github.io/hamstern/` 오픈.
- 정적 viewer: `docs/{index.html, app.js, style.css}`. CDN 의존성 = marked.js + DOMPurify 2개.
- 편집 흐름: 브라우저 read-only → `[×]` 클릭 → 클립보드 `/hams:audit-decisions remove "<text>"` → 사용자 세션 → 다음 dashboard 호출 시 publish.
- `skills/audit-decisions` 에 `remove "<text>"` 직접 args 형식 추가 (`remove.py` + 5 pytest 케이스).
- repo 이전: `getinthere-private-job/hamstern-plugin` → `edu-openskill/hamstern`.
- GitHub Pages 활성화는 1회성 manual step (Settings → Pages → Source: main /docs).

### Sub-project E — Dashboard per-project local serve (2026-05-23)

- `/hams:dashboard` 기본 동작을 **로컬 serve** 로 전환 — 모든 프로젝트에서 외부 의존 0 으로 즉시 동작.
- `skills/dashboard/serve.py` 신규 (≤ 80 줄 stdlib) — plugin 정적 자산 (`$PLUGIN/docs/`) + project 데이터 (`{project}/.hamstern/dashboard-data/`) 를 path 분기로 동시 serve.
- 동적 포트 (OS 할당) + background server + PID 추적 → 멀티-프로젝트 dashboard 동시 동작, 포트 충돌 0.
- Path traversal 차단 (`_safe_join` + sentinel path → 404).
- `/hams:dashboard --publish` = Sub-D 의 gh-pages 흐름 보존.
- SKILL.md 의 plugin 경로 탐지: `~/.claude/plugins/cache/hamstern/hams/*/` glob 으로 가장 최근 mtime 선택 (env var `$CLAUDE_PLUGIN_ROOT` 미신뢰).
- 9 pytest 케이스 (translate_path 5 + traversal 2 + pick_port 1 + e2e HTTPServer 1).

### 2026-05-23 — 멀티 플랫폼 핸드오프 (`/hams:record` 신설)

- **`/hams:record` 신규 스킬** — 지금 세션의 결정·실패·열린질문을 distill 해 `decisions.md` 에 idempotent 병합. **Claude Code CLI + Claude Desktop App 양쪽에서 동작** (Desktop sandbox 처럼 FS 쓰기 실패 시 동일 마크다운을 채팅 출력해 사용자가 CLI 에서 복붙).
- **공통 규약 문서 `docs/conventions.md`** — 표준 저장소 레이아웃 + 경로 해석 의사코드 (`git rev-parse → pwd` 폴백) + 능력 프로브 패턴 + decisions.md / decisions-log.md 포맷 스펙. 향후 신규 스킬도 이 규약을 따른다.
- **진입점 분리 명문화** — hook(자동/raw turn) ≠ record(수동/distilled) ≠ dashboard(Opus 정리). 셋 모두 같은 `decisions.md` 에 쓰되 서로 호출하지 않음.
- **포맷 호환성 회귀 테스트** — `skills/record/test_record_format.py` 가 dashboard 의 pin 흐름과 record 가 같은 포맷에 수렴함을 6개 케이스로 검증.
- **마켓플레이스 등록** — `.claude-plugin/marketplace.json` 의 skills 배열에 `./skills/record` 추가.
- 출처 설계: `docs/plans/2026-05-22-record-handoff-redesign.md` 의 Phase 0 + Phase 1 만 채택. Phase 2-5 (라우팅 가드 / 계층 메모리 / 3 청중 분리 / 자동화) 는 추후 별도 sub-project.

### 2026-05-23 — cmux 잔재 제거 + hooks 중복 정리 + 대시보드 검증

- **cmux 양보 메커니즘 (`.app-running` 마커) 완전 제거** — cmux 가 macOS 전용 동반 앱이고 사용자 환경에서 사용 안 함. `hooks/user_prompt.py` / `hooks/stop.py` 양쪽의 `is_app_running()` 함수 + 분기 삭제. `skills/dashboard/dashboard.sh` (cmux 바이너리 호출용 죽은 스크립트) 삭제.
- **`is_deeptalk_running()` 을 `hooks/_gate.py` 로 단일화** — 양쪽 hook 에 복붙되어 있던 함수를 게이트 모듈로 추출. 두 곳에서 동작이 미묘하게 달랐던 stale-marker auto-cleanup 차이도 자연 해소.
- **orphan `migrate_claude_md.py` + 테스트 삭제** — 1개월간 어디서도 호출 안 됨. 옛 CLAUDE.md 의 `<!-- hamstern:decisions:start --> ... <!-- hamstern:decisions:end -->` 잔존 마커는 수동 삭제 필요 (대다수 사용자는 이미 정리됨). `skills/remind/SKILL.md` 의 호출 단계도 함께 제거.
- **대시보드 작동 검증** — `python3 skills/dashboard/server.py --port 7777 --project {cwd}` 흐름 + `baby → mom → boss → /hams:remind` 핸드오프 무결성 6단계 manual 검증 완료. 결과: `docs/plans/2026-05-23-cleanup-verification.md`.
- **SKILL.md 정합성 정정** — `skills/dashboard/SKILL.md` 의 cmux 언급 제거, `skills/audit-decisions/SKILL.md` 의 cmux example 을 일반 시나리오로 교체.

### 2026-04-27 — `strip_giscus.py` 일회용 유틸 (이미 발행된 포스트에서 댓글 블록 제거)

- `skills/diary/strip_giscus.py` 신규 — 이미 배포된 `posts/*.html` 에서 `<!-- hamstern:comments:start --> ... :end -->` 마커 구간을 일괄 삭제하는 일회용 스크립트
- 사용법: `python skills/diary/strip_giscus.py <BLOG_REPO>/posts [--dry-run]`
- 배경: `config comments off` 는 **앞으로의** publish/rebuild 에서만 giscus 미주입. 이미 배포된 정적 HTML 에 박힌 giscus 블록은 그대로 남음. 그 갭을 이 유틸이 메움
- 어댑터의 idempotent 마커 설계(`inject_html_adapter.py:280-281`) 에 의존 — 마커 사이만 정확히 잘라내고 본문/시뮬레이터/themed 스타일은 그대로
- 댓글 OFF 통합 흐름: ① `config comments off` (또는 `.diary-meta.json` 의 `features.comments.enabled: false`) → ② `strip_giscus.py` 실행 → ③ commit · push

### 2026-04-27 — diary 어댑터: 시뮬레이터 세로 스크롤 + giscus 테마/디자인 정정

- **세로 스크롤 회복** — 어댑터가 시뮬레이터의 `html, body { height: 100%; overflow: hidden }` viewport 잠금을 override 로 풀어줌 (`overflow-y: auto !important; height: auto !important`). floating bar / 댓글이 viewport 밖으로 밀려나지 않고 페이지가 자연스럽게 스크롤됨. 향후 자체 스크롤 위젯이 깨지는 케이스 대비 `--lock-viewport` 옵션은 백로그
- **giscus 테마: OS 무시, 블로그 토글 따라감** — `data-theme` 을 빌드 시점에 고정하지 않고 페이지 로드 시 `localStorage('blog-theme')` 기반으로 결정. script 를 동적 생성 → iframe 첫 페인트부터 블로그 테마와 일치. iframe ready 메시지 hook + 블로그 토글 콜백 둘 다 유지 (3 단계 보호)
- **댓글 섹션 디자인 정정 (옵션 C)** — "💬 댓글" 큰 헤더 → 작은 uppercase "토론" 헤더, 폭 900px → 800px, border-top 1px + 다크/라이트 톤 살짝 패널 (rgba 기반). 블로그 톤과 자연스럽게 어울림

### 2026-04-27 — diary 어댑터에 `--fit-viewport` / `--scale-up` 폭 모드 추가

- 시뮬레이터 폭 정책을 사용자 선택으로 — 기본은 native (자체 폭 보존), 옵션 두 가지 추가:
  - `--fit-viewport`: max-width 풀기 → viewport 채움 (반응형 시뮬레이터)
  - `--scale-up`: CSS transform: scale → 비율대로 확대 (고정폭 시뮬레이터)
- 두 옵션은 상호 배타. 한 번 publish 시 선택한 모드는 `posts.json[].fit` 에 저장돼 `--rebuild` 시 그대로 재현
- `inject_html_adapter.py` 에 `--fit-viewport` · `--scale-up` 인자 + `inject(fit_mode=...)` 추가
- `--map` JSON 의 각 job 에도 `"fit": "viewport|scale|native"` 키로 per-job override 가능

### 2026-04-26 — diary 어댑터: 강제 풀너비 → 시뮬레이터 자체 폭 보존

- `inject_html_adapter.py` 의 `max-width: 100% !important` 강제 override 제거 (full / no-theme 두 모드 모두)
- 시뮬레이터에 자체 `.container { max-width: ...; margin: 0 auto }` 가 있으면 자동 가운데 정렬, 없으면 풀너비 — 작성자 의도 보존
- 처음 풀너비를 강제했던 이유 (외부 wrapper 좁은 박스에 갇혀 깨짐) 는 사실상 발생 안 함 — HTML 시뮬레이터는 `_post-frame.html` 셸을 안 쓰고 어댑터만 주입되는 구조라 외부 wrapper 자체가 없음
- floating bar 를 위한 `body { padding-top: 56px }` 와 라이트/다크 invert filter 는 그대로 유지
- 기존 사이트 적용은 `/hams:diary publish --rebuild all` 한 번

### 2026-04-26 — `/hams:diary giscus` 별도 진입점 + 댓글 디폴트 OFF 환원

- 댓글 셋업이 publish 첫 호출에 묻혔을 때 사용자가 중간에 막혀 포기하는 문제 → **댓글 디폴트를 다시 OFF**
- 새 서브명령 **`/hams:diary giscus`** — 댓글이 필요한 사용자만 한 번 실행하는 셋업 마법사
  - PAT (GH_TOKEN/GITHUB_TOKEN/`gh auth token`) 감지 → Discussions 활성화 자동, GraphQL 로 categoryId 자동
  - PAT 없으면 직접 링크 + 1 값 복사 (사용자 개입 최소화)
  - giscus GitHub App 설치는 항상 1 클릭 (GitHub 정책상 자동화 불가)
  - 셋업 후 `publish --rebuild all` 즉시 적용 옵션
- `inject_html_adapter.py` 에 `--comments-repo / --repo-id / --category / --category-id` 인자 추가 — 4 개 값 모두 있으면 `</body>` 직전에 giscus 블록 주입 (마커 기반 idempotent)
- `config comments on` 은 `giscus` 마법사로 위임 (별칭). `config comments off` 만 직접 enabled=false 처리
- `features.search` 디폴트는 그대로 ON 유지

### 2026-04-26 — diary 검색 디폴트 OFF → ON (직전 라운드)

- `features.search` 디폴트 false → **true**: 신규/기존 사용자 모두 별 설정 없이 publish 하면 Pagefind 검색이 뜨는 사이트
- (당시 댓글도 ON 으로 뒤집었으나 본 라운드에서 OFF 환원)

### 2026-04-26 — `/hams:context` → `/hams:remind` (자동 주입 제거)

- `/hams:context` 를 **`/hams:remind`** 로 완전 대체. 이름이 의도(=결정사항 환기)를 정확히 반영
- **SessionStart 훅의 결정사항 자동 주입 제거** — `/clear` 후 매번 따라붙던 노이즈가 사라짐
  - `hooks/session_start.py` · `hooks/inject_decisions.py` · 그 테스트 모두 삭제
  - `.claude/settings.json` 의 `SessionStart` 엔트리 제거 — 활성 후크는 `UserPromptSubmit` · `Stop` 만 남음
- **CLAUDE.md 비-오염 보장** — 이제 결정사항을 CLAUDE.md 에 쓰지 않음. `/hams:remind` 는 호출한 그 세션에만 본문을 출력 (다른 터미널·세션 영향 0)
- 기존 사용자 마이그레이션: `/hams:remind` 첫 호출 시 CLAUDE.md 의 `<!-- hamstern:decisions:start/end -->` 잔존 블록을 자동 정리 (`hooks/migrate_claude_md.py`, idempotent)
- 운영 패턴: **`/clear` → (필요시) `/hams:remind`** — 두 단계가 의식적으로 분리되어 사용자 통제력 최대

### 2026-04-26 — 후크 프로젝트 스코핑 + `/hams:start` · `/hams:stop`

- 후크 3종 (`SessionStart`, `UserPromptSubmit`, `Stop`) 가 `.hamstern/` 폴더 있는 프로젝트에서만 동작
- 그 외 프로젝트에선 silent exit — 의도치 않은 `.hamstern/baby-hamster/` 생성 / `CLAUDE.md` 수정 차단
- **`/hams:start`** 신규 — 현재 프로젝트에서 햄스턴 활성화 (`.hamstern/` 트리 + 메타 자동 생성)
- **`/hams:stop`** 신규 — 일시 비활성 (`.disabled` 마커. 데이터 보존)
- `SessionStart` 도 `.app-running` defer 추가 — cmux 툴과 공존 시 decisions.md 이중 주입 방지
- 19개 단위·통합 테스트 추가 (`hooks/test_gate.py`, `hooks/test_all_hooks_gated.py`)

### 2026-04-26 — 명령어 단순화 (3 서브명령 + 개인 블로그 프레이밍)

- 7~8 개 플래그 → **3개 서브명령**: `publish` · `edit` · `config`
  - `--set-repo`, `--set-template`, `--enable-search`, `--disable-search`, `--enable-comments`, `--disable-comments` → `config` 하나로 통합
  - `{file}/{dir}/{glob}` 모드 + `--rebuild-remote` → `publish` 하나로 통합
  - `--edit` → `edit`
- **옛 명령은 그대로 인식** (라우팅) — 점진적 전환 가능
- README · SKILL.md 의 프레이밍을 "강의자료 일괄 배포" → "**개인 블로그 운영**"으로 정정
  · 핵심 사용자: 강사·연구자·개발자가 자기 글을 한 곳에 모으는 것
  · 강의자료 배포는 그중 하나의 use case일 뿐
- 새 예시 블록: 일기/노트/시뮬레이터/검색·댓글 토글 — 강의 색채 줄이고 일반 블로깅 시나리오 강조

### 2026-04-26 — 검색·댓글 통합 (opt-in)

- `--enable-search` / `--disable-search` 추가 — Pagefind 풀텍스트 검색
  ```bash
  /hams:diary --enable-search
  /hams:diary ./new-post.md 강의   # 다음 배포부터 모든 포스트 자동 인덱싱
  ```
  홈에 검색창 자동 생성. Node.js 18+ 필요. DB 0개.
- `--enable-comments` / `--disable-comments` 추가 — giscus(GitHub Discussions) 댓글
  ```bash
  /hams:diary --enable-comments    # 대화형 — giscus.app 의 4개 data-* 값 입력
  ```
  포스트 하단에 자동 임베드. 라이트/다크 토글과 동기화.
- `~/.claude/hams-diary.json` 에 `features` 객체 추가 (`{search, comments}`).

### 2026-04-26 — HTML 시뮬레이터 양방향 톤 변환

- 빌드 시 원본 HTML 의 dominant background 를 자동 감지 (`data-osd-source-theme`)
- 다크 원본 → 라이트 모드, **라이트 원본 → 다크 모드** 모두 자동 변환 (이전엔 다크→라이트만)
- 톤이 같으면 필터를 적용하지 않아 원본 색상 보존

### 2026-04-26 — 편집 모드 (`--edit`)

- `/hams:diary --edit {slug}` 신설 — 기존 포스트 한 글자 고치는 데 30초
  ```bash
  /hams:diary --edit msa-k8s-websocket
  #  → 에디터로 _src/{slug}.{ext} 자동 오픈
  #  → 미리보기 서버 + 브라우저 자동 표시
  #  → 저장할 때마다 watcher 가 자동 재빌드 ([HH:MM:SS] rebuilt 출력)
  #  → 만족하면 ✅ 게시 / ❌ 취소
  ```
- 배포 시 원본을 `_src/{slug}.{ext}` 로 백업 (편집 모드의 진실의 원본)
- `posts.json` 에 `sourcePath` 필드 추가
- `watch_and_rebuild.py` helper 추가 (mtime polling)

### 2026-04-26 — 3가지 배포 모드 + 미리보기 승인 게이트 + 5템플릿 (대규모 재설계)

이전: MD 파일 1개를 즉시 push 하는 단방향 파이프라인.
이후:

- **3가지 입력 모드**: MD 1개 / HTML 시뮬레이터 1개 / 폴더·글롭 일괄
- **목업 → 승인 게이트**: 푸시 전 `python -m http.server 8765` + 브라우저 자동 오픈, ✅게시 / ✏️수정 / ❌취소 선택
- **5가지 디자인 템플릿**: `minimal`, `tech`(default), `lecture`, `notebook`, `magazine` — `--set-template {1-5|name}` 으로 변경
- **중복 자동 제외**: 배치 모드에서 같은 slug 는 skip (`--overwrite` 로 강제)
- **HTML 시뮬레이터 어댑터**: 풀-너비 + 라이트/다크 토글 + 플로팅 네비 바 자동 주입 (`--no-theme` 으로 끄기)
- **새 플래그**: `--no-theme`, `--overwrite`, `--draft`, `--preview-port`
- `inject_html_adapter.py` helper 추가 (HTML 빌드 책임 분리)
- 한글 파일명 처리: PowerShell `Get-ChildItem -LiteralPath` + ASCII slug 임시 복사 폴백

### 그 외

- `marketplace.json` 에 `./skills/diary` 등록 누락 수정
- SKILL.md 의 `name: hams-diary` → `name: diary` 정정 (플러그인 시스템이 자동으로 `hams-` prefix 추가)
- README 가 의사결정 분석 노트뿐이던 상태에서 `/hams:diary` 사용 가이드를 갖춘 본격 README 로 정리

---

## 향후 후보 (백로그)

- **시리즈 그룹핑** — `series` 필드로 강의 주차 묶음 자동 인덱스
- **공개 토글** — `published: false` 로 게시 후 미공개 (선공개 가능)
- **선수 학습 링크** — `prereq: ["slug"]` 로 다른 포스트 참조
- **slide 모드** — `?mode=slide` 발표용 풀스크린 변환
- **자동 ToC** — H2/H3 구조에서 우측 sticky 목차 (notebook 템플릿)
- **진도 추적·퀴즈** — 이 단계가 되면 비로소 Supabase 같은 DB 도입 정당화

자세한 향후 확장 백로그는 [`skills/diary/SKILL.md`](skills/diary/SKILL.md) 의 "강의자료 특화 향후 확장" 섹션 참조.
