---
name: lec
description: |
  강의 슬라이드(HTML) · 시뮬레이터(HTML) · 판서 대본(비공개)을 한 회차로 묶어
  GitHub Pages 강의 전용 블로그에 배포하는 도구. 판서 대본은 비밀번호로 암호화(AES-GCM)되어
  올라가므로 나만 볼 수 있다. 배포 전 로컬 미리보기 → 승인 후에만 push.
  panseo-slide / edu-sim-builder 로 만든 결과물을 그대로 회차별로 묶어 운영하기 좋다.
  사용법:
    /hams:lec publish --no "1강" --title "..." [--slide f] [--sim f] [--script f] [옵션]
    /hams:lec edit {id|slug}
    /hams:lec delete {id|slug}
    /hams:lec config <subcommand>
    /hams:lec option
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
  - PowerShell
---

# /hams:lec

panseo-slide·edu-sim-builder 로 만든 **강의 슬라이드 / 시뮬레이터 / 판서 대본**을 한 회차(lecture)로 묶어 **GitHub Pages 강의 블로그**에 배포한다. 갤럭시 탭 등에서 URL 하나로 슬라이드를 열어 판서·녹화하고, 시뮬레이터로 넘어가고, 대본은 비밀번호로 잠가 나만 본다.

## 핵심 가치

1. **회차 = 묶음** — 한 강의(회차)에 슬라이드·시뮬레이터·대본 최대 3개가 묶인다. 셋 다 선택사항.
2. **강의 목록 인덱스** — 자동 생성되는 홈에서 섹션(부/주차)별로 회차 카드가 정렬되고, 각 카드에 `▶ 슬라이드 · 🧪 시뮬레이터 · 🔒 대본` 버튼.
3. **대본은 나만 보기** — 판서 대본은 **AES-GCM 으로 암호화**되어 올라간다. 비밀번호 없이는 암호문만 보이고, 비밀번호는 레포에 저장되지 않는다. `robots.txt` + `noindex` 로 검색엔진에서도 가려진다.
4. **목업 후 게시** — 로컬 미리보기 서버 → 브라우저 검수 → 승인 → push (diary 와 동일한 안전 흐름).
5. **단일 HTML 보존** — 슬라이드·시뮬레이터 HTML 은 그대로 서빙(하단에 "← 강의 목록" 네비바만 주입). panseo-slide 의 펜 판서·풀스크린이 그대로 동작.

> **GitHub Pages 비공개 한계(반드시 사용자에게 고지)** — 무료 GitHub Pages 는 본질적으로 공개다. 서버 단의 접근 제어는 없다. 그래서 대본은 *클라이언트 암호화*로 보호한다 — 강력한 비밀번호를 쓰면 실질적으로 안전하지만, 비밀번호를 잊으면 복구 불가다. 더 강한 비공개가 필요하면 `scriptMode: local`(대본을 아예 push 하지 않고 로컬 보관) 을 안내한다.

---

## 사용 방법

5개 서브명령: `publish` · `edit` · `delete` · `config` · `option`.

### `publish` — 강의 올리기

```bash
/hams:lec publish --no "1강" --title "어텐션이란?" \
  --slide ./slide.html --sim ./sim.html --script ./script.md \
  --summary "전학생 비유로 보는 self-attention" --section "1부 · 트랜스포머 기초"

# 플래그
--no "1강"            # 회차 라벨(카드 좌측 뱃지). 필수
--title "..."         # 강의 제목. 필수
--slide  PATH         # panseo-slide HTML (선택)
--sim    PATH         # edu-sim-builder HTML (선택)
--script PATH         # 판서 대본 .md 또는 .html (선택, 암호화 게시)
--summary "..."       # 카드 한 줄 설명 (선택)
--section "..."       # 섹션 그룹(부/주차) 라벨 (선택)
--id N                # 회차 ID 직접 지정(기본: 자동 증가). edit/overwrite 용
--no-bar              # 슬라이드/시뮬에 "← 강의 목록" 네비바 주입 끄기
--draft               # push 안 하고 워크트리만 남김
--preview-port N      # 미리보기 포트(기본 8770)
--profile NAME        # 1회 임시 프로파일 override
```

`--slide/--sim/--script` 가 하나도 없으면 에러. 셋 중 무엇이든 조합 가능(대본만 올리는 것도 가능).

### `edit` — 강의 고치기

```bash
/hams:lec edit 1            # lecId=1
/hams:lec edit attention    # slug
# → 해당 회차의 현재 자료를 보여주고, 어떤 파일을 교체할지 물어
#   --slide/--sim/--script 새 경로로 재빌드(같은 id 유지 = URL 보존).
```

### `delete` — 강의 빼기

```bash
/hams:lec delete 1          # lecId=1 (정수 = 정확 매칭)
/hams:lec delete "어텐션"    # 제목 유사도 매칭
# → 미리보기로 사라진 것 확인 → 승인 → push. lecId 는 재사용하지 않는다.
```

### `config` — 설정

```bash
/hams:lec config show
/hams:lec config repo https://github.com/me/lectures.git
/hams:lec config blog-title "AI 네이티브 엔지니어링"
/hams:lec config tagline "비유로 익히는 AI 엔지니어링"
/hams:lec config script-mode {encrypt|local|off}   # 대본 처리 방식
# 멀티 블로그
/hams:lec config profile add ai https://github.com/me/ai-lectures.git
/hams:lec config profile use ai
```

### `option` — 사용법 한눈에 (read-only, 외부 동작 없음)

---

## 0️⃣ 설정 & 라우팅

**설정 파일**: `~/.claude/hams-lec.json`

```json
{
  "active": "default",
  "profiles": {
    "default": {
      "repo": "https://github.com/me/lectures.git",
      "blogTitle": "AI 네이티브 엔지니어링",
      "tagline": "비유로 익히는 AI 엔지니어링",
      "hero": "AI 네이티브 엔지니어링",
      "pagesUrl": "https://me.github.io/lectures/",
      "scriptMode": "encrypt"
    }
  }
}
```

- 첫 토큰으로 `publish|edit|delete|config|option` 분기. 그 외엔 "알 수 없는 명령. `/hams:lec option`" 안내 후 종료.
- 설정 파일이 없고 publish/edit/delete 호출이면 AskUserQuestion 으로 repo URL 을 받아 초기화.
- `scriptMode`:
  - `encrypt` (기본) — 대본을 비밀번호로 암호화해 게시. 비번 없이는 암호문만.
  - `local` — 대본을 push 하지 않음. `_scripts/{id}.{ext}` 로 워크트리에만 두고 안내(진짜 비공개).
  - `off` — 대본 무시(슬라이드·시뮬만).
- 변수 추출: `REPO_URL, OWNER, NAME, PAGES_URL(=https://{OWNER}.github.io/{NAME}/), BLOG_TITLE, TAGLINE, HERO, LOCAL_DIR=/tmp/{NAME}-{PROFILE}, WORKTREE_DIR=/tmp/{NAME}-{PROFILE}-preview-{TS}`.

`PLUGIN_ROOT` 은 이 SKILL.md 의 두 단계 상위(플러그인 루트). 빌더는 `${PLUGIN_ROOT}/skills/lec/build_lecture.py`.

---

## 1️⃣ publish 흐름 (Claude 가 따르는 순서)

1. **인자 파싱** — `--no --title` 필수, `--slide/--sim/--script` 중 1개 이상 필수. 입력 파일 존재 확인(절대경로화).
2. **프로파일 결정** (`--profile` 또는 active). repo 미설정이면 AskUserQuestion 으로 받기.
3. **레포 준비**:
   ```bash
   [ -d "$LOCAL_DIR" ] || git clone "$REPO_URL" "$LOCAL_DIR"
   cd "$LOCAL_DIR"
   BASE=$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p'); [ -z "$BASE" ] && BASE=main
   git fetch origin || true; git checkout "$BASE" 2>/dev/null || git symbolic-ref HEAD refs/heads/$BASE
   git pull origin "$BASE" 2>/dev/null || true
   TS=$(date +%Y%m%d-%H%M%S); BR="lec-$TS"
   git worktree add -b "$BR" "$WORKTREE_DIR"; cd "$WORKTREE_DIR"
   ```
4. **회차 ID 결정** — `--id` 있으면 그것, 없으면 `lectures.json` 의 `max(lecId)+1`(없으면 1). **삭제된 ID 는 재사용 금지**(URL 안정성). slug 는 `--title` 의 kebab(영문)이나 사용자 입력.
5. **대본 비밀번호 처리** (scriptMode=encrypt 이고 `--script` 있을 때):
   - AskUserQuestion 또는 안전 입력으로 비밀번호를 받는다(화면 로그에 남기지 말 것).
   - 빌더 호출 시 `LEC_SCRIPT_PASSCODE` **환경변수**로만 전달(명령행 인자로 노출 금지).
   - 같은 블로그의 모든 대본은 같은 비밀번호를 쓰도록 권장(사용자가 1개만 기억).
   - scriptMode=local 이면 암호화 대신 `_scripts/{id}.{ext}` 복사 + 안내. off 면 대본 생략.
6. **빌더 실행**:
   ```bash
   LEC_SCRIPT_PASSCODE="$PW" python3 "${PLUGIN_ROOT}/skills/lec/build_lecture.py" \
     --repo-dir "$WORKTREE_DIR" --plugin-root "$PLUGIN_ROOT" \
     --id "$ID" --no "$NO" --title "$TITLE" --slug "$SLUG" \
     --summary "$SUMMARY" --section "$SECTION" \
     ${SLIDE:+--slide "$SLIDE"} ${SIM:+--sim "$SIM"} ${SCRIPT:+--script "$SCRIPT"} \
     --date "$(date +%F)" --blog-title "$BLOG_TITLE" --tagline "$TAGLINE" \
     --hero "$HERO" --year "$(date +%Y)" ${NO_BAR:+--no-bar}
   ```
   빌더가 첫 배포면 템플릿(index.html, assets/, .nojekyll, robots.txt)을 깔고, 에셋 배치 + 대본 암호화 + `lectures.json` 업서트를 한다.
7. **미리보기**:
   ```bash
   PORT=${PREVIEW_PORT:-8770}; python3 -m http.server $PORT >/tmp/lec-preview.log 2>&1 &
   SERVER_PID=$!; sleep 1
   # OS별 브라우저 오픈: start(win) / open(mac) / xdg-open(linux)
   # 안내 URL: http://localhost:$PORT/  ·  /lectures/$ID/slide.html  ·  /lectures/$ID/script.html
   ```
   대본 게이트는 미리보기에서 직접 비밀번호 입력해 복호화 확인하도록 안내.
8. **승인 게이트** (AskUserQuestion): ✅ 게시 / ✏️ 수정 / ❌ 취소.
9. **push**:
   ```bash
   git add -A
   git commit -m "lec: #$ID $NO $TITLE"
   git push -u origin "$BR"
   if git ls-remote --heads origin "$BASE" | grep -q "$BASE"; then
     git push origin "$BR:$BASE"   # gh 없으면 직접 머지 push
   else
     git push origin "$BR:$BASE"   # 빈 레포 첫 배포
   fi
   git checkout "$BASE"; git pull origin "$BASE"
   ```
   `gh` CLI 가 있으면 PR→merge 도 가능. 없으면 위처럼 fast-forward push.
10. **정리 + 결과**:
    ```bash
    kill $SERVER_PID 2>/dev/null; git worktree remove --force "$WORKTREE_DIR"
    ```
    ```
    ✅ 게시 완료
       · #{ID} {NO} {TITLE}
         ▶ 슬라이드  {PAGES_URL}lectures/{ID}/slide.html
         🧪 시뮬레이터 {PAGES_URL}lectures/{ID}/sim.html
         🔒 대본(비공개) {PAGES_URL}lectures/{ID}/script.html
       🌐 강의 목록 {PAGES_URL}
       ⏱  1~2분 후 GitHub Pages 반영
    ```

---

## 2️⃣ edit 흐름

clone/pull → 워크트리 → `lectures.json` 에서 id/slug 로 entry 찾기 → 현재 slide/sim/script 경로 표시 → 사용자에게 교체할 파일 받기 → **같은 id 로** 빌더 재실행(URL 보존) → 미리보기 → 승인 → push. 대본 교체 시 비밀번호 다시 입력받아 재암호화.

## 3️⃣ delete 흐름

clone/pull → 워크트리 → entry 매칭(정수=lecId 정확, 문자열=제목/slug 유사도 ≥0.5, 다건이면 AskUserQuestion) → 미리보기 출력 → 확인 → `lectures/{id}/` 폴더 + `lectures.json` entry 제거 → 미리보기로 사라짐 확인 → 승인 → commit(`delete: #{id} {title}`) → push. **lecId 재사용 금지.**

## 4️⃣ config / option

config 는 `~/.claude/hams-lec.json` 의 active 프로파일을 갱신하고 종료(배포 트리거 안 함). option 은 아래 양식을 출력만 한다.

```
🎓 /hams:lec — 강의 슬라이드·시뮬레이터·판서 대본 → GitHub Pages 강의 블로그

publish --no "1강" --title "..." [--slide f][--sim f][--script f][--summary ..][--section ..][--id N][--no-bar][--draft]
edit {id|slug}      delete {id|slug}      config <sub>      option

config: repo {url} · blog-title "..." · tagline "..." · script-mode {encrypt|local|off}
        profile add {name} {url} · profile use {name} · profile list · show

🔒 대본은 AES-GCM 암호화로 게시(scriptMode=encrypt). 비번 없이는 못 봄. local=push 안 함. off=대본 생략.
⚠  무료 GitHub Pages 는 공개가 기본 — 진짜 비공개가 필요하면 script-mode local 권장. 비번 분실 시 복구 불가.

설정: ~/.claude/hams-lec.json
```

---

## 사이트 구조 (배포 결과)

```
index.html                 # 강의 목록(섹션별 카드) — 공개
assets/style.css, app.js   # 다크 기본, 라이트 토글
lectures.json              # 회차 메타(목록 데이터)
lectures/{id}/slide.html   # panseo 슬라이드 (네비바만 주입) — 공개
lectures/{id}/sim.html     # 시뮬레이터 — 공개
lectures/{id}/script.html  # 암호화된 판서 대본 — 비공개(noindex)
.nojekyll                  # _ 폴더 무시 방지
robots.txt                 # script.html 검색 제외
```

`lectures.json` 스키마:
```json
{ "blogTitle":"", "sections":["1부 · ..."],
  "lectures":[
    { "lecId":1, "no":"1강", "title":"...", "slug":"attention",
      "summary":"...", "section":"1부 · ...", "date":"YYYY-MM-DD",
      "slide":"lectures/1/slide.html", "sim":"lectures/1/sim.html",
      "script":"lectures/1/script.html" } ] }
```

## 대본 암호화 방식 (참고)

- 빌더가 대본(.md→HTML 또는 .html)을 `encrypt_script.mjs`(Node webcrypto)로 **PBKDF2-SHA256(210k회)+AES-GCM-256** 암호화.
- 암호문/salt/iv 만 `script.html` 에 인라인으로 박히고, 비밀번호는 어디에도 저장되지 않는다.
- 페이지는 브라우저 SubtleCrypto 로 같은 방식 복호화 → 비번 맞을 때만 본문 렌더.
- Node 필요(`node --version`). 없으면 사용자에게 설치 안내 후, scriptMode=local 로 폴백 권장.

## panseo-slide / edu-sim-builder 연계

이 스킬은 **콘텐츠를 만들지 않는다** — 배포만 한다. 권장 흐름:
1. `panseo-slide` 로 슬라이드 + 판서 대본 생성.
2. `edu-sim-builder` 로 시뮬레이터 생성.
3. `/hams:lec publish` 로 셋을 한 회차로 묶어 배포.

## 에러 처리

| 케이스 | 처리 |
|------|-----|
| 설정 없음 | AskUserQuestion 으로 repo URL 받아 초기화 |
| slide/sim/script 모두 없음 | "최소 1개 자료가 필요합니다" 안내 후 종료 |
| Node 없음(대본 암호화) | 설치 안내 + scriptMode=local 폴백 권장 |
| 비밀번호 분실 | 복구 불가 — 대본 .md 원본으로 `edit` 재게시 안내 |
| 빈 레포 | 첫 배포는 BR 을 BASE 로 직접 push |
| 포트 점유 | `--preview-port` 로 변경 |
| 사용자 ❌ | 워크트리/브랜치 삭제, push 0회 |
