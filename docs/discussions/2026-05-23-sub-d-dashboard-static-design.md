# Dashboard — Static gh-pages + Browser-Side Edit UI (Sub-project D)

**Date:** 2026-05-23
**Status:** Approved design, ready for plan
**Sub-project:** D (of A+B+C+D+...). A·B·C 완료. D 는 Sub-C 에서 deferred 한 "Dashboard 의 github.io 정적 호스팅 + 브라우저 편집 UI" 를 완성한다.
**Repo:** `edu-openskill/hamstern` (`getinthere-private-job/hamstern-plugin` 에서 이전 완료)

## 배경

Sub-C 에서 `/hams:record` 가 단일 capture 진입점이 되고 폴더 구조가 평탄화되면서 dashboard 는 read+편집(toggle/remove) 책임만 남았다. 그러나 현재 dashboard 는:

- 로컬 Python HTTP 서버 (`skills/dashboard/server.py`) — 매 호출마다 포트 충돌 정리·서버 기동 필요
- 데스크탑/노트북 등 다중 머신 간 공유 불가 — 각 머신에서 따로 띄워야 함
- 브라우저-서버 양방향 통신이 있어 진짜 정적 단순성에 도달 못 함

해법: **`/hams:dashboard` 가 `.hamstern/*.md` 를 정적 사이트 데이터로 번들·commit·push 하고, gh-pages 가 URL 하나로 서빙한다.** 편집은 브라우저에서 클립보드에 슬래시 명령을 복사 → Claude 세션에 붙여넣어 실행 → 다음 `/hams:dashboard` 호출 시 publish.

## 목표

`/hams:dashboard` 를 호출하면 1) 최신 `.hamstern/` 스냅샷을 정적 사이트로 publish 하고 2) 브라우저에서 viewer + 편집 명령 클립보드 UI 를 띄운다. 로컬 서버 의존성 0, 다중 머신 공유 URL 1개, 외부 SaaS·인증 0.

## 원칙

- **read 와 write 분리** — gh-pages 는 read-only viewer. 모든 write 는 `.hamstern/*.md` 를 거쳐 `/hams:audit-decisions` skill 이 갱신.
- **on-demand publish** — `/hams:dashboard` 호출 시점이 publish 시점. 사이트는 "마지막 dashboard 호출의 스냅샷" 의미가 명확.
- **idempotent 빌드** — `.hamstern/` 변경 없으면 `docs/data/` 도 동일 → 빈 commit 0 (`git status --short` 으로 가드).
- **인증 없음** — 브라우저는 GitHub API write 호출 안 함. 모든 권한 부여는 사용자의 Claude 세션에서 명시적으로 일어남.
- **CDN 만, 빌드 도구 0** — node_modules 없음. `marked.js` + `DOMPurify` 핀된 버전 CDN.
- **책임 단일성** — `/hams:record` 는 source 만 쓴다. `/hams:dashboard` 만 `docs/data/` 를 쓴다. `/hams:audit-decisions` 만 `.hamstern/decisions.md` 의 편집을 수행. 세 skill 의 책임이 겹치지 않는다.

## 비범위 (Out of scope)

- **Sub-E (가칭)**: Slack/Discord broadcast (MCP). decisions 변경을 채널로 알림하는 layer 는 D 이후.
- **다중 프로젝트 aggregation**: 한 dashboard 가 여러 hamstern-using repo 를 합쳐 보여주기. v2.
- **편집 v2**: × 외에 edit/add 버튼. v1 은 remove 만 클립보드 지원.
- **인증·다중 사용자**: hamstern 은 단일 사용자 도구.
- **양방향 실시간 동기화**: 정적 사이트의 본질.
- **페이지네이션 / 검색 / 필터**: sessions > 100 시 페이지네이션. v2.
- **Dark mode**: v2.

## 아키텍처

### 두 계층 + 하나의 다리

```
┌─────────────────────────────────────────────────────────────┐
│              main 브랜치 (단일 source of truth)            │
├─────────────────────────────────────────────────────────────┤
│ .hamstern/                docs/                             │
│   decisions.md     ───┐     index.html                      │
│   decisions-log.md    │     app.js                          │
│   sessions/*.md       │     style.css                       │
│                       │     data/                           │
│                       └──→    decisions.md     (복사)       │
│                              decisions-log.md (복사)        │
│                              sessions/*.md    (복사)        │
│                              manifest.json    (생성)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ git push
              GitHub Pages serves docs/  →  https://edu-openskill.github.io/hamstern/
                              │
                              ▼ 사용자 브라우저
                       [×] 클릭 → 클립보드: /hams:audit-decisions remove "..."
                              │
                              ▼ Claude 세션에 붙여넣어 실행
                       /hams:audit-decisions 가 .hamstern/decisions.md 갱신
                              │
                              ▼ 다음 /hams:dashboard 호출
                       build.py 재실행 → docs/data/ 갱신 → commit·push
```

### 파일 레이아웃

```
hamstern-plugin/
├── .hamstern/                          # 소스 (record 가 씀)
│   ├── decisions.md
│   ├── decisions-log.md
│   └── sessions/*.md
├── docs/                                # GitHub Pages 소스 (Settings → Pages → main /docs)
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── data/                           # /hams:dashboard 가 생성
│       ├── decisions.md
│       ├── decisions-log.md
│       ├── sessions/<filename>.md
│       └── manifest.json
└── skills/dashboard/
    ├── SKILL.md
    ├── build.py                        # .hamstern → docs/data 번들러
    └── test_build.py                   # pytest
```

**삭제 대상** (Sub-C 의 로컬 서버 흔적):
- `skills/dashboard/server.py`
- `skills/dashboard/static/` (전체 디렉터리)

## `/hams:dashboard` 호출 흐름

SKILL.md 가 Claude 에게 지시:

1. **번들**: `python3 skills/dashboard/build.py --project .`
   - 입력: `--project` (기본 `.`), `--out` (기본 `docs/data`)
   - 동작:
     1. `.hamstern/decisions.md` 존재 시 → `docs/data/decisions.md`
     2. `.hamstern/decisions-log.md` 동일
     3. `.hamstern/sessions/*.md` → `docs/data/sessions/`
     4. `docs/data/manifest.json` 생성
     5. 소스에 없는 파일이 `docs/data/` 에 남아있으면 삭제 (stale 정리)
   - 실패: stderr + exit 1
2. **변경 감지**: `git status --short docs/data/`
3. **commit + push**: 변경 있을 때만
   ```
   git add docs/data/
   git commit -m "chore(dashboard): refresh data YYYY-MM-DDTHH:MM:SSZ"
   git push origin main
   ```
4. **브라우저 오픈**: 플랫폼별
   - Windows: `start https://edu-openskill.github.io/hamstern/`
   - macOS: `open ...`
   - Linux: `xdg-open ...`

### manifest.json 스키마

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-23T08:42:00Z",
  "decisions": true,
  "decisions_log": true,
  "sessions": [
    "session_2026-05-22T12-34-56Z.md",
    "session_2026-05-23T08-00-00Z.md"
  ]
}
```

- `schema_version` 1: 이후 변경 시 브라우저가 강제 reload·migration 메시지 띄울 수 있음
- `decisions`, `decisions_log`: 소스에 존재 여부 (false 면 viewer 가 빈 패널 + 안내문)
- `sessions`: 파일명 배열, mtime 내림차순

## UI 명세

### 데스크탑 레이아웃 (≥ 769px)

3-column.

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🐹 hams-dashboard            generated: 2026-05-23 08:42 UTC        │
├──────────────┬──────────────────────────────┬───────────────────────┤
│ Sessions     │ Decisions                    │ Log timeline          │
│ (200px)      │ (flex, ~480px)               │ (320px)               │
│              │                              │                       │
│ session_…    │ ## Category A                │ 2026-05-23 08:42      │
│ session_…    │ - decision text       [×]   │ + pinned "..."        │
│ ▶ click →    │ - decision text       [×]   │                       │
│  MD render   │                              │ 2026-05-22 14:01      │
│  inline      │ ## Category B                │ − unpinned "..."      │
│              │ - …                  [×]    │                       │
└──────────────┴──────────────────────────────┴───────────────────────┘
```

- **Sessions 컬럼**: 파일명 리스트 (mtime 역순). 클릭 시 컬럼 하단에 marked.js 로 MD 렌더.
- **Decisions 컬럼**: `decisions.md` 의 H2 카테고리별 그룹. 각 `- ` 항목 옆 `[×]` 버튼.
- **Log timeline 컬럼**: `decisions-log.md` 의 `## YYYY-MM-DDTHH:MM:SS | 핀 추가|제거` 블럭을 시간 역순 카드로.

### 모바일 레이아웃 (≤ 768px)

탭 전환: `[Decisions] [Sessions] [Log]`. 기본 Decisions.

### 편집 클립보드

`[×]` 클릭 → 슬래시 명령을 `navigator.clipboard.writeText()` 로 복사:

```
/hams:audit-decisions remove "<decision text without leading '- '>"
```

Toast 알림 (3초): "복사됨 — Claude 세션에 붙여넣어 실행하세요"

**의존성**: 현재 `/hams:audit-decisions` 는 args 없는 인터랙티브 흐름. Sub-D 가 이 skill 에 직접 args 형식을 추가한다:

```
/hams:audit-decisions                          # 기존 인터랙티브 audit
/hams:audit-decisions remove "<text>"          # 신규 — 직접 제거 (matching line 한 줄 삭제 + log append)
```

`<text>` 에 `"` 가 포함되면 v1 은 백슬래시 escape (`\"`). 첫 매칭 한 줄만 제거. 0건 매칭 시 에러 메시지.

이 audit-decisions 확장은 Sub-D scope 에 포함된다 (분리하면 dashboard 가 비호환 명령을 발행하게 됨).

### 의존성 (CDN 핀)

- `marked@<latest stable>` — MD → HTML
- `dompurify@<latest stable>` — XSS 방지

스크립트 태그는 `integrity` 해시 동반. plan 단계에서 정확한 버전·해시 확정.

## 에러 처리

| 시나리오 | 동작 |
|---|---|
| `build.py` 실패 (파일 권한·손상) | stderr 메시지, exit 1, commit·push 스킵 |
| Pages 미활성 | 브라우저 404. SKILL.md 에 1회성 활성화 안내 ("Settings → Pages → Source: main /docs") |
| `docs/data/manifest.json` 없음 (브라우저) | "Dashboard 데이터 미생성. `/hams:dashboard` 호출 후 재방문" 메시지 |
| MD 파싱 에러 | 해당 항목만 raw text 로 fallback, console.warn |
| `clipboard.writeText()` 실패 (구 브라우저) | hidden `<textarea>` + "Ctrl+C 로 복사" 안내 |
| sessions/ 파일 수 폭증 (>100) | v1: 그대로 표시. 페이지네이션은 future work |
| 원격 push 거부 (인증·네트워크) | 사용자에게 stderr 전달, 브라우저는 그대로 오픈하되 "데이터는 로컬 빌드 시점" 경고 |

## 테스트

### 단위 (pytest)

`skills/dashboard/test_build.py`:

1. `.hamstern/decisions.md` 만 있을 때 → docs/data/decisions.md + `manifest.sessions == []`
2. sessions 만 있을 때 → manifest 의 sessions 리스트 정확
3. 빈 `.hamstern/` → docs/data/ 비어있음, manifest 의 decisions/decisions_log 모두 false
4. **stale 정리** — 이전 빌드의 session 파일이 .hamstern 에서 삭제되면 docs/data/sessions 에서도 제거
5. `manifest.schema_version == 1` 검증
6. 두 번 연속 호출 idempotent — 동일 입력 → 동일 출력 (파일 mtime 외)

### 매뉴얼 UAT (verification.md)

- `/hams:dashboard` 첫 호출 → docs/data/ 생성, commit, push, 브라우저 오픈
- decision `[×]` 클릭 → 정확한 슬래시 명령이 클립보드에
- 모바일 폭에서 탭 전환 동작
- 빈 `.hamstern/` 으로 호출 → 빈 패널 + 안내문
- sessions 클릭 → MD 렌더링
- Pages 미활성 상태에서 호출 → 404 + 활성화 안내 따라가면 동작

## 마이그레이션

Sub-C 에서 이미 `.hamstern/` 의 새 평탄 구조 (`sessions/`, `decisions.md`, `decisions-log.md`) 로 통일됨. Sub-D 의 마이그레이션은 단순:

- `skills/dashboard/server.py` 삭제
- `skills/dashboard/static/` 삭제
- `docs/` 디렉터리 신설 (현재 hamstern-plugin 에 `docs/` 는 `discussions/`, `plans/`, `conventions.md` 만 — Pages 의 Source: `/docs` 활성 시 이들도 같이 노출됨)

**중요 결정**: 기존 `docs/discussions/`, `docs/plans/`, `docs/conventions.md` 는 Pages 활성화 시 함께 호스팅됨. 이는 hamstern 의 자기-문서화 측면에서 오히려 자연스러움. 별도 디렉터리 분리 불필요.

## 변경 영향 매트릭스

| 항목 | 변경 |
|---|---|
| `skills/dashboard/SKILL.md` | 로컬 서버 절차 → 정적 사이트 publish·오픈 절차로 전면 재작성 |
| `skills/dashboard/server.py` | **삭제** |
| `skills/dashboard/static/` | **삭제** |
| `skills/dashboard/build.py` | **신규** |
| `skills/dashboard/test_build.py` | **신규** |
| `skills/audit-decisions/SKILL.md` | `remove "<text>"` args 형식 추가 문서화 |
| `skills/audit-decisions/test_audit.py` | 신규 — args 형식 단위 테스트 |
| `docs/index.html` | **신규** |
| `docs/app.js` | **신규** |
| `docs/style.css` | **신규** |
| `docs/data/` | **신규** (build.py 가 생성, 첫 commit) |
| `.gitignore` | `docs/data/` 는 commit 됨 — gitignore 추가 없음 |
| `README.md` | dashboard 사용법 섹션 갱신 (로컬 서버 → URL) + Pages 활성화 안내 |
| `docs/conventions.md` | dashboard 항목의 "Sub-D" 미정 표기 → 확정 표기로 갱신 |
| `.claude-plugin/marketplace.json` | 변경 없음 (`./` 상대 경로 유지) |

## 1회성 운영 작업 (plan 의 manual task)

- GitHub Settings → Pages → Source: `main` branch, folder `/docs` → Save
- 첫 빌드: `/hams:dashboard` 호출 → docs/data/ 첫 commit·push → 1~2분 후 https://edu-openskill.github.io/hamstern/ 활성 확인
- `getinthere-private-job/hamstern-plugin` 원격 처리 (archive or delete) — 사용자 결정

## 검증 체크리스트 (plan 의 Definition of Done)

- [ ] `skills/dashboard/server.py` 삭제됨
- [ ] `skills/dashboard/static/` 삭제됨
- [ ] `skills/dashboard/build.py` 작성됨 + 6개 pytest 케이스 그린
- [ ] `skills/audit-decisions/SKILL.md` 에 `remove "<text>"` args 형식 추가 + 단위 테스트 그린
- [ ] `docs/index.html`, `docs/app.js`, `docs/style.css` 작성됨
- [ ] `/hams:dashboard` 호출 → 번들 + commit + push + 브라우저 오픈 흐름 동작
- [ ] GitHub Pages 활성화 + URL 응답 확인
- [ ] `[×]` 클릭 → 정확한 슬래시 명령 클립보드 복사 확인
- [ ] 빈 `.hamstern/` 케이스 fallback 메시지 확인
- [ ] 모바일 폭 탭 전환 확인
- [ ] README dashboard 섹션 갱신
- [ ] `docs/conventions.md` Sub-D 표기 확정
- [ ] verification.md 작성 (수동 시나리오 6개)

## 다음 단계

Sub-E (가칭) — Broadcast layer:
- Slack/Discord MCP 연동
- `/hams:audit-decisions` 가 결정사항 변경 시 채널로 알림 broadcast
- 저장은 여전히 git, 알림만 SaaS

Sub-D 의 plan 은 본 spec 을 입력으로 `writing-plans` skill 이 작성.
