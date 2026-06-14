---
name: diary-server
description: |
  로컬 마크다운(.md)/HTML을 GitHub Pages 개인 블로그에 발행하는 도구. 로컬 전용 열람은 /hams:diary-local 사용.
  배포 전 로컬 미리보기 서버로 검수하고 승인 후에만 푸시한다.
  강사·연구자·개발자가 자기 글을 한 곳에 모아 운영하기 좋다.
  사용법:
    /hams:diary-server publish {file|dir|glob} [category]   # 게시 (단일/일괄 자동 감지)
    /hams:diary-server edit {slug|id}                        # 편집
    /hams:diary-server delete {title|id}                     # 삭제 (제목 유사도/숫자 ID)
    /hams:diary-server config <subcommand>                   # 설정 (프로파일 포함)
    /hams:diary-server option                                # 한 화면 사용법
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
  - PowerShell
---

# /hams:diary-server

로컬에서 작성한 마크다운·HTML 파일을 **GitHub Pages 개인 블로그**에 정리·게시하는 도구. 글쓰기는 익숙한 에디터에서 하고, 정리·배포·검수만 자동화한다.

## 핵심 가치

1. **로컬 우선** — 글은 자기 컴퓨터의 `.md` 파일로 살아있고, 블로그는 그 출력물.
2. **목업 후 게시** — 로컬에서 미리보기 서버 → 브라우저 검수 → 승인 → push.
3. **5가지 디자인** — `minimal` / `tech` / `lecture` / `notebook` / `magazine` 중 한 줄 명령으로 변경.
4. **DB 없이 풍부한 기능** — 검색(Pagefind, 기본 ON) · 라이트/다크 자동 변환 · 한글 파일명 안전 처리.
5. **숫자 ID URL** — 각 글은 `/posts/{id}/{slug}.html` (자동 1, 2, 3…) 로 게시돼 짧고 안정적.

---

## 사용 방법

명령은 5개의 서브명령으로 통합되어 있다 — `publish` · `edit` · `delete` · `config` · `option`.

### `publish` — 글 올리기

```bash
/hams:diary-server publish {input} [category] [flags]

# input 자동 감지
/hams:diary-server publish ./post.md 일상           # 단일 마크다운
/hams:diary-server publish ./simulator.html 강의    # 단일 HTML
/hams:diary-server publish ./drafts/ 일상           # 폴더 일괄 (.md + .html)
/hams:diary-server publish "*.md" 일상              # 글롭 일괄
/hams:diary-server publish --rebuild all            # 로컬 원본 없이 사이트 글 재테마

# 플래그
--no-theme                              # HTML 어댑터 주입 끄기 (라이트/다크 변환 OFF, 폭은 native)
--overwrite                             # 기존 동일 글 덮어쓰기 (originalFilename → slug → 제목 매칭)
--draft                                 # 푸시 안 하고 워크트리만 남김
--preview-port N                        # 미리보기 포트 (기본 8765)
--rebuild [slug|all|--category name]    # 사이트 기존 글 재테마/재시그니처
--profile {name}                        # 1회 임시 프로파일 override (active 변경 안 함)
--fit-viewport                          # 시뮬레이터 max-width 풀어서 viewport 채움 (반응형 시뮬레이터 권장)
--scale-up                              # CSS transform: scale 로 viewport 너비에 맞게 확대 (고정폭 시뮬레이터 권장)
```

> **시뮬레이터 폭 정책 (HTML 엔진 전용)** — 디폴트는 시뮬레이터 자체 `max-width` 보존 (가운데 정렬 또는 풀너비). `--fit-viewport` / `--scale-up` 은 상호 배타. 한 번 publish 시 선택한 모드는 `posts.json[].fit` 에 저장돼 다음 `--rebuild` 때 그대로 재현된다.

두 번째 위치 인자는 카테고리 (쉼표 구분 다중 가능). 비어있으면 AskUserQuestion `multiSelect: true` 로 선택받는다.

### `edit` — 글 고치기

```bash
/hams:diary-server edit {slug|id} [--profile {name}]
# slug 또는 숫자 ID (postId) 모두 가능
# → 에디터에서 _src/{slug}.{ext} 자동 오픈
# → 미리보기 서버 + 브라우저 자동 표시
# → 저장하면 watcher 가 자동 재빌드
# → ✅ 게시 / ❌ 취소
```

### `delete` — 글 삭제

```bash
/hams:diary-server delete {title|id} [--profile {name}] [--yes]

# 숫자 ID — 정확 매칭
/hams:diary-server delete 5                    # postId=5 인 글 삭제

# 제목 — 유사도 매칭
/hams:diary-server delete "MSA Kubernetes"     # title 부분일치/유사도 ≥0.5
                                        # 1건이면 확인 후 삭제
                                        # 다건이면 AskUserQuestion 으로 선택

# 플래그
--yes      # 확인 프롬프트 생략 (스크립트용)
--profile  # 임시 프로파일 override
```

삭제 흐름은 워크트리 → posts.json 에서 entry 제거 → `posts/{id}/{slug}.html` + 디렉토리 + `_src/{slug}.{ext}` 삭제 → pagefind 재빌드 → 미리보기 확인 → 승인 → commit + push. 자세한 흐름은 [🗑 삭제 모드](#-삭제-모드-delete) 참조.

### `config` — 설정 한 곳

```bash
# 활성 프로파일 갱신
/hams:diary-server config show                       # 활성 + 모든 프로파일 표시
/hams:diary-server config repo {github-url}          # 활성 프로파일의 타겟 레포
/hams:diary-server config template {1-5|name}        # 활성 프로파일 사이트 디자인
/hams:diary-server config search {on|off}            # Pagefind 검색 (기본 on)
/hams:diary-server config blog-title "{title}"       # 활성 프로파일 블로그 제목

# 프로파일 관리 (멀티 블로그 운영용)
/hams:diary-server config profile list                       # 등록된 프로파일 목록 + 활성 표시
/hams:diary-server config profile add {name} {repo-url}      # 신규 프로파일 등록
/hams:diary-server config profile use {name}                 # 활성 프로파일 전환
/hams:diary-server config profile remove {name}              # 프로파일 삭제
```

> 다른 톤의 블로그(예: 기술 / 일상 / 강의)는 **별도 프로파일 = 별도 레포**로 운영. 한 사이트 안에 카테고리별 다른 템플릿은 비권장 (시각 일관성·SEO 이유).

### `option` — 사용법 한눈에

```bash
/hams:diary-server option   # 서브명령·플래그·템플릿·예시·현재 설정을 한 번에 표시 (read-only)
```

`option` 은 어떤 외부 동작(git/clone/server/AskUserQuestion/파일 갱신)도 발생시키지 않는다. 사용법을 빠르게 훑고 싶을 때 호출. 출력 양식은 0-4 참조.

---

## 0️⃣ 인자 해석 & 설정 확인

### 0-1. 설정 로드 (공유 모듈)

`python3`로 `${PLUGIN_ROOT}/skills/diary-core/diary_config.py`를 사용한다:
- `cfg = diary_config.load()` (없으면 None → 0-1.1로 초기화)
- `cfg, changed = diary_config.migrate(cfg)`; `changed`면 `diary_config.save(cfg, backup=True)`
- 활성 프로파일: `name, P = diary_config.resolve(cfg, "server", override=<--profile 값|None>)`
  - `ValueError`("type 'local'…")면 "이 프로파일은 로컬용입니다 — /hams:diary-local 사용" 안내 후 종료
- `config profile use {n}`은 `diary_config.set_active(cfg, n)` 사용 (타입에 맞는 activeServer/activeLocal 갱신)

스키마는 `{activeServer, activeLocal, profiles{<name>:{type, repo|dir, template, ...}}}`. server 스킬은 `type=="server"` 프로파일만 다룬다.

### 0-2. 서브명령 라우팅

인자 1번째 토큰으로 분기:

| 토큰 | 분기 |
|---|---|
| `publish` | publish 흐름 (1️⃣~🔟) |
| `edit {slug|id}` | edit 모드 |
| `delete {title|id}` | 0-3.2 — 삭제 (제목 유사도 또는 숫자 ID) |
| `config <sub>` | 0-3 |
| `option` | 0-4 (read-only) |
| 그 외 | "알 수 없는 명령. `/hams:diary-server option` 으로 사용법을 확인하세요" 안내 후 종료 |

> 옛 표기(`--set-repo`, `--set-template`, `--enable-*`, `--disable-*`, `--edit`, `--rebuild-remote`, `giscus`, `config comments`, 서브명령 없는 단독 파일 인자)는 모두 **폐기됐다**. 받으면 위 "알 수 없는 명령" 분기로 안내 후 종료.

### 0-3. `config` 서브명령 분기

마이그레이션 후 `cfg['profiles'][cfg['active']]` 를 **P** (활성 프로파일) 라고 한다.

| 명령 | 동작 |
|---|---|
| `config show` | `cfg` 전체 + 활성 프로파일 강조해서 보기 좋게 출력 |
| `config repo {url}` | `P['repo'] = url` 갱신 |
| `config template {1-5\|name}` | `TEMPLATES = ['minimal','tech','lecture','notebook','magazine']`. 숫자/이름 검증 후 `P['template']` 갱신 |
| `config search on\|off` | on이면 Node.js (`npx`) 가용성 체크 + `npx -y pagefind --version` 사전 다운로드 → `P['features']['search'] = on/off` |
| `config blog-title "{title}"` | `P['blogTitle'] = title` |
| `config profile list` | `cfg['profiles']` 키 목록 + `cfg['active']` 표시 |
| `config profile add {name} {url}` | 이름 충돌 검사 → `cfg['profiles'][name] = {'repo': url, 'template': 'tech'}` 등록 |
| `config profile use {name}` | 존재 검증 → `cfg['active'] = name` |
| `config profile remove {name}` | 활성이면 다른 프로파일로 자동 전환. 마지막 1개면 거부 |

모든 갱신은 `json.dump(cfg, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)` 로 저장 후 종료. publish/edit는 트리거되지 않는다.

### 0-3.2 `delete` 서브명령 — 글 삭제

**호출 형태**

```bash
/hams:diary-server delete {target} [--profile {name}] [--yes]
```

**target 해석**

1. `target` 이 **순수 정수** (예: `5`, `12`) → **숫자 ID 모드**
   - `posts[].postId == int(target)` 인 entry 찾기 → 정확 매칭
   - 없으면 "ID {N} 글이 없습니다" 안내 후 종료
2. 그 외 (문자열, 한글, 슬러그 패턴) → **제목 유사도 모드**
   - 후보 = `posts[]` 중 다음 중 하나를 만족하는 entry:
     - `target.lower() in entry['title'].lower()` (부분 일치)
     - `target.lower() in entry['id'].lower()` (slug 부분 일치)
     - `difflib.SequenceMatcher(None, target.lower(), entry['title'].lower()).ratio() >= 0.5`
   - 후보 0건 → "일치하는 글이 없습니다. `/hams:diary-server delete` 로 ID 입력하세요" 안내 후 종료
   - 후보 1건 → 그 entry 로 진행 (확인 단계로)
   - 후보 2건 이상 → AskUserQuestion 으로 사용자에게 선택받음 (각 옵션: `[#{postId}] {title} (slug={id}, category={cat})`)

**흐름**

1. 활성 프로파일 P 결정 (publish 와 동일 — `--profile` 추출, 0-5 로직).
2. LOCAL_DIR clone/pull → 워크트리 생성 (`BR=delete-${postId}-${TS}`).
3. posts.json 로드 → 위 매칭 로직으로 **삭제 대상 entry 선정**.
4. **삭제 미리보기 출력**:
   ```
   🗑  삭제 대상
      #ID: {postId}
      제목: {title}
      slug: {id}
      카테고리: {category}
      URL: /posts/{postId}/{id}.html
      파일: posts/{postId}/{id}.html, _src/{id}.{ext}
   ```
5. `--yes` 가 없으면 AskUserQuestion: "정말 삭제할까요?"
   - ✅ 삭제 / ❌ 취소
   - 취소 시: 워크트리·브랜치 삭제, push 0회, 종료
6. **파일·entry 삭제**:
   - `os.remove(f"posts/{postId}/{id}.html")`
   - `shutil.rmtree(f"posts/{postId}")` (디렉토리 비면 — 단일 글당 폴더 1개이므로 항상 삭제됨)
   - `os.remove(f"_src/{id}.{ext}")` (존재할 때만)
   - posts.json `posts[]` 에서 해당 entry 제거 (postId 재정렬은 하지 않음 — ID 영구 유지)
   - 글로벌 `categories[]` 재계산: 삭제 후 남은 entry 들의 `categories` 의 union 만 유지 (insertion order)
7. Pagefind 재빌드 (search 활성 시 — 인덱스에 삭제된 페이지가 남으면 안 됨).
8. 미리보기 서버 시작 + `http://localhost:$PORT/` 브라우저 오픈 → 목록에서 사라진 것 확인.
9. AskUserQuestion: "사이트에서 삭제 확인됐습니다. push 할까요?"
   - ✅ → commit (메시지: `delete: {title} (#${postId})`) → push → PR → merge → 워크트리 정리
   - ❌ → 워크트리·브랜치 삭제, push 0회
10. 결과 출력:
    ```
    ✅ 삭제 완료
       · #{postId} {title}
       🌐 {PAGES_URL} 에서 1~2 분 후 반영
    ```

**주의**
- **postId 는 재사용하지 않는다.** 5번 글을 삭제해도 다음 글은 (현재 최대값 + 1) 을 받음. URL stability + 검색엔진 캐시 보호.
- `posts/` 아래 잘못된 빈 디렉토리(예: 옛 빌드 잔재) 정리는 별도 안전장치로 처리 — 삭제 모드는 entry 가 실제로 가리키는 파일만 건드린다.
- 매칭 결과를 표시할 때 한국어 title 우선, slug 보조.

### 0-4. `option` 서브명령 (read-only)

어떤 외부 동작(git/clone/server/AskUserQuestion/파일 갱신)도 발생시키지 않고 다음을 출력하고 종료:

```
🐹 /hams:diary-server — 로컬 마크다운/HTML → GitHub Pages 개인 블로그

📌 서브명령
  publish {file|dir|glob} [category] [--플래그…]      # 게시 (단일/일괄 자동 감지)
  edit {slug|id} [--profile {name}]                    # 기존 글 편집 (라이브 미리보기)
  delete {title|id} [--yes] [--profile {name}]         # 삭제 (제목 유사도 또는 숫자 ID)
  config <sub>                                          # 설정 (아래)
  option                                                # 이 사용법 표시 (read-only)

🚩 publish 플래그
  --no-theme                           # HTML 어댑터 주입 끄기 (라이트/다크 변환 OFF, 폭은 native)
  --overwrite                          # 같은 글 발견 시 기존 slug에 덮어쓰기 (URL 보존)
  --draft                              # 푸시 안 하고 워크트리만 남김
  --preview-port N                     # 미리보기 포트 (기본 8765)
  --rebuild [slug|all|--category X]    # 사이트 기존 글 재테마
  --profile {name}                     # 1회 임시 프로파일 override (active 변경 안 함)
  --fit-viewport                       # 시뮬레이터 max-width 풀어서 viewport 채움 (반응형 시뮬레이터 권장)
  --scale-up                           # CSS transform: scale 로 viewport 너비에 맞게 확대 (고정폭 시뮬레이터 권장)

🔧 config 서브명령 (활성 프로파일 갱신)
  show                                 # 활성 + 모든 프로파일 표시
  repo {github-url}                    # 활성 프로파일의 타겟 레포
  template {1-5|minimal|tech|lecture|notebook|magazine}
  search {on|off}                      # Pagefind 풀텍스트 검색
  blog-title "{제목}"

👥 프로파일 관리 (멀티 블로그 운영용)
  config profile list                              # 전체 목록 + 활성 표시
  config profile add {name} {repo-url}             # 신규 프로파일 등록
  config profile use {name}                        # 활성 전환
  config profile remove {name}                     # 삭제 (마지막 1개는 거부)

🎨 5가지 템플릿
  minimal   — 흰 배경 · 세리프 · 단일 컬럼 (텍스트 노트, 에세이)
  tech      — 다크 히어로 · 그라데이션 카드 · 카테고리 필터 (시뮬레이터·도구)
  lecture   — 주차/회차 번호 · 사이드 목차 (강의 시리즈)
  notebook  — Jupyter풍 좌측 TOC · monospace 헤딩 (튜토리얼)
  magazine  — 큰 히어로 · 에디토리얼 그리드 · 세리프 (포트폴리오)

💡 예시
  /hams:diary-server publish ./hello.md 일상
  /hams:diary-server publish ./hello.md "msa,kafka"                # 다중 카테고리 (쉼표 구분)
  /hams:diary-server publish ./drafts/ 일상 --overwrite
  /hams:diary-server publish ./사이트.html 기술 --no-theme
  /hams:diary-server publish ./post.md 일상 --profile diary        # 1회 임시 override
  /hams:diary-server edit hello-world
  /hams:diary-server edit 5                                        # 숫자 ID 도 가능
  /hams:diary-server delete 5                                      # postId=5 삭제
  /hams:diary-server delete "MSA Kubernetes"                       # 제목 유사 매칭
  /hams:diary-server config profile add tech https://github.com/me/tech-blog.git
  /hams:diary-server config profile use tech
  /hams:diary-server config search on

📂 현재 설정 (~/.claude/hams-diary.json)
  activeServer: <cfg.activeServer>
  profiles: <N>개
  - <name>  →  <repo>  (<template>)
  - ...

  활성 프로파일 <active> 상세
    repo:        <P.repo>
    template:    <P.template>
    blogTitle:   <P.blogTitle 또는 (미설정)>
    search:      <on|off> (기본 on)

💾 옛 flat 형태({repo, template, ...})는 첫 호출 시 자동으로 default 프로파일로 변환되며 ~/.claude/hams-diary.json.bak 에 백업됩니다.

⚠️  옛 표기(--set-repo / --set-template / --enable-* / --disable-* / --edit / --rebuild-remote / giscus / config comments / 서브명령 없는 단독 파일 인자)는 모두 폐기됐습니다.

📖 더 자세한 spec: skills/diary-server/SKILL.md
```

설정 파일이 아예 없으면 "📂 현재 설정" 섹션은 "(아직 없음 — `/hams:diary-server config profile add default <url>` 로 시작)"으로 대체.

### 0-5. 일반 실행 (publish/edit) — 활성 프로파일 추출

`publish` 또는 `edit` 로 라우팅된 경우:

1. 인자에서 `--profile {name}` 추출 → 있으면 그 이름, 없으면 `cfg['active']`
2. `cfg['profiles'][name]` 존재 여부 검증 (없으면 에러 종료: "프로파일 없음. `/hams:diary-server config profile list` 로 확인")
3. 활성 프로파일 P에서 다음 변수 추출:

| 변수 | 값 |
|---|---|
| `PROFILE_NAME` | 사용 중인 프로파일 이름 |
| `REPO_URL` | `P['repo']` |
| `REPO_OWNER`, `REPO_NAME` | URL 파싱 |
| `PAGES_URL` | `P['pagesUrl']` 또는 `https://${OWNER}.github.io/${NAME}/` |
| `TEMPLATE` | `P['template']` (기본 `tech`) |
| `BLOG_TITLE` | `P['blogTitle']` (없으면 첫 배포 시 AskUserQuestion으로 받아 P에 저장) |
| `FEATURES` | `P['features']` (없으면 `{search: true}` — Pagefind 검색만 ON) |
| `LOCAL_DIR` | `/tmp/${REPO_NAME}-${PROFILE_NAME}` (프로파일별 분리) |
| `WORKTREE_DIR` | `/tmp/${REPO_NAME}-${PROFILE_NAME}-preview-${TS}` |

`P['template']` 필드 없으면 첫 배포 시 AskUserQuestion으로 5개 중 선택받고 P에 저장.

---

## 렌더링 단계 (공유)

입력 분류·메타 추출·템플릿 복사·posts.json 매칭·포스트 HTML 생성·검색·Pagefind 인덱스는
`${PLUGIN_ROOT}/skills/diary-core/RENDER.md`를 따른다. 호출 전 `$BLOG_DIR=$WORKTREE_DIR`로 세팅한다.

---

## 2️⃣ 레포 준비 + 워크트리 생성

```bash
# Clone (없으면) 또는 pull (있으면)
if [ ! -d "$LOCAL_DIR" ]; then
  git clone "$REPO_URL" "$LOCAL_DIR"
fi
cd "$LOCAL_DIR"
BASE_BRANCH=$(git remote show origin | grep 'HEAD branch' | sed 's/.*: //')
# 빈 레포면 BASE_BRANCH는 main 으로 가정
[ -z "$BASE_BRANCH" ] && BASE_BRANCH=main
git fetch origin || true
git checkout "$BASE_BRANCH" 2>/dev/null || git symbolic-ref HEAD refs/heads/$BASE_BRANCH
git pull origin "$BASE_BRANCH" 2>/dev/null || true

# 워크트리 (배포 단위)
TS=$(date +%Y%m%d-%H%M%S)
BR="post-preview-${TS}"
git worktree add -b "$BR" "$WORKTREE_DIR"
cd "$WORKTREE_DIR"
```

---

## 6️⃣ 미리보기 서버 + 브라우저 오픈

```bash
PORT=${PREVIEW_PORT:-8765}
cd "$WORKTREE_DIR"
python3 -m http.server $PORT >/tmp/diary-preview.log 2>&1 &
SERVER_PID=$!
sleep 1

# 브라우저 자동 오픈
URL="http://localhost:${PORT}/"
case "$(uname -s)" in
  MINGW*|CYGWIN*|MSYS*) start "$URL" ;;
  Darwin) open "$URL" ;;
  Linux) xdg-open "$URL" >/dev/null 2>&1 || true ;;
esac
```

> Windows Git Bash 에서 `start` 가 안 되면 `cmd //c start "" "$URL"` 또는 PowerShell `Start-Process "$URL"` 로 폴백.

미리보기에서 개별 글은 `http://localhost:${PORT}/posts/{postId}/{slug}.html` 에서 볼 수 있다. 사용자에게 안내 출력 시 첫 N개의 직접 URL 을 함께 표시하면 좋다.

---

## 7️⃣ 승인 게이트

AskUserQuestion 호출:

```
질문: "이 모습으로 게시할까요?"
   ✅ 게시 (Recommended) — push + PR + merge
   ✏️ 수정     — 사용자 피드백 받아 4~5단계 재실행 (또는 워크트리 그대로 두고 사용자가 직접 편집)
   ❌ 취소     — 워크트리 삭제, 0회 push
```

선택 후 처리:

- **✅ 게시** → 9단계로 진행
- **✏️ 수정** → 사용자에게 어떤 부분이 문제인지 묻고, 가능하면 자동으로 수정 후 4~5단계 재실행. 수정 불가능한 경우 워크트리를 그대로 두고 "워크트리 위치: ${WORKTREE_DIR}. 직접 수정 후 다시 실행해 주세요" 안내. 서버는 종료.
- **❌ 취소** → `kill $SERVER_PID; git worktree remove --force "$WORKTREE_DIR"; git branch -D $BR` 후 종료.

---

## 9️⃣ Commit + Push + PR + Merge

```bash
cd "$WORKTREE_DIR"
git add -A
git commit -m "feat: ${TITLES_SUMMARY}

- 카테고리: ${CATEGORIES}
- 템플릿: ${TEMPLATE}
- 처리 파일 수: ${OK_COUNT}"

git push -u origin "$BR"

# 빈 레포면 PR 안 됨 → 직접 base에 push
if ! git ls-remote --heads origin "$BASE_BRANCH" | grep -q "$BASE_BRANCH"; then
  git push origin "${BR}:${BASE_BRANCH}"
else
  gh pr create --head "$BR" --base "$BASE_BRANCH" \
    --title "feat: ${TITLES_SUMMARY}" \
    --body "${PR_BODY}"
  gh pr merge --squash --delete-branch
fi

git checkout "$BASE_BRANCH"
git pull origin "$BASE_BRANCH"
```

`gh` CLI 가 없으면 `git push origin "${BR}:${BASE_BRANCH}"` 로 직접 푸시 + 사용자에게 GitHub Pages 활성화 가이드 출력.

## 🔟 정리 + 결과 출력

```bash
kill $SERVER_PID 2>/dev/null
git worktree remove --force "$WORKTREE_DIR"
```

```
✅ 게시 완료!

📦 처리한 포스트 (N개):
   · #{postId1} {slug1} — {title1}   → {PAGES_URL}/posts/{postId1}/{slug1}.html
   · #{postId2} {slug2} — {title2}   → {PAGES_URL}/posts/{postId2}/{slug2}.html
   · [skip] {slug3} — already existed (use --overwrite to replace)

🏷️  카테고리: {cat}
🎨 템플릿: {template}
🌐 블로그: {PAGES_URL}
⏱️  반영: 1~2분 후 (GitHub Actions 자동 배포)
```

---

## ✏️ 편집 모드 (`edit`)

기존 게시글의 내용·제목·태그를 고치는 가장 빠른 방법. 워크트리·미리보기·자동 재빌드·승인 게이트가 한 번에 묶여 있어 "오타 1개 고치고 게시" 가 30초 안에 끝난다.

### 흐름

```
[1] /hams:diary-server edit msa-k8s-websocket     (또는 /hams:diary-server edit 1)
[2] 레포 clone/pull → 워크트리 생성
[3] target 해석:
    - 순수 정수 → posts[].postId 매칭
    - 그 외     → posts[].id (slug) 정확 매칭
    매칭 없음 → "slug / postId 일치 없음" 안내 후 종료
[4] entry 의 sourcePath 확인
    sourcePath 없음 → "_src/ 백업 부재" 안내 후 종료
[5] 기본 에디터로 _src/{slug}.{ext} 열기
[6] python -m http.server $PORT 백그라운드 실행
[7] 브라우저 자동 오픈 → http://localhost:8765/posts/{postId}/{slug}.html
[8] watch_and_rebuild.py 백그라운드 실행
    → _src/{slug}.{ext} mtime 변경 감지 시
    → 적절한 빌더 호출 (md → 변환, html → inject_html_adapter)
    → posts/{postId}/{slug}.html 갱신 + 콘솔에 [HH:MM:SS] rebuilt 출력
[9] 사용자가 에디터에서 저장할 때마다 (6)~(8)의 자동 빌드 발생
    브라우저에서 F5 로 변경 확인
[10] 편집 완료 후 AskUserQuestion: "이 변경을 게시할까요?"
       ✅ 게시 → commit + push + PR + merge (커밋 메시지: "edit: {title}")
       ❌ 취소 → 워크트리/브랜치 삭제, push 0회
[11] watcher 종료 + 서버 종료 + 워크트리 정리
```

### `_src/` 가 없는 기존 포스트

`/hams:diary-server` v1 시절(즉, `_src/` 백업 도입 이전)에 게시된 포스트는 `posts/{postId}/{slug}.html` 의 빌드 결과만 레포에 있다. 처리 경로:

- **HTML 시뮬레이터**: `publish --rebuild {slug|id}` 가 자동으로 `extract_original_html.py` 를 돌려 어댑터 마커 사이 블록을 제거 → 원본 복원 → `_src/` 에 저장 → 어댑터 재주입. 손에 원본 파일 없어도 됨.
- **MD 였던 포스트**: 역변환 비신뢰 (HTML→MD 손실). 원본 `.md` 가 손에 있다면 `--overwrite` 로 재배포해 `_src/` 백업 생성. 없으면 skip + 경고.

가장 안전한 길: 첫 게시 후엔 원본을 로컬에서 보관하지 말고, 항상 `_src/` 를 진실의 원본으로 사용한다.

### 명령어 호출 예

```bash
# Python watcher 호출 형태 (md)
python3 "${PLUGIN_ROOT}/skills/diary-core/watch_and_rebuild.py" \
  --src "_src/${slug}.md" --dst "posts/${postId}/${slug}.html" \
  --engine md --frame "_post-frame.html" \
  --title "${TITLE}" --category "${CAT}" \
  --date "${DATE}" --blog-title "${BLOG_TITLE}" &
WATCHER_PID=$!

# Python watcher 호출 형태 (html)
python3 "${PLUGIN_ROOT}/skills/diary-core/watch_and_rebuild.py" \
  --src "_src/${slug}.html" --dst "posts/${postId}/${slug}.html" \
  --engine html --title "${TITLE}" \
  ${NO_THEME:+--no-theme} &
WATCHER_PID=$!
```

### 메타데이터(제목·요약·카테고리·태그) 편집

본문이 아닌 메타만 바꾸고 싶으면 `_src/` 의 frontmatter(MD) 또는 `<title>`/`<meta>` 태그(HTML)를 수정하면 watcher 가 추출해 posts.json 도 갱신한다 (재빌드 시 메타 추출 로직이 동일하게 돌기 때문).

---

## 🔄 재빌드 모드 (`publish --rebuild`)

**언제 쓰나** — 어댑터 로직이 바뀌었거나 새로운 시그니처/테마/기능 토글을 기존 모든 글에 일괄 적용하고 싶을 때. 로컬에 원본 파일이 있을 필요가 없다 (레포의 `_src/` 또는 `posts/{postId}/{slug}.html` 역추출이 소스가 됨).

### 호출 형태

```bash
/hams:diary-server publish --rebuild msa-k8s-websocket          # 단일 (slug 또는 postId)
/hams:diary-server publish --rebuild 5                          # 단일 (숫자 ID)
/hams:diary-server publish --rebuild all                        # 전체
/hams:diary-server publish --rebuild --category msa             # 카테고리
```

### 흐름

```
[1] 설정 Read → REPO clone/pull → 워크트리 생성 (BR=rebuild-{TS})
[2] posts.json 로드 → 대상 entries 결정:
    - 순수 정수    : posts[].postId 매칭 단일 entry
    - {slug}      : posts[].id 매칭 단일 entry (없으면 종료)
    - all         : posts[] 전체
    - --category X: posts[].category == X 인 것들
[3] **postId 마이그레이션 검사** — entry 에 `postId` 가 없으면 현재 배열 순서대로 부여
    (이미 부여된 항목의 postId 는 절대 재배정 안 함)
[4] 첫 배포 판단 (index.html 부재 / 템플릿 변경) → 템플릿 다시 입힘
[5] 각 entry 에 대해 SOURCE 결정 (우선순위):
    a. _src/{slug}.{ext} 존재 → 그대로 사용
    b. engine == html, _src/ 없음:
       extract_original_html.py --src <기존 filename> --dst _src/{slug}.html
       → 원본 복원 후 (a) 와 같이 사용. _src/ 없는 옛날 글의 자가치유.
    c. engine == md, _src/ 없음 → skip + 경고 ("MD 역변환 비신뢰; 원본 .md 로 --overwrite 재배포 필요")
[6] 출력 경로 변경:
    OLD_FILENAME = entry['filename']             # 옛 경로
    NEW_FILENAME = f"posts/{postId}/{slug}.html" # 새 경로
    mkdir -p posts/{postId}/
    빌더 호출:
      - md  → markdown→html 변환 → _post-frame.html 치환 → NEW_FILENAME
      - html → inject_html_adapter.py --src _src/{slug}.html --dst NEW_FILENAME --title "{title}"
    OLD_FILENAME != NEW_FILENAME 이면 OLD_FILENAME 삭제 + 빈 부모 dir 정리
[7] posts.json 갱신: filename ← NEW_FILENAME, postId 채움, themeInjected/sourcePath/originalFilename(없으면 채움)
[8] 미리보기 서버 + 브라우저 오픈 → 첫 N개 (3개 권장) URL 안내
[9] AskUserQuestion 승인 게이트:
    ✅ 게시 → commit + push + PR + merge (메시지: "rebuild: re-apply adapter to N posts")
    ✏️ 수정 → 워크트리 두고 안내 후 종료 (사용자 직접 수정)
    ❌ 취소 → 워크트리/브랜치 삭제, push 0회
[10] 워크트리 정리
```

### 명령어 호출 예

```bash
# extract (HTML 역추출)
python3 "${PLUGIN_ROOT}/skills/diary-core/extract_original_html.py" \
  --src "${OLD_FILENAME}" --dst "_src/${slug}.html"

# 그 후 평소처럼 inject
python3 "${PLUGIN_ROOT}/skills/diary-core/inject_html_adapter.py" \
  --src "_src/${slug}.html" --dst "posts/${postId}/${slug}.html" \
  --title "${TITLE}" ${NO_THEME:+--no-theme}
```

### 안전장치

- 변경 없는 entry (재빌드 후 새 `posts/{postId}/{slug}.html` 바이트가 동일하고 경로도 동일) 는 commit 에서 자동 제외 (`git diff --quiet`)
- `all` 모드는 처리 전 AskUserQuestion 로 "총 N개 재빌드합니다. 계속?" 확인
- MD entry skip 시 결과 출력에서 `[skip] {slug} (MD, _src/ 없음)` 로 명시
- postId 마이그레이션 (옛 → 새 URL) 은 1회만 발생. 다음 rebuild 부터는 위 안전장치가 정상 동작

---

## 🗑 삭제 모드 (`delete`)

**언제 쓰나** — 잘못 올린 글, 더 이상 보여주기 싫은 글을 사이트에서 빼고 싶을 때. 파일 + posts.json entry + pagefind 인덱스가 한 번에 정리된다.

### 호출 형태 (다시)

```bash
/hams:diary-server delete 5                    # postId=5
/hams:diary-server delete "MSA Kubernetes"     # 제목 유사도
/hams:diary-server delete msa-k8s-websocket    # slug 정확/유사
/hams:diary-server delete 5 --yes              # 확인 생략 (스크립트용)
```

### 흐름 (요약)

```
[1] 활성 프로파일 결정 (--profile override 가능)
[2] REPO clone/pull → 워크트리 (BR=delete-{postId}-{TS})
[3] posts.json 로드 → 0-3.2 매칭 로직으로 entry 선정
    · 정수 → postId 정확 매칭
    · 문자열 → title 부분일치 / slug 부분일치 / SequenceMatcher 유사도 ≥0.5
    · 후보 다건 → AskUserQuestion 으로 선택
[4] 삭제 미리보기 출력 + (--yes 없으면) AskUserQuestion 확인
[5] 파일 삭제:
    - posts/{postId}/{slug}.html
    - posts/{postId}/  디렉토리 (안 비면 경고 — 정상 시 비어있다)
    - _src/{slug}.{ext}
    - posts.json posts[] 에서 entry pop
    - 해당 entry 가 유일한 사용자였던 카테고리는 categories[] 에서 제거
[6] Pagefind 재빌드 (search === true 일 때) — 인덱스에 삭제된 페이지 잔여 방지
[7] 미리보기 서버 + 브라우저 → 목록에서 사라짐 확인
[8] AskUserQuestion 승인 → ✅ commit/push/PR/merge (메시지: "delete: {title} (#{postId})") | ❌ 취소
[9] 워크트리 정리
```

### 명령어 호출 예

```bash
# entry 결정 후 파일 정리
rm -f "posts/${postId}/${slug}.html"
rmdir "posts/${postId}" 2>/dev/null    # 비어있으면 제거 (정상)
rm -f "_src/${slug}.html"

# posts.json 갱신 (Python 한 줄)
python3 -c "
import json, sys
p = 'posts.json'
d = json.load(open(p, encoding='utf-8'))
d['posts'] = [x for x in d['posts'] if x.get('postId') != ${postId}]
# 카테고리 정리 (categories 배열 union, insertion order)
def cats_of(x):
    if isinstance(x.get('categories'), list): return x['categories']
    return [x['category']] if x.get('category') else []
used, seen = [], set()
for x in d['posts']:
    for c in cats_of(x):
        if c not in seen:
            seen.add(c); used.append(c)
d['categories'] = used
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"

# pagefind 재빌드 (검색 활성 시)
[ "$FEATURES_SEARCH" = "true" ] && npx -y pagefind --site . --output-path pagefind
```

### 안전장치

- **postId 재사용 금지** — 5번을 삭제해도 다음 신규 글은 (현재 최대값 + 1) 받음. 이건 강한 규칙이다.
- 매칭 다건 시 사용자가 선택할 때까지 파일은 1바이트도 안 건드림.
- `--yes` 없으면 항상 확인 프롬프트 1회 + push 직전 승인 1회 = 2단계 안전장치.
- 파일은 있는데 entry 없는 (또는 그 반대) 비정상 상태는 1회 경고 출력하고 가능한 만큼 정리.

---

## 강의자료 특화 향후 확장 (미구현)

다음은 본 스킬에는 포함되어 있지 않지만 강의자료 운영에 유용한 기능들. 백로그.

1. **시리즈 그룹핑** — `series` 필드로 "MSA 강의 1주차" 같은 묶음 자동 생성
2. **공개 토글** — `published: false` 로 게시는 했지만 목록에서 숨김
3. **선수 학습 링크** — `prereq: ["msa-k8s-websocket"]`
4. **slide 모드** — `?mode=slide` 로 발표용 풀스크린 변환
5. **자동 ToC** — H2/H3 구조에서 우측 sticky ToC

필요해지면 별도 phase 로 추가.

---

## 에러 처리

| 케이스 | 처리 |
|------|-----|
| 설정 파일 없음 | AskUserQuestion 으로 URL 받기 → 저장 후 계속 |
| Clone 실패 | git config user.name/email · PAT/SSH 안내 |
| 한글 파일명 안 보임 | PowerShell `Get-ChildItem -LiteralPath` 폴백 |
| 빈 레포 | 첫 배포는 BR 을 직접 BASE_BRANCH 로 push |
| 미리보기 서버 포트 점유 | `--preview-port` 로 변경 또는 자동 incrementー 8765→8766→… |
| 브라우저 자동 오픈 실패 | URL 출력 후 사용자에게 직접 열도록 안내 |
| 사용자 ❌ 선택 | 워크트리/브랜치 삭제, push 0회, 깨끗하게 종료 |

---

## 내부 구현 체크리스트 (Claude 가 따를 순서)

### 공통 (모든 서브명령 진입 시)

- [ ] **인자 토큰 분류** — `publish` / `edit` / `delete` / `config <sub>` / `option` / 그 외
- [ ] **설정 자동 마이그레이션** — `~/.claude/hams-diary.json` Read → flat schema(`{repo, template, ...}`)면 `.bak` 백업 후 `{active, profiles}` 로 변환 (0-1 로직)
- [ ] 그 외 토큰이면 "알 수 없는 명령. `/hams:diary-server option` 으로 사용법을 확인하세요" 출력 후 종료

### `option` 분기

- [ ] 0-4의 출력 양식 그대로 출력. 어떤 외부 동작도 안 함. 종료.

### `config` 분기

- [ ] `cfg['profiles'][cfg['active']]` 를 P로 가져옴 (없으면 P = {})
- [ ] 0-3 표대로 처리:
  - `show` → cfg 보기 좋게 출력
  - `repo` / `template` / `search` / `blog-title` → P 갱신
  - `profile list` / `profile add` / `profile use` / `profile remove` → cfg 직접 갱신
  - 옛 `comments` 서브명령은 폐기 — 받으면 "지원하지 않는 명령" 안내 후 종료
- [ ] `json.dump(cfg, p, ensure_ascii=False, indent=2)` 저장
- [ ] 종료 (publish/edit/delete 안 트리거)

### `publish` 분기

- [ ] 인자에서 `--profile {name}` 추출 → 없으면 `cfg['active']`
- [ ] `cfg['profiles'][name]` 검증 (없으면 에러 종료: "프로파일 없음. /hams:diary-server config profile list 로 확인")
- [ ] 활성 프로파일에서 PROFILE_NAME, REPO_URL, OWNER, NAME, PAGES_URL, TEMPLATE, BLOG_TITLE, FEATURES, LOCAL_DIR, WORKTREE_DIR 결정 (0-5)
- [ ] **JOBS 배열 구성** — 단일/디렉토리/글롭 분기, 한글 파일명 PowerShell 폴백
- [ ] 각 job 메타 추출 (title/summary/tags/slug/categories, **originalFilename**)
- [ ] **categories 정규화** — CLI 인자 (쉼표 구분 → 배열), 단일 string 도 호환. 비어있으면 AskUserQuestion `multiSelect: true` 로 기존 + "신규 입력"
- [ ] LOCAL_DIR clone/pull
- [ ] WORKTREE_DIR worktree add (`BR=post-preview-${TS}`)
- [ ] 첫 배포 판단 (index.html 부재 또는 .diary-meta.json template 다름) → 템플릿 복사 + {{BLOG_*}} 치환 + .nojekyll
- [ ] BLOG_TITLE 등 미설정시 AskUserQuestion → P에 저장
- [ ] posts.json 로드 (없으면 빈 구조)
- [ ] **postId 마이그레이션** — 기존 entry 에 postId 없으면 현재 배열 순서대로 1, 2, 3... 부여 (이미 부여된 ID 는 보존)
- [ ] **categories 마이그레이션** — 기존 entry 에 옛 단일 `category` 만 있으면 `entry['categories'] = [entry.pop('category')]` 로 변환
- [ ] **각 job: 3단계 매칭** (originalFilename → slug → 제목 유사도 ≥0.85+같은 engine), 매칭 발견 시 기존 postId/slug 재사용. `--overwrite` 미설정이면 skip, 설정이면 in-place 교체 (categories 갱신). 매칭 없음이면 `max(postId)+1` 부여 후 신규 삽입.
- [ ] **글로벌 categories[] 갱신** — entry.categories 의 모든 항목을 글로벌 `categories[]` 에 union (insertion order)
- [ ] posts.json 워크트리에 Write
- [ ] **각 job 실행**:
  - `mkdir -p posts/{postId}/`
  - md → 인라인 변환 또는 markdown 라이브러리 → `_post-frame.html` 치환 → `posts/{postId}/{slug}.html` 기록
  - html → `inject_html_adapter.py --src --dst posts/{postId}/{slug}.html --title [--no-theme]` 호출
  - **원본 백업**: `cp ${SRC} _src/${slug}.${EXT}` + posts.json 에 `postId`, `sourcePath`, `originalFilename`, `filename` 필드 기록
- [ ] **미리보기 서버 시작** — `python3 -m http.server $PORT &` (PID 저장)
- [ ] **브라우저 자동 오픈** — OS별 분기 (start/open/xdg-open)
- [ ] **AskUserQuestion 승인 게이트** — ✅게시 / ✏️수정 / ❌취소
- [ ] 사용자 응답 처리:
  - ✅: commit + push + PR (gh 없으면 직접 push) + merge → 워크트리 정리
  - ✏️: 사용자 피드백 받아 재빌드 또는 워크트리 그대로 두고 안내 후 종료
  - ❌: kill server, worktree remove, branch delete, 종료
- [ ] **결과 출력** — 성공한 포스트 목록, skip된 항목, 블로그 URL, 반영 예상 시간
- [ ] (`--draft` 케이스) push 건너뛰고 워크트리 보존, 위치 안내

### `publish --rebuild` 분기 (재빌드 모드)

- [ ] 활성/`--profile` 프로파일 결정 (위와 동일)
- [ ] 워크트리 생성 (`BR=rebuild-${TS}`)
- [ ] posts.json 로드 → 대상 entries 결정 (slug / postId / all / `--category X`)
  - 빈 결과 → "대상 없음" 안내 후 종료
- [ ] **postId 마이그레이션** — 기존 entry 에 postId 없으면 현재 배열 순서대로 부여
- [ ] **categories 마이그레이션** — 옛 `category` 만 있으면 `categories: [category]` 로 변환 + 글로벌 `categories[]` union
- [ ] `all` 모드면 AskUserQuestion 으로 "총 N개 재빌드합니다. 계속?" 확인
- [ ] 첫 배포 판단 → 템플릿 다시 입힘
- [ ] **각 entry 처리**:
  - SOURCE 결정: (a) `_src/{slug}.{ext}` → (b) html+없음→`extract_original_html.py` (src=현재 `entry['filename']`) → (c) md+없음→skip+경고
  - `mkdir -p posts/{postId}/`
  - 빌더 호출: md→마크다운 변환+`_post-frame.html` 치환 → `posts/{postId}/{slug}.html` / html→`inject_html_adapter.py --dst posts/{postId}/{slug}.html`
  - `entry['filename']` 갱신 → `posts/{postId}/{slug}.html`
  - 기존 파일이 새 경로와 다르면 옛 경로 + 빈 부모 dir 삭제 (URL 변경 마이그레이션 1회)
  - `originalFilename` 비어있으면 entry 의 `id`/`title` 으로 추정해 채우기 (마이그레이션)
  - posts.json 의 `themeInjected`/`sourcePath` 갱신
- [ ] posts.json Write
- [ ] 미리보기 서버 시작 + 첫 3개 URL 안내
- [ ] **AskUserQuestion 승인 게이트** — ✅게시 / ✏️수정 / ❌취소
- [ ] ✅: `git diff --quiet` 인 entry 는 자동 제외 → commit (메시지: "rebuild: re-apply adapter to N posts") + push + PR + merge → 워크트리 정리
- [ ] ✏️: 워크트리 두고 안내 후 종료
- [ ] ❌: 서버 종료 → 워크트리·브랜치 삭제

### `edit` 분기

- [ ] 활성/`--profile` 프로파일 결정
- [ ] 설정 Read + REPO clone/pull
- [ ] 워크트리 생성 (`BR=edit-${slug}-${TS}`)
- [ ] target 해석:
  - 순수 정수 → `posts[].postId == int(target)` 으로 entry 검색
  - 그 외 → `posts[].id == target` 으로 entry 검색
  - 없음 → "slug / postId 일치 없음" 안내 후 종료
  - 있음 + sourcePath 없음 → "원본 백업 부재" 안내 후 종료
- [ ] entry 의 postId/slug 추출 → 새 path = `posts/{postId}/{slug}.html`
- [ ] 메타(title, category, date, blog_title) 추출 → watcher 인자로 전달
- [ ] 기본 에디터로 `_src/{slug}.{ext}` 오픈 (Windows: `start ""`, mac: `open`, linux: `xdg-open`)
- [ ] `python -m http.server $PORT` 백그라운드 시작 → 브라우저 자동 오픈 (`http://localhost:$PORT/posts/{postId}/{slug}.html`)
- [ ] `watch_and_rebuild.py` 백그라운드 시작 (engine = entry.engine, 인자 전달, --dst = posts/{postId}/{slug}.html)
- [ ] **사용자 편집 대기** — "편집 완료 후 답변하세요"
- [ ] AskUserQuestion: "이 변경을 게시할까요?" (✅게시 / ❌취소)
- [ ] ✅: watcher·서버 종료 → commit + push + PR + merge → 워크트리 정리
- [ ] ❌: watcher·서버 종료 → 워크트리·브랜치 삭제 → push 0회로 종료

### `delete` 분기

- [ ] 활성/`--profile` 프로파일 결정
- [ ] 설정 Read + REPO clone/pull
- [ ] 워크트리 생성 (`BR=delete-${TS}` — entry 확정 후 `delete-${postId}-${TS}` 로 rename 도 가능)
- [ ] posts.json 로드
- [ ] target 해석 (0-3.2 로직):
  - 순수 정수 → postId 정확 매칭
  - 그 외 → 제목 부분일치 / slug 부분일치 / SequenceMatcher 유사도 ≥0.5
- [ ] 후보 0건 → "일치 없음" 안내 후 종료
- [ ] 후보 다건 → AskUserQuestion 으로 선택 (옵션 라벨: `[#{postId}] {title} (slug={id})`)
- [ ] 삭제 미리보기 출력
- [ ] `--yes` 없으면 AskUserQuestion: "정말 삭제?" (✅/❌). ❌이면 워크트리/브랜치 삭제 후 종료
- [ ] **파일·entry 정리**:
  - `os.remove(f'posts/{postId}/{slug}.html')`
  - `os.rmdir(f'posts/{postId}')` (실패하면 경고만 — 다른 파일 남아있는 비정상)
  - `os.remove(f'_src/{slug}.{ext}')` (있을 때만)
  - posts.json `posts[]` 에서 entry pop
  - 카테고리 정리 (위 코드 예 참조)
- [ ] Pagefind 재빌드 (search 활성 시)
- [ ] 미리보기 서버 시작 + 브라우저 오픈 → 목록에서 사라진 것 확인
- [ ] AskUserQuestion: "push 할까요?" (✅/❌)
- [ ] ✅: commit (메시지: `delete: {title} (#${postId})`) → push → PR → merge → 워크트리 정리
- [ ] ❌: 워크트리·브랜치 삭제, push 0회

---

## 참고

- 설정: `~/.claude/hams-diary.json` — 스키마 `{activeServer, activeLocal, profiles: {<name>: {repo, template, blogTitle?, pagesUrl?, features?}}}`. 옛 flat 형태(`{repo, template, ...}`)는 첫 호출 시 `default` 프로파일로 자동 마이그레이션 (`.bak` 백업 후).
- 템플릿: `${PLUGIN_ROOT}/skills/diary-core/templates/{minimal|tech|lecture|notebook|magazine}/`
- HTML 어댑터 빌더: `${PLUGIN_ROOT}/skills/diary-core/inject_html_adapter.py`
- HTML 어댑터 역추출: `${PLUGIN_ROOT}/skills/diary-core/extract_original_html.py` (재빌드 모드 fallback)
- 편집 모드 워처: `${PLUGIN_ROOT}/skills/diary-core/watch_and_rebuild.py`
- 레포 메타: `{REPO}/.diary-meta.json` (현재 적용된 템플릿 기록)
- 원본 백업: `{REPO}/_src/{slug}.{md|html}` (편집·재빌드 모드용)
