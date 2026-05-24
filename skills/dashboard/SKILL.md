---
name: dashboard
description: hamstern dashboard 실행. 기본 = 로컬 serve (모든 프로젝트 즉시 동작). --publish 시 gh-pages 흐름 (Sub-D demo).
---

# /hams:dashboard

`.hamstern/*.md` 를 정적 viewer 로 본다. 두 모드:

| 모드 | 명령 | 데이터 | 자산 출처 | 외부 의존 |
|---|---|---|---|---|
| **local** (기본) | `/hams:dashboard` | `{project}/.hamstern/dashboard-data/` | plugin install 의 `docs/` | 0 |
| **publish** | `/hams:dashboard --publish` | `{project}/docs/data/` | 같음 (commit 됨) | git remote + GitHub Pages |

## 동작 (Claude 가 실행)

### 공통 — plugin 경로 탐지

```
PLUGIN_DIR=$(python3 -c "from pathlib import Path; ps=sorted(Path.home().glob('.claude/plugins/cache/hamstern/hams/*/'), key=lambda p: p.stat().st_mtime, reverse=True); print(str(ps[0]) if ps else '', end='')")
if [ -z "$PLUGIN_DIR" ]; then echo "hamstern plugin not installed under ~/.claude/plugins/cache/hamstern/" >&2; exit 1; fi
```

가장 최근 mtime 의 hamstern 설치 디렉터리 선택. 없으면 stderr + exit.

### Local 모드 (기본)

1. **이전 인스턴스 정리**
   ```
   if [ -f .hamstern/dashboard.pid ]; then
     OLD_PID=$(cat .hamstern/dashboard.pid)
     kill -0 "$OLD_PID" 2>/dev/null && kill "$OLD_PID"
     rm -f .hamstern/dashboard.pid .hamstern/dashboard.url
   fi
   ```

2. **데이터 번들**
   ```
   python3 "$PLUGIN_DIR/skills/dashboard/build.py" --project . --out .hamstern/dashboard-data
   ```
   exit 1 시 중단.

3. **서버 background 기동**
   ```
   python3 "$PLUGIN_DIR/skills/dashboard/serve.py" \
     --plugin-dir "$PLUGIN_DIR/docs" \
     --data-dir .hamstern/dashboard-data \
     > .hamstern/dashboard.url 2>&1 &
   echo $! > .hamstern/dashboard.pid
   ```

4. **URL 대기 (최대 5초 폴링)**
   ```
   for i in 1 2 3 4 5; do
     if [ -s .hamstern/dashboard.url ]; then break; fi
     sleep 1
   done
   URL=$(head -1 .hamstern/dashboard.url)
   if [ -z "$URL" ]; then
     echo "server did not emit URL within 5s; output:" >&2
     cat .hamstern/dashboard.url >&2
     exit 1
   fi
   ```

5. **브라우저 오픈 (플랫폼별)**
   - Windows: `start "$URL"`
   - macOS: `open "$URL"`
   - Linux: `xdg-open "$URL"`

6. **사용자에게 보고**
   ```
   echo "dashboard live at $URL (pid=$(cat .hamstern/dashboard.pid))"
   ```

### Publish 모드 (--publish, Sub-D 흐름)

1. **데이터 번들**
   ```
   python3 "$PLUGIN_DIR/skills/dashboard/build.py" --project . --out docs/data
   ```

2. **변경 감지 + commit + push**
   ```
   if [ -n "$(git status --short docs/data/)" ]; then
     git add docs/data/
     git commit -m "chore(dashboard): refresh data $(date -u +%Y-%m-%dT%H:%M:%SZ)"
     git push origin main
   fi
   ```

3. **gh-pages URL 오픈**
   git remote 에서 owner/repo 추출 → `https://<owner>.github.io/<repo>/`. Windows: `start ...`.

### 1회성 GitHub Pages 활성화 (publish 모드 전제)

repo 의 Settings → Pages → Source: `Deploy from a branch` → Branch: `main` → Folder: `/docs` → Save. ~1-2분 대기.

## 종료 (local 모드)

명시적 stop 명령 없음. 세 경로:
1. 다음 `/hams:dashboard` 호출 시 자동 kill·재시작
2. `kill $(cat .hamstern/dashboard.pid)`
3. 머신 종료

좀비 누적 우려 시 미래에 `/hams:dashboard-stop` 추가 검토.

## 사용자 프로젝트 `.gitignore` 추천

publish 모드 안 쓰는 프로젝트:
```
.hamstern/dashboard-data/
.hamstern/dashboard.pid
.hamstern/dashboard.url
```

## 편집 흐름

dashboard 는 read-only. `[×]` 클릭 → 클립보드 `/hams:audit-decisions remove "<text>"` → Claude 세션에 붙여넣어 실행 → 다음 `/hams:dashboard` 호출 시 viewer 반영.

## 데이터 매핑

| 모드 | 소스 | 출력 |
|---|---|---|
| local | `.hamstern/decisions.md` | `.hamstern/dashboard-data/decisions.md` |
| local | `.hamstern/decisions-log.md` | `.hamstern/dashboard-data/decisions-log.md` |
| local | `.hamstern/sessions/*.md` | `.hamstern/dashboard-data/sessions/<name>.md` |
| publish | `.hamstern/decisions.md` | `docs/data/decisions.md` |
| publish | `.hamstern/sessions/*.md` | `docs/data/sessions/<name>.md` |
