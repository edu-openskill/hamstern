# hamstern-data Repo — UUID per Project (Sub-project F)

**Date:** 2026-05-24
**Status:** Approved design, ready for plan
**Sub-project:** F (of A+B+C+D+E+F+...). A·B·C·D·E 완료. Sub-F 는 hamstern 의 cross-device·cross-platform 운영 모델을 git-as-DB 패턴으로 확립한다.
**Repo:** `edu-openskill/hamstern` (plugin) — 단 본 sub-project 는 사용자의 personal `hamstern-data` repo (별도) 를 도입한다.

## 배경

Sub-A → Sub-E 까지 hamstern 은 **프로젝트 repo 내부의 `.hamstern/` 디렉터리** 에 결정사항을 누적했다. 이 모델의 한계가 사용자 운영에서 드러남:

- 매 프로젝트마다 `.hamstern/` 가 코드 repo 에 끼어듦 (CI 노이즈, code review 산만)
- Cloud Claude 세션·Desktop App 등 multi-device 에서 결정사항 동기화 마찰
- HTML mockup, 이미지 등 binary 산출물 cross-session 보존 메커니즘 없음
- 프로젝트 동일성이 디렉터리 경로에 묶여있어 cloud stateless 컨테이너에서 깨짐

해결 모델 두 가지 검토:
1. **Supabase cloud DB** — Postgres + Storage + REST API
2. **Personal `hamstern-data` git repo** — 단일 git repo 를 cloud DB 처럼 운영, projects/{uuid}/ 디렉터리 격리

세 병렬 research 결과 ([AI memory 도구], [ADR 생태계], [객관 점수 비교]) **만장일치로 git 추천**. 산업 컨센서스 (Cline Memory Bank, Aider, Claude Code claude-memsync, Windsurf Rules, Log4brains, adr-tools, MADR, Backstage ADR, Obsidian-with-git 전부 git 선택), 이미 ship 된 Sub-D/E 자산 재사용, lock-in·offline·portability 우위.

## 목표

`hamstern-data` 라는 사용자의 personal GitHub repo 단 1개를 만들어, 그 안에 모든 프로젝트의 결정사항·세션 distill·HTML mockup 을 UUID 별 디렉터리로 격리·누적한다. 모든 디바이스 (PC, Desktop App, cloud Claude, 휴대폰 브라우저) 가 이 한 repo 만 sync 하면 cross-device·cross-session 연속성 달성. Sub-D/E 의 정적 dashboard 자산을 재사용해 `https://<owner>.github.io/hamstern-data/` 단일 URL 에서 모든 프로젝트 viewer 접근.

## 원칙

- **단일 hamstern-data repo, UUID 디렉터리 격리** — Cloud DB 의 project_id FK 패턴을 git 디렉터리로 변환
- **프로젝트 동일성은 UUID + 이름** — git remote 나 파일시스템 경로에 의존 안 함, cloud 컨테이너에서도 식별 가능
- **명시적 link 패턴** — 새 환경에서 `/hams:link "name"` 으로 active 프로젝트 바인딩, ~/.config/hamstern/active-project.json 에 캐시
- **read/write 분리 유지** — Sub-C 의 single-writer 원칙 보존 (record / save-mockup / audit-decisions remove 만 write, 나머지 read-only)
- **Markdown 포맷 보존** — 결정사항 / 세션 포맷은 Sub-C 그대로 (research 검증), Postgres row 스키마는 도입 안 함
- **gh-pages dashboard 재사용** — Sub-D/E 의 `docs/` 자산 (index.html, app.js, style.css, build.py, serve.py) 100% 재사용
- **HTML mockup 도 첫 클래스 아티팩트** — `projects/{uuid}/mockups/` 디렉터리에 누적, gh-pages 가 native serving

## 비범위 (Out of scope)

- **Supabase / Postgres / 모든 cloud DB** — research 만장일치 결정, Sub-F 에서 도입 안 함
- **diary 변경** — Sub-D 의 verification.md 에 명시된 대로 diary 는 그대로 git+Pages 유지
- **다중 사용자 sharing / ACL** — Sub-F 는 단일 사용자, multi-device. 다른 사람 공유는 repo 권한 부여 (별도)
- **모바일 *쓰기*** — 모바일 브라우저는 read-only dashboard. 쓰기는 PC/Desktop/cloud Claude 만
- **Realtime push** — gh-pages 의 ~1분 빌드 지연 수용
- **edu-openskill/hamstern (plugin repo) 의 demo 흐름** — 그대로 보존 (Sub-D dogfood)
- **자동 mockup 압축 / git LFS** — 10MB+ mockup 빈도 high 시 future trigger

## 아키텍처

### Repo 구조

```
edu-openskill/hamstern-data           ← 사용자의 personal repo (사용자당 1개)
├── projects/
│   ├── {uuid-1}/                      ← 프로젝트별 격리 디렉터리
│   │   ├── meta.json                  ← {uuid, name, repos[], created_at, last_active, description}
│   │   ├── decisions.md               ← Sub-C 포맷 (- body (이유: reason) <!-- session: id -->)
│   │   ├── decisions-log.md           ← append-only 이력 (Sub-C 포맷)
│   │   ├── sessions/
│   │   │   └── session_YYYY-MM-DDTHH-MM-SS.md
│   │   └── mockups/
│   │       ├── _index.json            ← {filename: {title, description, source_session, created_at}}
│   │       ├── payment-sim.html
│   │       └── architecture.png
│   ├── {uuid-2}/
│   │   └── ...
│   └── _index.json                    ← {uuid: {name, last_active, decision_count}}
└── docs/                              ← gh-pages source (Pages: main /docs)
    ├── index.html                     ← 프로젝트 목록 + 검색 (신규)
    ├── p/
    │   └── {uuid}/
    │       ├── index.html             ← 프로젝트별 4-column dashboard
    │       └── data/                  ← build.py 가 생성 (Sub-D 의 manifest.json 구조 확장)
    ├── app.js                         ← Sub-D 자산 (multi-project routing 추가)
    └── style.css                      ← Sub-D 자산
```

### 데이터 파일 포맷

**`projects/{uuid}/meta.json`**:
```json
{
  "uuid": "01HXY4P8Z6QK4R5T8V9W0X1Y2Z",
  "name": "포트폴리오 V2",
  "description": "선택적 한 줄 설명",
  "repos": [
    { "url": "https://github.com/me/portfolio-v2", "provider": "github", "role": "main" }
  ],
  "created_at": "2026-05-24T10:30:00Z",
  "last_active": "2026-05-24T14:22:00Z"
}
```

**`projects/_index.json`** (전체 인덱스, 매 record/init 시 갱신):
```json
{
  "01HXY4P8Z6QK4R5T8V9W0X1Y2Z": {
    "name": "포트폴리오 V2",
    "last_active": "2026-05-24T14:22:00Z",
    "decision_count": 12,
    "session_count": 5,
    "mockup_count": 2
  },
  "01HXZ5Q9A7BLR6S7U9W0X1Y2Z3": {
    "name": "강의 사이트",
    "last_active": "2026-05-20T09:11:00Z",
    "decision_count": 8,
    "session_count": 3,
    "mockup_count": 0
  }
}
```

**`projects/{uuid}/mockups/_index.json`**:
```json
{
  "payment-sim.html": {
    "title": "결제 시뮬레이터",
    "description": "Stripe 통합 흐름 mockup",
    "source_session": "session_2026-05-24T14-22-00Z.md",
    "mime_type": "text/html",
    "size_bytes": 87432,
    "created_at": "2026-05-24T14:22:00Z"
  }
}
```

**`decisions.md`, `decisions-log.md`, `sessions/*.md`** — Sub-C 의 conventions.md §4-6 포맷 그대로 (변경 없음).

### Active project 바인딩

각 디바이스의 `~/.config/hamstern/active-project.json`:
```json
{
  "uuid": "01HXY4P8Z6QK4R5T8V9W0X1Y2Z",
  "name": "포트폴리오 V2",
  "linked_at": "2026-05-24T10:30:00Z",
  "hamstern_data_path": "/c/Users/me/.claude/hamstern-data"
}
```

`hamstern_data_path` 는 사용자 머신의 hamstern-data clone 위치. 첫 셋업 시 결정.

## 스킬 변경

### 신규 (3개)

#### `/hams:init "이름" [--repo URL] [--description "..."]`

1. UUID 생성 (uuidv7 — time-ordered)
2. hamstern-data clone 위치 확인 (`~/.config/hamstern/active-project.json` 의 `hamstern_data_path`, 없으면 첫 셋업 진입)
3. `projects/{uuid}/` 디렉터리 + `meta.json` + 빈 `decisions.md` (헤더만) + `sessions/` 빈 디렉터리 + `mockups/_index.json: {}` 생성
4. `projects/_index.json` 에 새 엔트리 추가
5. `~/.config/hamstern/active-project.json` 갱신 (이 프로젝트로 바인딩)
6. hamstern-data repo 에서 `git add projects/{uuid}/ projects/_index.json && git commit -m "init: {name}" && git push`

#### `/hams:link "이름"` (또는 부분 일치)

1. hamstern-data 의 `projects/_index.json` 로드
2. name 부분 일치 검색
3. 1건 → 즉시 active 바인딩
4. 여러 건 → AskUserQuestion 으로 선택
5. 0건 → "그런 프로젝트 없음, `/hams:init` 으로 생성하시겠어요?" 안내 후 종료
6. 매칭된 UUID 를 `~/.config/hamstern/active-project.json` 에 저장

#### `/hams:save-mockup "제목" [파일]`

1. active project UUID 확인 (없으면 `/hams:link` 안내 + 중단)
2. 파일 인자 없으면: 현 세션의 최근 HTML/이미지 후보 자동 탐지 (확장자 + 최근 mtime), 또는 AskUserQuestion
3. 파일 크기 확인 — 10MB 초과 시 경고 + AskUserQuestion
4. slug 생성 (제목 → kebab-case)
5. `hamstern-data/projects/{uuid}/mockups/{slug}.{ext}` 로 복사
6. `mockups/_index.json` 갱신 (title, description, source_session, mime_type, size_bytes, created_at)
7. git add + commit + push
8. 출력: 접근 URL `https://<owner>.github.io/hamstern-data/p/{uuid}/mockups/{slug}.html`

### 변경 (4개)

#### `/hams:record`

- **Step 1 (신규)**: `~/.config/hamstern/active-project.json` 의 UUID 확인. 없으면 `/hams:link` 또는 `/hams:init` 안내 후 중단
- **Step 2-4 (기존)**: distill 로직 그대로, 단 출력 경로가 `hamstern-data/projects/{uuid}/` 로 변경
- **Step 5 (신규)**: hamstern-data repo 에서 git commit + push (현 프로젝트 repo 가 *아닌*)
- **Step 6**: `projects/_index.json` 의 해당 UUID 의 `last_active`, `decision_count`, `session_count` 갱신 후 같은 commit 에 포함

#### `/hams:remind`

- 기본: 모든 active decisions (모든 카테고리) + 최근 N=2 sessions (8KB 토큰 cap)
- `--deep` 플래그: sessions N=5
- `--mockups` 플래그: 최근 mockup 메타 5개도 환기 (`_index.json` 에서)
- 읽기 소스: hamstern-data 의 마지막 pull 상태. 첫 호출 시 자동 `git pull` (사용자 옵션 `--no-pull` 가능)

#### `/hams:dashboard`

- **local 모드 (기본)**: `python3 serve.py --plugin-dir=$CLAUDE_PLUGIN_ROOT/docs --data-dir=$HAMSTERN_DATA_PATH/projects` — Sub-E 의 serve.py 재사용. URL 의 `/data/...` 경로가 multi-project 라우팅으로 확장됨 (`/data/p/{uuid}/...` → `projects/{uuid}/...`)
- **`--publish` 모드**: build.py (확장된 버전) 가 모든 projects 의 데이터를 `hamstern-data/docs/p/{uuid}/data/` 로 번들 + commit + push to hamstern-data 의 main → gh-pages 자동 빌드
- **메인 페이지** (`/`): 프로젝트 목록 + 검색 (signal-light HTML, `_index.json` 클라이언트 fetch)
- **프로젝트별** (`/p/{uuid}/`): Sub-D 의 4-column (sessions / decisions / mockups / log)

#### `/hams:audit-decisions remove "<text>"`

- 동작 동일, 단 대상 파일이 `hamstern-data/projects/{uuid}/decisions.md`
- remove.py 의 `--project` 인자에 hamstern-data path 전달

## 마이그레이션 (`/hams:migrate-project` 신규, 1회성)

```
사용자가 기존 .hamstern/ 가 있는 프로젝트에서 호출:

1. 현 프로젝트 디렉터리의 `.hamstern/` 존재 확인 (없으면 종료)
2. 프로젝트 이름 추정:
   - git remote 의 repo 이름 fallback
   - AskUserQuestion 으로 사용자 확정
3. `/hams:init "이름"` 자동 호출 → 새 UUID + meta.json (`repos` 에 현 git remote 자동 채움)
4. 파일 복사:
   - `.hamstern/decisions.md` → `hamstern-data/projects/{uuid}/decisions.md`
   - `.hamstern/decisions-log.md` → 같은 위치
   - `.hamstern/sessions/*.md` → `hamstern-data/projects/{uuid}/sessions/`
5. 원본 보존 (기본):
   - `.hamstern/` 그대로 유지
   - `.hamstern/MIGRATED.md` 생성: 한 줄 메모 "이 데이터는 hamstern-data/projects/{uuid}/ 로 이전됨. UUID: {uuid}. {ISO date}"
6. `--delete-original` 옵션 시: `.hamstern/` 통째 삭제 (사용자 확신할 때만)
7. 옛 dashboard (현 프로젝트 repo 의 `docs/`) 가 있으면 그대로 둠 — 더 이상 갱신 안 될 뿐 정상 동작
8. hamstern-data 에 commit + push
```

### `edu-openskill/hamstern` (plugin repo) 처리

Sub-D 가 demo 로 publish 한 dashboard 사이트는 그대로 유지. 그건 *plugin 의 자기 자신을 dogfood* 한 demo (Sub-D scope 의 본질).

신규 사용자 흐름은 별도 personal hamstern-data repo. 두 repo 공존 — demo vs 실사용 분리.

## 에러 처리

| 시나리오 | 동작 |
|---|---|
| hamstern-data repo 가 로컬에 없음 (첫 셋업) | `/hams:init` 첫 호출 시 자동 clone (또는 안내) — 새 사용자는 GitHub 에서 repo 먼저 생성 |
| `active-project.json` 의 UUID 가 `_index.json` 에 없음 | record/remind 가 중단, "해당 UUID 없음. `/hams:link` 로 재바인딩" 안내 |
| git push 실패 (네트워크·인증) | 로컬 commit 은 성공. 다음 호출 시 자동 retry. 사용자에게 경고 출력 |
| 두 디바이스 동시 record (merge conflict) | git pull --rebase 자동 시도 → 충돌 시 사용자에게 conflict 파일 안내 + 수동 해결 가이드 |
| Mockup 파일 너무 큼 (>10MB) | 경고 + AskUserQuestion 확인 ("이 mockup 은 큽니다. git LFS 도입 시점인지 검토 권장") |
| `_index.json` 이 디렉터리와 desync (수동 편집 등) | `/hams:rebuild-index` 수동 명령 — projects/ 디렉터리 스캔해서 재생성 |
| 사용자가 hamstern-data 를 private repo 로 했지만 GitHub Pages 미가용 (free plan) | 안내 후 두 옵션: (a) public 으로 전환 (b) local 모드만 사용 |
| `~/.config/hamstern/` 미존재 | 첫 호출 시 디렉터리 자동 생성 |

## 테스트

### 단위 (pytest)

- `skills/dashboard/build.py` 변경 — multi-project 번들 로직 (projects/* 순회)
- `skills/dashboard/serve.py` 변경 — `/data/p/{uuid}/...` path 분기
- `_index.json` 갱신 로직 (record 시 인크리먼트)
- `/hams:init` 의 UUID 생성·디렉터리 scaffolding
- `/hams:link` 의 부분 일치 검색
- `/hams:save-mockup` 의 slug 생성 + size validation

### 통합

- 임시 git repo (`hamstern-data` 흉내) 만들어서:
  - init → record → remind → dashboard 전체 흐름
  - 2개 프로젝트 init + link 전환
  - mockup save + dashboard 에서 확인

### 매뉴얼 UAT (verification.md)

1. **첫 셋업** — hamstern-data repo 없는 상태에서 `/hams:init` 호출 → repo 생성 안내 + 셋업 완료
2. **첫 프로젝트** — `/hams:init "테스트 프로젝트"` → 디렉터리 생성 + active 바인딩
3. **record 사이클** — `/hams:record` 한두 번 → decisions.md + sessions/ 갱신 + push
4. **remind 환기** — `/hams:remind` → decisions + 최근 2 sessions 출력
5. **두 번째 프로젝트** — `/hams:init "테스트 2"` → 새 UUID, active 자동 전환
6. **프로젝트 전환** — `/hams:link "테스트 프로젝트"` → 첫 프로젝트로 active 복귀
7. **mockup save** — `/hams:save-mockup "결제 mockup" payment.html` → mockups/ 에 복사 + push
8. **dashboard** — `/hams:dashboard` → 로컬 서버 + 브라우저 오픈 → 메인 페이지에서 두 프로젝트 보임 + 각 프로젝트 클릭 시 4-column dashboard
9. **`--publish`** — `/hams:dashboard --publish` → gh-pages 빌드 + `https://<owner>.github.io/hamstern-data/` 접근
10. **두 디바이스 시뮬레이션** — 같은 hamstern-data 를 다른 디렉터리에 clone, 양쪽에서 record, 양쪽 push, merge conflict 해결 흐름
11. **마이그레이션** — 기존 .hamstern/ 가 있는 프로젝트에서 `/hams:migrate-project` → hamstern-data 로 이전

## 변경 영향 매트릭스

| 항목 | 변경 |
|---|---|
| `skills/init/SKILL.md` | **신규** |
| `skills/link/SKILL.md` | **신규** |
| `skills/save-mockup/SKILL.md` | **신규** |
| `skills/migrate-project/SKILL.md` | **신규** (1회성 마이그레이션) |
| `skills/rebuild-index/SKILL.md` | **신규** (복구용 수동 도구) |
| `skills/record/SKILL.md` | active-project 확인 + hamstern-data 경로로 출력 변경 |
| `skills/remind/SKILL.md` | hamstern-data 의 active project 디렉터리 읽기, N=2 sessions 추가 |
| `skills/dashboard/SKILL.md` | multi-project 메인 페이지 + per-project 라우팅 |
| `skills/dashboard/build.py` | multi-project 번들 (projects/* 순회), mockup 메타 포함 |
| `skills/dashboard/serve.py` | `/data/p/{uuid}/` path 분기 |
| `docs/index.html` | 메인 페이지 (프로젝트 목록 + 검색) 신규 |
| `docs/app.js` | mockups column 추가, project 라우팅 (`/p/{uuid}/`) |
| `docs/style.css` | mockups column 스타일 |
| `skills/audit-decisions/remove.py` | `--data-root` 옵션 추가, project_uuid 인자 |
| `~/.config/hamstern/active-project.json` | 신규 (디바이스별 상태) |
| `README.md` | hamstern-data 셋업 가이드 + Sub-F changelog |
| `docs/conventions.md` | git-as-DB 모델 명시, projects/{uuid}/ 디렉터리 규약 |
| `.claude-plugin/marketplace.json` | 신규 skill 5개 등록 (init, link, save-mockup, migrate-project, rebuild-index) |

## 1회성 운영 작업

- 사용자가 GitHub 에서 `hamstern-data` repo 생성 (private 권장, 단 GitHub Pages 사용 시 plan 확인)
- 사용자의 머신에 hamstern-data clone
- 첫 디바이스에서 `/hams:init` 첫 호출 시 자동 셋업
- 추가 디바이스 매번: hamstern-data clone + `~/.config/hamstern/active-project.json` 위치만 안내
- GitHub Pages 활성화 (`/hams:dashboard --publish` 첫 호출 시 안내)

## 검증 체크리스트 (Definition of Done)

- [ ] 5개 신규 SKILL.md 작성 (`init`, `link`, `save-mockup`, `migrate-project`, `rebuild-index`)
- [ ] 4개 기존 SKILL.md 수정 (`record`, `remind`, `dashboard`, `audit-decisions`)
- [ ] `build.py` multi-project 확장 + pytest
- [ ] `serve.py` path 분기 확장 + pytest
- [ ] `docs/index.html` 메인 페이지 (프로젝트 목록)
- [ ] `docs/app.js` mockups + project 라우팅
- [ ] `~/.config/hamstern/active-project.json` 스키마 + 로딩 로직
- [ ] `marketplace.json` 신규 스킬 등록
- [ ] README hamstern-data 셋업 가이드 + Sub-F changelog
- [ ] `docs/conventions.md` git-as-DB 규약 추가
- [ ] 매뉴얼 UAT 11 시나리오 verification.md 작성

## 다음 단계

Sub-G+ 후보 (verification.md 의 발견 사항에 따라):

- **Hybrid Supabase index** — 결정사항 200+ 누적 시 SQL 검색 layer 추가 (git source-of-truth 유지)
- **mockup 자동 thumbnail** — HTML → 첫 viewport 캡처 (이미지 PNG) → dashboard 미리보기
- **모바일 PWA + write** — GitHub API direct write 로 모바일에서도 record 가능
- **다중 사용자 sharing** — 특정 프로젝트만 다른 사용자에게 공유 (sub-repo split 또는 권한)
- **diary 메타 미러링** — diary 글 메타가 hamstern-data 의 통합 dashboard 에 노출 (Sub-D verification.md 의 발견 사항 반영)

Sub-F 의 plan 은 본 spec 을 입력으로 `writing-plans` skill 이 작성.
