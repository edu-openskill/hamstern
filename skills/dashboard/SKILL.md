---
name: dashboard
description: |
  사용자의 hamstern-data repo 의 multi-project dashboard 실행. 기본 = 로컬 serve. --publish 시 gh-pages 갱신.
  사용법:
    /hams:dashboard                # 로컬 background 서버 + 브라우저 오픈
    /hams:dashboard --publish      # hamstern-data 의 docs/ 갱신 + push → gh-pages
allowed-tools:
  - Read
  - Write
  - Bash
  - PowerShell
---

# /hams:dashboard

## 개요

사용자의 `hamstern-data` repo 를 정적 multi-project viewer 로 본다. 모든 프로젝트가 하나의 dashboard 에 모인다.

## 두 모드

| 모드 | 명령 | 데이터 | 자산 출처 | 외부 의존 |
|---|---|---|---|---|
| **local** (기본) | `/hams:dashboard` | `hamstern-data` 내용 → 임시 dir | plugin install 의 `docs/` | 0 |
| **publish** | `/hams:dashboard --publish` | `hamstern-data/docs/data/` | 같음 (plugin → hamstern-data/docs/) | git remote + Pages |

> **build.py vs SKILL.md 역할 분담**:
> - `build.py run_multiproject` 는 데이터 번들만 담당 (`hamstern-data/projects/*` → `out_dir/p/{uuid}/*`).
> - 정적 자산 복사 (`index.html`, `app.js`, `style.css`) 와 per-UUID `index.html` 생성 (`_project.html` 템플릿 복사) 은 이 SKILL.md 가 처리. build.py 는 plugin 의 `docs/` 위치를 모르기 때문.

## 동작 (Claude 가 실행)

> **Note**: 아래 모든 shell snippet 은 Bash 문법 (`[ -f`, `kill -0`, `head -1`, backgrounding 등). Windows 에서는 git-bash / WSL 또는 Claude 가 Bash tool 로 실행. raw PowerShell 직접 실행은 작동 안 함.

### 공통 — Plugin 경로 + hamstern-data 경로 탐지

```bash
# Plugin 경로
PLUGIN_DIR=$(python3 -c "from pathlib import Path; ps=sorted(Path.home().glob('.claude/plugins/cache/hamstern/hams/*/'), key=lambda p: p.stat().st_mtime, reverse=True); print(str(ps[0]) if ps else '', end='')")
if [ -z "$PLUGIN_DIR" ]; then echo "hamstern plugin not installed" >&2; exit 1; fi

# hamstern-data 경로 (active-project.json 에서)
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
if [ ! -f "$ACTIVE_CONFIG" ]; then
  echo "active project 없음. /hams:init 또는 /hams:link 먼저." >&2
  exit 1
fi
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
if [ ! -d "$HAMSTERN_DATA/.git" ]; then
  echo "hamstern_data_path 가 git repo 가 아닙니다: $HAMSTERN_DATA" >&2
  exit 1
fi
```

### Local 모드 (기본)

> Note: `serve.py --plugin-dir` 는 정적 자산 (index/app/style/p/{uuid}/index.html) 의 출처. Sub-F local 모드는 plugin 의 `docs/` 직접 사용 대신 임시 dir 에 자산 + 데이터를 합쳐 둠 (per-UUID `index.html` 생성을 위해).

1. **이전 인스턴스 정리**
   ```bash
   if [ -f "$HAMSTERN_DATA/.dashboard.pid" ]; then
     OLD_PID=$(cat "$HAMSTERN_DATA/.dashboard.pid")
     kill -0 "$OLD_PID" 2>/dev/null && kill "$OLD_PID"
     rm -f "$HAMSTERN_DATA/.dashboard.pid" "$HAMSTERN_DATA/.dashboard.url"
   fi
   ```

2. **임시 data 디렉터리에 multi-project 번들**
   ```bash
   TMP_DATA="$HAMSTERN_DATA/.tmp-dashboard-data"
   rm -rf "$TMP_DATA"
   python3 "$PLUGIN_DIR/skills/dashboard/build.py" \
     --hamstern-data "$HAMSTERN_DATA" \
     --out "$TMP_DATA"
   ```

3. **정적 자산 + per-UUID index.html 생성을 위한 임시 docs dir**
   ```bash
   TMP_DOCS="$HAMSTERN_DATA/.tmp-dashboard-docs"
   rm -rf "$TMP_DOCS"
   mkdir -p "$TMP_DOCS/p"
   cp "$PLUGIN_DIR/docs/index.html" "$TMP_DOCS/index.html"
   cp "$PLUGIN_DIR/docs/app.js" "$TMP_DOCS/app.js"
   cp "$PLUGIN_DIR/docs/style.css" "$TMP_DOCS/style.css"
   ```

4. **각 project UUID 마다 `_project.html` 을 그 디렉터리의 `index.html` 로 복사**
   ```bash
   python3 -c "
   import json, os, shutil
   from pathlib import Path
   manifest_file = Path(r'$TMP_DATA') / 'manifest.json'
   if manifest_file.exists():
       manifest = json.load(open(manifest_file))
       for uuid in manifest.get('projects', {}).keys():
           dst_dir = Path(r'$TMP_DOCS') / 'p' / uuid
           dst_dir.mkdir(parents=True, exist_ok=True)
           shutil.copy2(Path(r'$PLUGIN_DIR/docs/p/_project.html'), dst_dir / 'index.html')
   "
   ```

5. **data 도 TMP_DOCS 안으로 이동**
   ```bash
   mv "$TMP_DATA" "$TMP_DOCS/data"
   ```

6. **서버 background 기동**
   ```bash
   python3 "$PLUGIN_DIR/skills/dashboard/serve.py" \
     --plugin-dir "$TMP_DOCS" \
     --data-dir "$TMP_DOCS/data" \
     > "$HAMSTERN_DATA/.dashboard.url" 2>&1 &
   echo $! > "$HAMSTERN_DATA/.dashboard.pid"
   ```

7. **URL 대기 (최대 5초 폴링)**
   ```bash
   for i in 1 2 3 4 5; do
     if [ -s "$HAMSTERN_DATA/.dashboard.url" ]; then break; fi
     sleep 1
   done
   URL=$(head -1 "$HAMSTERN_DATA/.dashboard.url")
   if [ -z "$URL" ]; then
     echo "server did not emit URL within 5s" >&2
     cat "$HAMSTERN_DATA/.dashboard.url" >&2
     exit 1
   fi
   ```

8. **브라우저 오픈 (플랫폼별)**
   ```bash
   case "$(uname -s)" in
     MINGW*|MSYS*|CYGWIN*) start "$URL" ;;
     Darwin) open "$URL" ;;
     Linux)
       if command -v xdg-open >/dev/null; then xdg-open "$URL"
       else echo "no browser command found — open manually: $URL"
       fi ;;
     *) echo "platform unknown — open manually: $URL" ;;
   esac

   echo "dashboard live at $URL (pid=$(cat $HAMSTERN_DATA/.dashboard.pid))"
   ```

### Publish 모드 (`--publish`)

1. **data 번들 → hamstern-data/docs/data/**
   ```bash
   python3 "$PLUGIN_DIR/skills/dashboard/build.py" \
     --hamstern-data "$HAMSTERN_DATA" \
     --out "$HAMSTERN_DATA/docs/data"
   ```

2. **정적 자산 → hamstern-data/docs/**
   ```bash
   cp "$PLUGIN_DIR/docs/index.html" "$HAMSTERN_DATA/docs/index.html"
   cp "$PLUGIN_DIR/docs/app.js" "$HAMSTERN_DATA/docs/app.js"
   cp "$PLUGIN_DIR/docs/style.css" "$HAMSTERN_DATA/docs/style.css"
   ```

3. **per-UUID `index.html` 생성 (`_project.html` 템플릿 복사)**
   ```bash
   python3 -c "
   import json, os, shutil
   from pathlib import Path
   manifest_file = Path(r'$HAMSTERN_DATA/docs/data/manifest.json')
   if manifest_file.exists():
       manifest = json.load(open(manifest_file))
       for uuid in manifest.get('projects', {}).keys():
           dst_dir = Path(r'$HAMSTERN_DATA/docs/p') / uuid
           dst_dir.mkdir(parents=True, exist_ok=True)
           shutil.copy2(Path(r'$PLUGIN_DIR/docs/p/_project.html'), dst_dir / 'index.html')
   "
   ```

4. **commit + push**
   ```bash
   cd "$HAMSTERN_DATA"
   if [ -n "$(git status --short docs/)" ]; then
     git add docs/
     git commit -m "chore(dashboard): refresh $(date -u +%Y-%m-%dT%H:%M:%SZ)"
     git push origin main
   fi
   cd - > /dev/null
   ```

5. **URL 오픈** (git remote 에서 owner/repo 동적 추출)
   ```bash
   # SSH (`git@host:owner/repo.git`) 와 HTTPS (`https://host/owner/repo[.git]`) 양쪽 지원.
   # 주의: `|` 가 alternation 으로 쓰이므로 sed delimiter 는 `#` 사용.
   ORIGIN_URL=$(cd "$HAMSTERN_DATA" && git remote get-url origin)
   OWNER=$(echo "$ORIGIN_URL" | sed -E 's#^(https?://[^/]+/|git@[^:]+:)([^/]+)/.*#\2#')
   REPO=$(echo "$ORIGIN_URL" | sed -E -e 's#/$##' -e 's#\.git$##' -e 's#.*/##')
   URL="https://$OWNER.github.io/$REPO/"

   case "$(uname -s)" in
     MINGW*|MSYS*|CYGWIN*) start "$URL" ;;
     Darwin) open "$URL" ;;
     Linux)
       if command -v xdg-open >/dev/null; then xdg-open "$URL"
       else echo "no browser command found — open manually: $URL"
       fi ;;
     *) echo "platform unknown — open manually: $URL" ;;
   esac

   echo "dashboard published at $URL"
   ```

### 1회성 GitHub Pages 활성화 (publish 모드 전제)

repo (`hamstern-data`) 의 Settings → Pages → Source: `Deploy from a branch` → Branch: `main` → Folder: `/docs` → Save. ~1-2분 대기.

## 종료 (local 모드)

명시적 stop 명령 없음. 세 경로:
1. 다음 `/hams:dashboard` 호출 시 자동 kill·재시작
2. `kill $(cat $HAMSTERN_DATA/.dashboard.pid)`
3. 머신 종료

## 편집 흐름

dashboard 는 read-only. `[×]` 클릭 → 클립보드 `/hams:audit-decisions remove "<text>" --project-uuid <UUID>` → Claude 세션에 붙여넣어 실행 → remove.py 가 active-project.json 으로 hamstern-data 경로 자동 resolve.

## `.gitignore` 추천 (사용자의 `hamstern-data` repo 에서)

```
.tmp-dashboard-data/
.tmp-dashboard-docs/
.dashboard.pid
.dashboard.url
```

## 데이터 매핑

| 모드 | 소스 | 출력 |
|---|---|---|
| local | `$HAMSTERN_DATA/projects/{uuid}/decisions.md` | `$TMP_DOCS/data/p/{uuid}/decisions.md` |
| local | `$HAMSTERN_DATA/projects/{uuid}/sessions/*.md` | `$TMP_DOCS/data/p/{uuid}/sessions/*.md` |
| local | (plugin) `docs/p/_project.html` | `$TMP_DOCS/p/{uuid}/index.html` |
| publish | `$HAMSTERN_DATA/projects/{uuid}/decisions.md` | `$HAMSTERN_DATA/docs/data/p/{uuid}/decisions.md` |
| publish | (plugin) `docs/p/_project.html` | `$HAMSTERN_DATA/docs/p/{uuid}/index.html` |
