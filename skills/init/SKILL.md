---
name: init
description: |
  새 hamstern 프로젝트 생성. UUID 부여 + hamstern-data/projects/{uuid}/ 디렉터리 scaffolding + active 바인딩.
  GitHub remote 연결 필수 (cross-device sync 보장). 프로젝트 콘텐츠와 분리된 별도 위치 강제.
  사용법:
    /hams:init "프로젝트 이름" [--repo URL] [--description "..."]
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# /hams:init

새 hamstern 프로젝트를 생성하고 현재 세션을 그 프로젝트로 바인딩.

**필수 원칙 (2026-05-30 패치):**

1. **hamstern-data는 프로젝트 콘텐츠와 분리된 별도 위치**여야 한다. 기본 경로 `~/.claude/hamstern-data`. 프로젝트 작업물(CLAUDE.md, src/, package.json 등)이 있는 디렉토리를 hamstern-data로 지정하면 거부한다.
2. **GitHub remote 연결이 필수.** 로컬-only init은 차단된다. cross-device(다른 컴퓨터에서의 remind/link)가 불가능해지기 때문. URL은 `--repo` 인자 또는 AskUserQuestion으로 받고, 없으면 init 중단.

## Claude 실행 절차

### Step 1: 인자 파싱 + hamstern_data_path 확인

```bash
NAME="$1"
[ -z "$NAME" ] && { echo "Usage: /hams:init \"name\" [--repo URL] [--description \"...\"]" >&2; exit 1; }

ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
mkdir -p "$HOME/.config/hamstern"

# hamstern_data_path 결정
if [ -f "$ACTIVE_CONFIG" ]; then
  HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
else
  HAMSTERN_DATA="$HOME/.claude/hamstern-data"
fi
```

active-project.json 이 없으면 (= 첫 셋업) 기본 경로 `$HOME/.claude/hamstern-data` 제안. AskUserQuestion 으로 사용자 확정.

**경로 안전 검증 (필수):** 사용자가 지정한 HAMSTERN_DATA가 프로젝트 디렉토리와 섞이지 않도록 검증한다. 프로젝트 시그널 파일이 발견되고 hamstern-data 마커(`projects/` 디렉토리)가 없으면 거부.

```bash
# 프로젝트 디렉토리 신호 (있으면 별도 hamstern-data 위치 필요)
HAS_PROJECT_MARKER=0
for marker in "CLAUDE.md" "package.json" "pyproject.toml" "Cargo.toml" "go.mod" "src" "lib" "README.md"; do
  [ -e "$HAMSTERN_DATA/$marker" ] && HAS_PROJECT_MARKER=1 && break
done
HAS_HAMSTERN_MARKER=0
[ -d "$HAMSTERN_DATA/projects" ] && HAS_HAMSTERN_MARKER=1

if [ "$HAS_PROJECT_MARKER" = "1" ] && [ "$HAS_HAMSTERN_MARKER" = "0" ]; then
  echo "❌ '$HAMSTERN_DATA'는 프로젝트 디렉토리로 보입니다 (CLAUDE.md/src/README 등 발견)." >&2
  echo "hamstern-data는 metadata 전용 별도 위치여야 합니다." >&2
  echo "권장: $HOME/.claude/hamstern-data" >&2
  exit 1
fi
```

### Step 2: hamstern-data 디렉터리 + GitHub remote 연결 (필수)

```bash
# --repo 인자 우선
HAMSTERN_REPO_URL="${REPO_FROM_ARG:-}"

if [ ! -d "$HAMSTERN_DATA/.git" ]; then
  # GitHub repo URL 강제 (cross-device sync 보장)
  if [ -z "$HAMSTERN_REPO_URL" ]; then
    # AskUserQuestion: "hamstern-data GitHub repo URL? (없으면 먼저 github.com/new에서 빈 private repo 생성)"
    HAMSTERN_REPO_URL="<사용자 입력>"
  fi
  [ -z "$HAMSTERN_REPO_URL" ] && {
    echo "❌ GitHub repo URL이 필요합니다. 로컬-only는 지원 안 함 (cross-device 동기화 보장)." >&2
    exit 1
  }

  # clone 시도, 빈 repo면 init+remote 폴백
  if ! git clone "$HAMSTERN_REPO_URL" "$HAMSTERN_DATA" 2>/dev/null; then
    mkdir -p "$HAMSTERN_DATA"
    (cd "$HAMSTERN_DATA" && git init -b main && git remote add origin "$HAMSTERN_REPO_URL")
    echo "ℹ️ 빈 repo에 init + remote 연결됨"
  fi
elif ! (cd "$HAMSTERN_DATA" && git remote get-url origin > /dev/null 2>&1); then
  # .git은 있지만 remote 없음 — remote 추가 강제
  echo "⚠️ hamstern-data에 GitHub remote가 없습니다. cross-device 사용을 위해 추가합니다." >&2
  if [ -z "$HAMSTERN_REPO_URL" ]; then
    # AskUserQuestion: "GitHub repo URL?"
    HAMSTERN_REPO_URL="<사용자 입력>"
  fi
  [ -z "$HAMSTERN_REPO_URL" ] && {
    echo "❌ remote 없는 hamstern-data는 init 불가." >&2
    exit 1
  }
  (cd "$HAMSTERN_DATA" && git remote add origin "$HAMSTERN_REPO_URL")
fi
```

**로컬-only fallback 제거됨 (2026-05-30 패치).** URL 없으면 init 중단. 사용자가 cross-device로 옮길 일 절대 없다고 확신하더라도 예외 없음 — 미래의 자신이 후회한다.

### Step 3: UUID 생성

uuidv7 (time-ordered). Python stdlib `uuid.uuid7()` 는 3.13 부터. 그 미만이면 fallback:

```bash
UUID=$(python3 -c "
import time, secrets
try:
  from uuid import uuid7
  print(uuid7())
except ImportError:
  # uuidv7 manual: 48-bit ms timestamp + 12-bit rand + version 7 + variant + 62-bit rand
  ts_ms = int(time.time() * 1000)
  rand_a = secrets.randbits(12)
  rand_b = secrets.randbits(62)
  ts_hex = f'{ts_ms:012x}'
  ra_hex = f'{rand_a:03x}'
  rb_hex = f'{rand_b:016x}'
  print(f'{ts_hex[0:8]}-{ts_hex[8:12]}-7{ra_hex}-{(rand_b >> 60) | 0x8:01x}{rb_hex[1:4]}-{rb_hex[4:16]}')
")
```

### Step 4: projects/{uuid}/ 디렉터리 + 파일 생성

```bash
PROJ_DIR="$HAMSTERN_DATA/projects/$UUID"
mkdir -p "$PROJ_DIR/sessions" "$PROJ_DIR/mockups"

ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# meta.json
python3 -c "
import json, sys
meta = {
  'uuid': '$UUID',
  'name': '$NAME',
  'description': '',  # --description 인자에서 채움
  'repos': [],         # --repo 인자에서 채움
  'created_at': '$ISO',
  'last_active': '$ISO'
}
json.dump(meta, open(r'$PROJ_DIR/meta.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"

# 빈 decisions.md (Sub-C 포맷 헤더만)
cat > "$PROJ_DIR/decisions.md" <<EOF
# 프로젝트 결정사항

_마지막 업데이트: $ISO_

EOF

# 빈 mockups/_index.json
echo '{}' > "$PROJ_DIR/mockups/_index.json"

# projects/_index.json 갱신
INDEX_FILE="$HAMSTERN_DATA/projects/_index.json"
[ ! -f "$INDEX_FILE" ] && echo '{}' > "$INDEX_FILE"
python3 -c "
import json
idx = json.load(open(r'$INDEX_FILE'))
idx['$UUID'] = {
  'name': '$NAME',
  'last_active': '$ISO',
  'decision_count': 0,
  'session_count': 0,
  'mockup_count': 0
}
json.dump(idx, open(r'$INDEX_FILE', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"
```

### Step 5: active-project.json 갱신

```bash
python3 -c "
import json
json.dump({
  'uuid': '$UUID',
  'name': '$NAME',
  'hamstern_data_path': r'$HAMSTERN_DATA',
  'linked_at': '$ISO'
}, open(r'$ACTIVE_CONFIG', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"
```

### Step 6: git commit + push

```bash
cd "$HAMSTERN_DATA"
git add "projects/$UUID/" projects/_index.json
git commit -m "init: $NAME"
git push origin main 2>&1 || echo "⚠️ push failed. local commit 만 됐어요." >&2
```

### Step 7: 사용자 보고

```
✅ 프로젝트 생성됨
   이름: $NAME
   UUID: $UUID
   위치: $PROJ_DIR
   이 세션은 이 프로젝트로 바인딩됨.
   /hams:record 로 첫 결정사항 기록.
```
