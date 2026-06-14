---
name: diary-local
description: |
  로컬 마크다운(.md)/HTML을 로컬 전용 정적 블로그로 렌더해 브라우저에서 열람하는 도구.
  GitHub에 올리지 않는다 — 비공개 노트·spec·초안용. 공개 발행은 /hams:diary-server.
  사용법:
    /hams:diary-local publish {file|dir|glob} [category]   # 로컬 폴더에 렌더
    /hams:diary-local serve [profile] [--port N]           # http.server + 브라우저
    /hams:diary-local edit {slug|id}                       # 편집 + 라이브 재빌드
    /hams:diary-local delete {title|id}                    # 삭제
    /hams:diary-local config <subcommand>                  # 설정(프로파일)
    /hams:diary-local option                               # 사용법
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
  - PowerShell
---

# /hams:diary-local

로컬 마크다운·HTML을 **로컬 전용 정적 블로그**로 렌더한다. git·GitHub·push 일절 없음. 산출물은 프로파일의 로컬 디렉터리(`dir`)에 쌓이고, `serve`로 `http.server`를 띄워 브라우저에서 본다. 목록·카테고리 필터·Pagefind 검색은 HTTP가 필요하므로 `file://`이 아니라 `serve`로 연다.

발행(공개)이 필요하면 `/hams:diary-server`. 렌더 결과물·템플릿·검색 동작은 server와 동일(코어 공유).

## 0️⃣ 인자 해석 & 설정

### 0-1. 설정 로드 (공유 모듈)

`python3`로 `${PLUGIN_ROOT}/skills/diary-core/diary_config.py` 사용:
- `cfg = diary_config.load()`; 없으면 0-1.1로 초기화
- `cfg, changed = diary_config.migrate(cfg)`; `changed`면 `diary_config.save(cfg, backup=True)`
- 활성 프로파일: `name, P = diary_config.resolve(cfg, "local", override=<--profile|None>)`
  - `ValueError`("no active local profile")면 0-1.1로 첫 로컬 프로파일 생성 유도
  - `ValueError`("type 'server'…")면 "이 프로파일은 발행용입니다 — /hams:diary-server 사용" 안내 후 종료

로컬 프로파일 스키마: `{ "type": "local", "dir": "<로컬 절대경로>", "template": "minimal", "features": {"search": true} }`. `repo`/`pagesUrl` 없음.

### 0-1.1 첫 로컬 프로파일 초기화

로컬 프로파일이 없으면 AskUserQuestion으로 (a) 프로파일 이름(기본 `local`), (b) 출력 디렉터리(기본 `~/.claude/hams-diary-local/<이름>`), (c) 템플릿(기본 `minimal`)을 받아:
```python
cfg.setdefault("profiles", {})[name] = {"type": "local", "dir": <expanded>, "template": <tmpl>, "features": {"search": True}}
cfg["activeLocal"] = name
diary_config.save(cfg)
```
`dir`은 `os.path.expanduser`로 절대경로화 후 `os.makedirs(dir, exist_ok=True)`.

### 0-2. 서브명령 라우팅

| 토큰 | 분기 |
|---|---|
| `publish` | 1️⃣~6️⃣ (git 없음) |
| `serve` | 7️⃣ |
| `edit {slug|id}` | 8️⃣ |
| `delete {title|id}` | 9️⃣ |
| `config <sub>` | 0-3 |
| `option` | 0-4 (read-only) |
| 그 외 | "알 수 없는 명령. /hams:diary-local option" 안내 후 종료 |

### 0-3. config 서브명령

`P = 활성 로컬 프로파일`. 갱신 후 `diary_config.save(cfg)`.

| 명령 | 동작 |
|---|---|
| `config show` | cfg 전체 + activeLocal 강조 |
| `config dir {path}` | `P['dir'] = expanduser(path)` + makedirs |
| `config template {1-5\|name}` | `TEMPLATES=['minimal','tech','lecture','notebook','magazine']` 검증 후 `P['template']` |
| `config search {on\|off}` | on이면 `npx -y pagefind --version` 사전체크 → `P['features']['search']` |
| `config blog-title "{t}"` | `P['blogTitle']=t` |
| `config profile list` | `type=="local"` 프로파일 목록 + activeLocal 표시 |
| `config profile add {name} {dir}` | 이름 충돌 검사 → `{type:'local', dir:expanduser(dir), template:'minimal', features:{search:true}}` 등록 + makedirs |
| `config profile use {name}` | `diary_config.set_active(cfg, name)` (로컬 아니면 거부) |
| `config profile remove {name}` | activeLocal이면 다른 로컬로 전환(없으면 None) |

### 0-4. option (read-only)

어떤 외부 동작도 없이 서브명령·플래그·5템플릿·예시·현재 설정(activeLocal 프로파일의 dir/template/search)을 출력하고 종료.

## 1️⃣~5️⃣ 렌더 (공유)

`$BLOG_DIR = P['dir']`로 세팅하고 `${PLUGIN_ROOT}/skills/diary-core/RENDER.md`의 단계를 그대로 수행한다:
입력 분류 → 메타 추출 → (첫 실행이면) 템플릿 복사 → posts.json 매칭/갱신 → 포스트 HTML 생성(`posts/{postId}/{slug}.html`) → `_src/` 백업 → 검색 블록 → Pagefind 인덱스.

**server와의 유일한 차이:** clone/worktree/commit/push/PR/merge가 **전혀 없다.** `$BLOG_DIR`은 git 워크트리가 아니라 그냥 로컬 폴더이고, 파일을 그 자리에서 직접 만든다.

플래그: `--no-theme` `--overwrite` `--rebuild [slug|all|--category X]` `--profile` `--fit-viewport` `--scale-up` `--preview-port`. (`--draft`는 없음 — 로컬은 항상 "초안".)

publish 완료 출력:
```
✅ 로컬 렌더 완료 (N개) → {dir}
   · #{postId} {slug} — {title}
▶ 보기:  /hams:diary-local serve {profileName}
```

## 6️⃣ (승인 게이트 없음)

로컬은 push가 없으므로 publish 후 바로 끝난다. 사용자가 결과를 보려면 7️⃣ serve.

## 7️⃣ serve — 로컬 서버 + 브라우저

```bash
DIR="${P_DIR}"                      # 활성(또는 인자) 로컬 프로파일의 dir
PORT="${PREVIEW_PORT:-8765}"
cd "$DIR"
python3 -m http.server "$PORT" >/tmp/diary-local-$PORT.log 2>&1 &
SERVER_PID=$!
sleep 1
URL="http://localhost:${PORT}/"
case "$(uname -s)" in
  MINGW*|CYGWIN*|MSYS*) start "$URL" ;;
  Darwin) open "$URL" ;;
  Linux) xdg-open "$URL" >/dev/null 2>&1 || true ;;
esac
```

- `serve [profile]`로 프로파일 지정 가능(생략 시 activeLocal). 포트 점유 시 `--port`로 변경 또는 8765→8766 자동 증가.
- **장시간 열람용**이므로 Bash `run_in_background`로 띄우고 PID·URL·종료법(`kill $SERVER_PID`)을 안내한다. publish 직후 "지금 serve 할까요?" AskUserQuestion 제안 가능.
- 개별 글: `http://localhost:${PORT}/posts/{postId}/{slug}.html`.

## 8️⃣ edit — 편집 + 라이브 재빌드 (push 없음)

```
[1] target 해석: 정수→posts[].postId / 그 외→posts[].id(slug). $DIR/posts.json 기준.
[2] entry.sourcePath 확인 (없으면 "_src 백업 부재" 안내 종료)
[3] 에디터로 $DIR/_src/{slug}.{ext} 오픈 (start/open/xdg-open)
[4] $DIR에서 python3 -m http.server 백그라운드 + 브라우저 오픈
[5] watch_and_rebuild.py (코어) 백그라운드:
    python3 ${PLUGIN_ROOT}/skills/diary-core/watch_and_rebuild.py \
      --src "$DIR/_src/{slug}.{ext}" --dst "$DIR/posts/{postId}/{slug}.html" \
      --engine {md|html} [--frame "$DIR/_post-frame.html"] [--title ...] [--no-theme]
[6] 저장 시 자동 재빌드 → 브라우저 F5
[7] 완료 시 watcher·서버 종료. 커밋 없음 (로컬 파일이 곧 결과).
```

## 9️⃣ delete — 삭제 (push 없음)

```
[1] target 해석 (정수=postId 정확 / 문자열=title·slug 부분일치·SequenceMatcher≥0.5; 다건이면 AskUserQuestion)
[2] 삭제 미리보기 + (--yes 없으면) 확인
[3] $DIR에서: rm posts/{postId}/{slug}.html; rmdir posts/{postId}; rm _src/{slug}.{ext};
    posts.json에서 entry pop + categories[] 재계산 (RENDER.md 매칭 코드 동일)
[4] search 활성 시 cd $DIR && npx -y pagefind --site . --output-path pagefind
[5] (선택) serve로 사라짐 확인. 커밋 없음.
```

## 에러 처리

| 케이스 | 처리 |
|------|-----|
| 로컬 프로파일 없음 | 0-1.1로 생성 유도 |
| 활성 프로파일이 server 타입 | "발행용 — /hams:diary-server 사용" 안내 후 종료 |
| dir 없음 | `os.makedirs(dir, exist_ok=True)` |
| 포트 점유 | `--port` 또는 자동 증가 |
| 한글 파일명 안 보임 | RENDER.md의 PowerShell `Get-ChildItem -LiteralPath` 폴백 |

## 참고

- 설정: `~/.claude/hams-diary.json` (server와 공유, `diary_config.py`). 로컬은 `type:"local"` + `dir`, `activeLocal` 포인터.
- 렌더 단계: `${PLUGIN_ROOT}/skills/diary-core/RENDER.md`
- 스크립트: `${PLUGIN_ROOT}/skills/diary-core/{inject_html_adapter,extract_original_html,watch_and_rebuild}.py`
- 출력: `{dir}/posts/{postId}/{slug}.html`, 원본 백업 `{dir}/_src/{slug}.{md|html}`, 검색 `{dir}/pagefind/`
