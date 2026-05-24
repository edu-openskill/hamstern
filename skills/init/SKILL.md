---
name: init
description: |
  새 hamstern 프로젝트 생성. UUID 부여 + hamstern-data/projects/{uuid}/ 디렉터리 scaffolding + active 바인딩.
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

### Step 2: hamstern-data 디렉터리 존재 확인 / clone

```bash
if [ ! -d "$HAMSTERN_DATA/.git" ]; then
  # 사용자에게 GitHub repo URL 받기
  # AskUserQuestion: "hamstern-data repo URL 을 알려주세요 (예: https://github.com/me/hamstern-data.git)"
  HAMSTERN_REPO_URL="<사용자 입력>"
  git clone "$HAMSTERN_REPO_URL" "$HAMSTERN_DATA" || {
    echo "clone 실패. repo 가 비어있다면 빈 디렉터리 + git init 으로 진행하시겠습니까?" >&2
    # AskUserQuestion: "빈 hamstern-data 로 시작" / "취소"
  }
fi
```

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
