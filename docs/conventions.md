# Hamstern Plugin Conventions

> 모든 hamstern 스킬·hook 이 따르는 공통 규약. 신규 스킬 추가 시 이 문서를 먼저 읽고 따른다.

## 1. 표준 저장소 레이아웃 (Sub-F 이후 — git-as-DB)

```
{HAMSTERN_DATA}/                          # 사용자의 personal hamstern-data repo
├── projects/
│   ├── {uuid}/
│   │   ├── meta.json                     # {uuid, name, repos, created_at, last_active}
│   │   ├── decisions.md                  # 현재 결정사항 (Sub-C 포맷 유지)
│   │   ├── decisions-log.md              # append-only 이력
│   │   ├── sessions/{session_id}.md      # 세션별 distill
│   │   └── mockups/
│   │       ├── _index.json               # {filename: {title, description, ...}}
│   │       └── *.html|*.png|...
│   └── _index.json                       # {uuid: {name, last_active, counts}}
└── docs/                                  # gh-pages source
    ├── index.html                        # 프로젝트 목록 메인
    ├── p/{uuid}/                         # per-project view
    └── data/                              # build.py 산출물 (manifest + 각 프로젝트 데이터)

# 디바이스별 캐시 (모든 hamstern 사용 디바이스)
~/.config/hamstern/
└── active-project.json                   # {uuid, name, hamstern_data_path, linked_at}

# 프로젝트 자체 repo (변경 없음 — 영구 룰만 보유)
{project_root}/.claude/rules/{topic}.md (+references/)   # 영구 룰 (자동 로드)
```

핵심 원칙:

- **모든 결정·세션·mockup 은 사용자의 personal `hamstern-data` repo 한 곳에 누적**. 프로젝트 자체 repo 는 건드리지 않음 (`.claude/rules/` 제외).
- **UUID 디렉터리 격리** — 프로젝트 이름이 바뀌어도, 같은 이름 프로젝트가 여럿 있어도 `{uuid}` 가 영구 식별자.
- **디바이스별 active 캐시** — `~/.config/hamstern/active-project.json` 이 현 세션이 어느 프로젝트인지 결정. 디바이스마다 다를 수 있음 (자연 multi-device).
- **gh-pages 빌트인** — `hamstern-data/docs/` 가 정적 viewer 의 source. `/hams:dashboard --publish` 가 `docs/data/` 를 채우고 push.

옛 단일 `.hamstern/` 인접 모델 (Sub-A~E) 은 수동으로 hamstern-data 모델로 이전 (`/hams:init` 으로 새 UUID 발급 후 옛 `.hamstern/` 내용을 `hamstern-data/projects/{uuid}/` 로 복사).

> 옛 3-tier 구조 (`baby-hamster/`, `mom-hamster/`, `boss-hamster/`) 는 Sub-C 에서 제거됨. record 첫 호출 시 자동 마이그레이션 (`.hamstern.bak.{ts}/` 백업 후 새 구조로 mv). 이 자동 마이그레이션은 *프로젝트 repo 내 옛 .hamstern/* 한정 — Sub-F 의 hamstern-data 모델로 옮긴 후에는 트리거 안 됨.

## 2. 경로 해석 의사코드

### Sub-F 이후 (active-project.json 기반)

모든 capture/read 스킬은 다음 함수를 본문 첫 단계에 호출한다:

```
resolve_active_project():
  cfg = read_json("$HOME/.config/hamstern/active-project.json")
  if cfg is missing:
    error("no active project. /hams:link \"name\" or /hams:init \"name\" first.")
  return {
    uuid:           cfg.uuid,
    name:           cfg.name,
    hamstern_data:  cfg.hamstern_data_path,
    proj_dir:       f"{cfg.hamstern_data_path}/projects/{cfg.uuid}"
  }

store_paths(active):
  return {
    sessions:  {active.proj_dir}/sessions/,
    decisions: {active.proj_dir}/decisions.md,
    log:       {active.proj_dir}/decisions-log.md,
    mockups:   {active.proj_dir}/mockups/,
    meta:      {active.proj_dir}/meta.json
  }
```

쓰기 후엔 `{hamstern_data}` 안에서 `git add ... && git commit && git push` (네트워크 실패 시 local commit 만 + 경고).

### Sub-D/E 호환용 (옛 흐름)

옛 단일 `.hamstern/` 모델에서 아직 hamstern-data 로 옮기지 않은 프로젝트나, 옛 SKILL.md 잔재에서 다음을 볼 수 있음:

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
```

신규 스킬은 이 흐름을 새로 채용하지 말 것. 기존 사용자는 수동으로 Sub-F 모델로 이전.

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

### 핀 추가·제거 블럭 (dashboard/audit-decisions)

`/hams:audit-decisions remove "<text>"` 와 dashboard 의 핀 추가 흐름은 별도 블럭 포맷을 사용한다:

```
## YYYY-MM-DDTHH:MM:SSZ | 핀 추가
- **결정:** <text>
- **카테고리:** <category>
- **배경:** <...>
- **출처:** ...
```

```
## YYYY-MM-DDTHH:MM:SSZ | 핀 제거
- **결정:** <text>
- **제거 이유:** ...
```

`/hams:context-save` 가 쓰는 세션 블럭 (`## YYYY-MM-DD HH:MM · session <id>`) 과는 다른 prefix (`|` separator + 한국어 이벤트명) 로 구분된다. dashboard 의 log timeline viewer (`docs/app.js`) 는 이 두 종류만 인식한다.

## 7. 진입점 단일화 (Sub-F 이후)

| 진입점 | 역할 |
|--------|------|
| `/hams:init` | 새 프로젝트 생성. UUID 부여 + `projects/{uuid}/` scaffolding + active 바인딩 + hamstern-data commit·push. |
| `/hams:link` | 기존 프로젝트로 active 바인딩 (부분 이름 검색). `~/.config/hamstern/active-project.json` 갱신. |
| `/hams:context-save` | **유일한 capture 진입점**. active 프로젝트의 `projects/{uuid}/{sessions/{id}.md, decisions.md, decisions-log.md}` 에 atomic dual-write + hamstern-data commit·push. |
| `/hams:context-resume` | 읽기 전용. active 프로젝트의 `decisions.md` + 최근 세션 환기. `--last N` 으로 N개 세션, `--full` 로 상세까지. |
| `/hams:save-mockup` | active 프로젝트의 `mockups/` 에 HTML/이미지 보존 + `mockups/_index.json` 갱신 + hamstern-data commit·push. |
| `/hams:audit-decisions` | 읽기 + 갱신. `decisions.md` 와 `sessions/*.md` 를 재검토하고 사용자 승인 시 `decisions.md` 갱신. `remove "<text>" --data-root <...>` 으로 dashboard 핀 제거 흐름. |
| `/hams:dashboard` (local 기본) | hamstern-data 전체 → 임시 dir 로 multi-project 번들 + background 서버 + http://localhost:<dynamic_port>/. |
| `/hams:dashboard --publish` | hamstern-data 의 `docs/data/` 로 multi-project 번들 + commit·push → `https://<owner>.github.io/hamstern-data/`. |

write 는 context-save/save-mockup/init 만, 다른 스킬은 reader 또는 reader+editor. hook 은 Sub-C 에서 제거됨 — 자동 캡쳐 없음. 모든 write 후엔 hamstern-data 안에서 git commit + push (네트워크 실패 시 local 만).

## 8. `mockups/_index.json` 포맷 + GitHub Pages URL 유도

`/hams:save-mockup` 이 쓰고, `/hams:dashboard` 가 읽는다.

```json
{
  "{filename}": {
    "title": "{제목}",
    "description": "{설명, 선택}",
    "source_session": "{세션 파일명, 예: sess1.md}",
    "mime_type": "{예: text/html, image/png}",
    "size_bytes": {정수},
    "created_at": "{ISO timestamp}"
  }
}
```

per-project Pages URL 은 hamstern-data 의 git origin 에서 유도한다 (owner/repo 추출 — alternation 에 `|` 가 있어 sed delimiter 는 `#` 사용):

```bash
ORIGIN_URL=$(cd "$HAMSTERN_DATA" && git remote get-url origin)
OWNER=$(echo "$ORIGIN_URL" | sed -E 's#^(https?://[^/]+/|git@[^:]+:)([^/]+)/.*#\2#')
REPO=$(echo "$ORIGIN_URL" | sed -E -e 's#/$##' -e 's#\.git$##' -e 's#.*/##')
URL="https://$OWNER.github.io/$REPO/p/$ACTIVE_UUID/mockups/$FNAME"
```

결과 예: `https://{owner}.github.io/hamstern-data/p/{uuid}/mockups/{filename}`

## 9. 룰 2-경로: 영구(`.claude/rules/`) vs 잠정(`.hamstern/why/rules/`)

룰은 **프로젝트 자체 repo** 에 저장된다 (hamstern-data 아님). 두 경로가 있다:

| 경로 | 생성 | 자동 로드 | 용도 |
|------|------|----------|------|
| `{project_root}/.claude/rules/{topic}.md` (+ `references/{topic}/`) | `/hams:rule add`, `/hams:rule promote` | ✅ 매 세션 (paths frontmatter 매칭 시) | 확정된 영구 룰 |
| `{project_root}/.hamstern/why/rules/{topic}.md` | `/hams:why` | ❌ 수동 호출만 | 잠정 룰 (재발 시 격상 후보) |

**영구 룰 포인터** (`{topic}.md`) 는 5~10줄: 선택적 `paths:` frontmatter (없으면 전역, 있으면 글로브 한정) + `**원칙:**` 한 줄 + `references/{topic}/` 본문 포인터. 본문(`rule.md`, `examples.md`, `mockup.html`(디자인 타입만), `history.md`)은 lazy-load.

**격상** (`/hams:rule promote {topic}`, 또는 `/hams:why` 가 재발을 감지했을 때): 잠정 룰 → 영구 룰 파일 생성 + 원본 잠정 파일 상단에 마커 삽입:

```
> 격상됨 → .claude/rules/{topic}.md ({YYYY-MM-DD})
```
