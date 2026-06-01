## 플러그인 설치 / 재설치 / 삭제

```bash
/plugin uninstall hams@hamstern
/plugin marketplace remove hamstern
/plugin marketplace add edu-openskill/hamstern
/plugin install hams@hamstern
```

---

# hamstern — Claude Code 용 personal AI memory system

Claude Code 의 모든 세션에서 나온 결정사항·세션 distill·HTML mockup 을 사용자 개인의 GitHub repo 하나(`hamstern-data`)에 UUID 격리로 누적 저장하고, 어느 디바이스에서든 dashboard 로 조회하고 필요할 때 환기하는 시스템.

## 한 줄 정리

> AI 와 대화한 내용·결정사항·HTML 목업을 휴대폰·데스크탑앱·다중 컴퓨터 CLI 에서 한 곳(`hamstern-data` private repo)에 모으고, 필요할 때 명시적으로 가져온다. git-as-DB 패턴, 외부 SaaS 의존 0, CLAUDE.md 비-오염.

## 핵심 비전

Claude 와 한 대화의 결과물은 휘발성이다. `/clear` 한 번이면 사라지고, 디바이스를 바꾸면 다시 시작. hamstern 은 그 결과물 중 **결정사항·세션 요약·HTML 목업** 만 골라 사용자 personal repo 에 누적해 둔다. 어떤 클라우드 SaaS 도 거치지 않고, 모든 게 git history 로 남는다.

- **Multi-device** — 휴대폰 브라우저로 dashboard 열어 결정사항 조회. 다른 컴퓨터에서 clone 만 하면 동기화.
- **Multi-project** — 한 hamstern-data 에 여러 프로젝트가 UUID 격리. dashboard 가 프로젝트 선택 UI.
- **Plain Markdown** — 모든 데이터가 사람이 읽을 수 있는 `.md`. lock-in 0.

---

## 셋업 (3 step)

```bash
# 1. GitHub 에서 private repo `hamstern-data` 생성 (이름은 자유, 권장: 본인 이름 또는 hamstern-data)
#    git clone 로 사용자 머신에 (기본 위치: ~/.claude/hamstern-data)

# 2. plugin 설치 (Claude Code marketplace)
/plugin install hamstern

# 3. 첫 프로젝트 생성
/hams:init "내 첫 프로젝트"
#    → UUID 발급 + hamstern-data/projects/{uuid}/ scaffolding
#    → ~/.config/hamstern/active-project.json 에 active 바인딩
#    → commit + push
```

다른 디바이스 추가는 hamstern-data clone 후 `/hams:link "프로젝트 이름"`.

---

## 핵심 명령 (한눈에)

| 명령 | 역할 |
|---|---|
| `/hams:init` | 새 hamstern 프로젝트 생성 (UUID + scaffolding) |
| `/hams:link` | 기존 프로젝트로 active 바인딩 (부분 이름 매칭) |
| `/hams:context-save` | 세션 컨텍스트(맥락 + ADR 결정 + narrative)를 핸드오프 문서로 저장 (`--full` 시 시간순 상세까지) |
| `/hams:context-resume` | 저장된 세션 상세 환기 → 다음 작업 첫 항목까지 제안 (`--list`로 선택) |
| `/hams:context-decisions` | `decisions.md`(현 유효 결정 누적)만 빠르게 환기 |
| `/hams:save-mockup` | HTML/이미지 mockup 을 hamstern-data 에 cross-session 보존 |
| `/hams:dashboard` | local serve 기본, `--publish` 로 gh-pages multi-project dashboard |
| `/hams:audit-decisions` | 결정사항 타당성 재검토 (또는 dashboard `[×]` 의 클립보드 명령 흐름) |
| `/hams:why` | 현상의 근본 원인 추론 — 재발 시 영구 룰로 격상 |
| `/hams:rule` | 프로젝트 영구 룰 관리 (add/list/edit/remove/promote) — `.claude/rules/` |
| `/hams:deeptalk` | Socratic 토론 모드 (코드 수정 없이 트레이드오프 탐색) |
| `/hams:diary` | 로컬 마크다운 → GitHub Pages 블로그 게시 (별도 흐름) |

---

## 자세한 사용법

### 1. 첫 셋업 — `hamstern-data` repo

1. GitHub 에서 새 repo 생성: `hamstern-data` (private 권장)
2. 사용자 머신에 clone (기본 위치: `~/.claude/hamstern-data`)
3. Claude 세션에서: `/hams:init "프로젝트 이름"`
4. 자동으로 UUID 발급 → `hamstern-data/projects/{uuid}/` scaffolding → active 바인딩 → commit + push
5. (옵션) GitHub Settings → Pages → main `/docs` 활성화 → `/hams:dashboard --publish` 로 휴대폰 등에서 조회 가능

### 2. 세션 컨텍스트 저장 — `/hams:context-save`

지금 세션의 작업 컨텍스트를 다음 세션이 이어갈 수 있는 핸드오프 문서로 저장한다. 결정 한 줄만이 아니라 **맥락 요약(narrative) + ADR-style 결정 + 미정 + 다음 작업**을 함께 보존:

- `hamstern-data/projects/{uuid}/sessions/{id}.md` — 5섹션 핸드오프 문서 (`--full` 시 시간순 상세 narrative까지)
- `hamstern-data/projects/{uuid}/decisions.md` — 결정만 append (자동 dedup)

```bash
/hams:context-save                # 기본 5섹션 저장
/hams:context-save "제목"          # 제목 지정
/hams:context-save --full          # 시간순 상세 narrative까지 (deeptalk 보존용)
```

호출 시점: 굵직한 결정을 끝낸 직후, `/clear` 직전. active 프로젝트가 없으면 먼저 `/hams:init` 또는 `/hams:link` 필요.

### 3. 세션 환기 — `/hams:context-resume` · `/hams:context-decisions`

`/clear` 후 이전 맥락이 필요해지면 **명시적으로** 호출. 자동 주입 없음.

```bash
/hams:context-resume             # 가장 최근 세션 상세 환기 + 다음 작업 제안
/hams:context-resume --list      # 저장된 세션 전체 목록 → 선택
/hams:context-decisions          # decisions.md(현 유효 결정 누적)만 빠르게 환기
```

**왜 자동 주입을 안 하는가:**
- `/clear` = 진짜 컨텍스트 비우기. 자동 주입은 GC 효과를 반감시킴.
- 가벼운 질문은 빈 컨텍스트가 더 빠르고 정확.
- 사용자가 의식적으로 "지금 이 결정들이 적용 중" 임을 인지하는 게 통제력에 유리.

`SessionStart` 훅 자동 주입은 폐기. CLAUDE.md 도 건드리지 않음 — 결정사항은 호출한 그 세션에만 들어가고, 다른 터미널·디바이스에 영향 0.

### 4. HTML mockup 보존 — `/hams:save-mockup`

UI 스케치·시뮬레이터·도식 HTML 을 cross-session 보존.

```bash
/hams:save-mockup ./sketch.html "로그인 화면 v2"
#  → hamstern-data/projects/{uuid}/mockups/{slug}.html 저장
#  → mockups/_index.json 갱신
#  → (gh-pages 활성 시) 즉시 URL 발급
```

`/hams:dashboard` 로 다른 세션·디바이스에서도 mockup 메타·링크 환기.

### 5. Dashboard — `/hams:dashboard`

기본 동작은 **local serve** — 외부 의존 0 으로 즉시 동작:

```bash
/hams:dashboard          # 동적 포트 + 브라우저 자동 오픈, multi-project view
/hams:dashboard --publish  # docs/data/ 번들 + commit·push → gh-pages 게시
```

**View 구조:**
- 메인 페이지: 프로젝트 목록 (`projects/_index.json` 기반) + 검색
- per-project 4-column view: sessions / decisions / mockups / decisions-log

CDN 의존성: marked.js + DOMPurify 2개. 그 외 stdlib only.

### 6. 결정 편집 (dashboard `[×]` → audit-decisions remove)

dashboard 의 결정 옆 `[×]` 클릭 → 클립보드에 다음이 복사됨:

```bash
/hams:audit-decisions remove "<text>" --project-uuid <UUID>
```

다음 Claude 세션에 붙여넣어 실행 → `decisions.md` 에서 해당 줄 삭제 + `decisions-log.md` 에 제거 이벤트 append → 다음 dashboard publish 시 반영.

### 7. 프로젝트 전환 — `/hams:link`

```bash
/hams:link "로그인"        # 부분 이름 매칭 → 후보 1개면 즉시 바인딩
/hams:link                 # 인자 없으면 전체 목록 + 선택
```

`~/.config/hamstern/active-project.json` 갱신. 디바이스별 캐시 → multi-device 가 각자 다른 active 가능.

---

## 보조 명령

### `/hams:audit-decisions` (interactive 흐름)

```bash
/hams:audit-decisions
#  → active 프로젝트의 모든 결정사항을 Opus 분석으로 1개씩 검토
#  → [k] Keep / [m] Modify / [d] Delete / [s] Skip
```

`active-project.json` 에서 UUID + path 자동 resolve. dashboard `[×]` 의 `remove "<text>"` 형식과 별개 사용 사례.

### `/hams:why` + `/hams:rule` (영구 룰 시스템)

프로젝트의 반복되는 실수를 영구 원칙으로 전환하는 2단계 시스템.

| 경로 | 자동 로드 | 용도 |
|------|----------|------|
| `.claude/rules/{topic}.md` | session_start (eager) | 포인터 (5~7줄) |
| `.claude/rules/references/{topic}/*` | lazy | 본문 (트리거 매칭 시 Claude 가 Read) |
| `.hamstern/why/rules/{topic}.md` | — | 잠정 보관소 (격상 전) |

**경로 1 — 진단형 `/hams:why`:**
1회차 = 근본 원인 도출 + 잠정 저장. 2회차(같은 원칙 재발) = 자동 격상 제안.

**경로 2 — 직접 등록 `/hams:rule add`:**
대화 중 도출한 패턴을 즉시 영구화.

```bash
/hams:rule add              # 컨텍스트에서 자동 추출 → 1차 초안 → 검수 → 영구
/hams:rule list             # 목록
/hams:rule edit {topic}     # 수정
/hams:rule remove {topic}   # 삭제
/hams:rule promote {topic}  # 잠정 → 영구 수동 격상
```

설계 원칙: **CLAUDE.md 절대 안 건드림** · 포인터 작게·본문 lazy · 사용자 확신 → 직접 등록, 진단 결과 → 격상 사다리.

### `/hams:deeptalk` — Socratic 토론

사용자가 결론·구현을 강요하지 않고 의견·트레이드오프를 교환하려 할 때. 코드 수정 없이 주제 탐색. 자연 트리거: "어떻게 생각해?", "니 의견은?", "같이 생각해보자".

### `/hams:diary` — 별도 라이프사이클 (블로그 게시)

hamstern-data 와 **분리된** 도구. 로컬 `.md` / `.html` 을 GitHub Pages 개인 블로그로 게시.

```bash
/hams:diary config repo https://github.com/myuser/my-blog.git
/hams:diary publish ./hello.md 일상
/hams:diary edit hello-world
/hams:diary option   # 한 화면 사용법
```

3 서브명령 (`publish` · `edit` · `config`) + 5 디자인 템플릿 (`minimal` · `tech` · `lecture` · `notebook` · `magazine`). 검색 (Pagefind) · 댓글 (giscus) 통합. 자세한 사용법은 [`skills/diary/SKILL.md`](skills/diary/SKILL.md).

---

## 아키텍처 — git-as-DB

```
사용자 디바이스 (CLI / Desktop / 모바일 브라우저)
        ↓ /hams:context-save · /hams:save-mockup
hamstern-data/  (사용자 personal GitHub repo, private)
├── meta.json                         # schema_version, created_at
├── projects/
│   ├── _index.json                   # UUID → {name, last_active, counts}
│   └── {uuid}/
│       ├── decisions.md              # 결정만 (자동 dedup)
│       ├── decisions-log.md          # append-only 제거 이벤트
│       ├── sessions/{id}.md          # 세션별 full distill
│       └── mockups/
│           ├── _index.json
│           └── {slug}.html
└── docs/                             # gh-pages dashboard (--publish 시)
    ├── index.html · app.js · style.css
    └── data/ (build.py 산출)
```

| | Cloud DB (Supabase 등) | hamstern (git-as-DB) |
|---|---|---|
| 쓰기 | API call | git commit + push |
| 읽기 | API call | git clone / fetch |
| 검색 | SQL/full-text | dashboard 또는 ripgrep |
| 외부 의존 | SaaS account | GitHub 만 |
| 비용 | 사용량 | 0 (private repo) |
| 이력 | DB log | git history (자동) |
| Multi-device sync | server-side | git pull/push |
| Lock-in | provider 종속 | plain markdown |

---

## 환경별 사용

| 환경 | 쓰기 | 읽기 |
|---|---|---|
| Claude Code CLI | ✅ | ✅ |
| Claude Desktop App | ✅ (FS write 가능 시) | ✅ |
| Cloud Claude.ai/code | ✅ (PAT 필요) | ✅ |
| 휴대폰 브라우저 | ❌ | ✅ (dashboard `--publish` URL) |

---

## 데이터 파일 포맷

- **`meta.json`**: `{schema_version, created_at}`
- **`projects/_index.json`**: `{ {uuid}: {name, last_active, decision_count, session_count, mockup_count} }`
- **`mockups/_index.json`**: `{ {slug}: {title, created_at, source} }`
- **`decisions.md`**: `## {category}` 헤더 + `- {text} <!-- session: {id} -->` 줄
- **`decisions-log.md`**: `## removed` 헤더 + 제거 이벤트 append-only
- **`sessions/{id}.md`**: `## 결정` / `## 실패` / `## 열린 질문` 3-섹션

`~/.config/hamstern/active-project.json` (디바이스별):
```json
{ "uuid": "...", "hamstern_data_path": "/home/user/.claude/hamstern-data" }
```

---

## 알려진 제약

- bash → Python `-c` 보간 escape: single quote 안전성 약함 (실사용 위험 낮음, hardening 백로그)
- uuidv7 fallback (Python <3.13): non-strict shape
- merge conflict 자동 해결 없음 — 양 디바이스 동시 push 시 사용자 수동 해결
- gh-pages publish 활성화는 1회성 manual (Settings → Pages → main /docs)

---

## Sub-projects (변경 이력)

- **Sub-A** (2026-04-26) — Rules system (`/hams:why` + `/hams:rule`), 2-경로 등록 (진단형 / 직접)
- **Sub-B** (2026-04-26~) — diary (블로그 게시), 3 서브명령 + 5 템플릿 + 검색·댓글
- **Sub-C** (2026-05-23) — `/hams:record` 신설, hooks 전부 제거, 3-tier → 2-tier 평탄화
- **Sub-D** (2026-05-23) — Dashboard static gh-pages + 브라우저 편집 UI (`[×]` 클립보드 흐름)
- **Sub-E** (2026-05-23) — Dashboard local serve 기본, dynamic port + path traversal 차단
- **Sub-project F** (2026-05-24) — **hamstern-data repo + UUID per project (git-as-DB)** — 핵심 비전 실현. 신규 skill (`init`/`link`/`save-mockup`) + multi-project dashboard
- **Sub-G** (2026-05-30) — `record`/`remind` → `context-save`/`context-resume`/`context-decisions` 로 대체 (맥락 narrative + ADR 결정 함께 보존)
- **Sub-H** (2026-06-01) — 폐기된 `record`/`remind` 스킬 디렉터리·매니페스트 항목 완전 제거 (v1.2.1)

---

## Sub-G+ 후보

- **Hardening pass** — bash → Python 보간 escape 견고화, `uuid7` 표준 채택 (Python 3.13+)
- **Hybrid index** — Supabase 같은 가벼운 read-only index 로 휴대폰 검색 응답 가속 (선택)
- **Mobile PWA** — dashboard 의 offline-first PWA 화 (서비스 워커 + 캐시)
- **Conflict-aware sync** — 양 디바이스 동시 push 시 사용자에게 머지 후보 제시
- **Decision graph** — 결정사항 간 의존 관계 시각화 (Graphviz / mermaid)

---

## 라이선스 / Contributing

내부 도구. PR / issue 환영. `docs/conventions.md` 의 저장소 레이아웃·경로 해석 규약을 따른다.

---

> 슬래시 명령어는 모두 콜론 표기 (`/hams:<name>`) — Claude Code 공식 plugin skill invocation 표준.
