---
name: link
description: |
  hamstern-data 의 기존 프로젝트로 active 바인딩 (부분 이름 검색).
  사용법:
    /hams:link "프로젝트 이름 또는 부분"
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# /hams:link

기존 hamstern 프로젝트를 현 세션의 active 로 바인딩.

## Claude 실행 절차

### Step 1: 인자 + active-project.json 확인

```bash
QUERY="$1"
[ -z "$QUERY" ] && { echo "Usage: /hams:link \"name or partial\"" >&2; exit 1; }

ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
if [ ! -f "$ACTIVE_CONFIG" ]; then
  echo "active-project.json 없음. /hams:init 으로 프로젝트 먼저 생성하시거나, 기존 hamstern-data 경로를 알려주세요." >&2
  # AskUserQuestion: "hamstern-data 위치를 입력하세요 (기본: $HOME/.claude/hamstern-data)"
  HAMSTERN_DATA="<사용자 입력 또는 기본>"
else
  HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
fi
```

### Step 2: hamstern-data git pull (최신 상태로)

```bash
cd "$HAMSTERN_DATA"
git pull origin main 2>&1 || echo "⚠️ pull failed. 기존 로컬 상태로 진행." >&2
cd - > /dev/null
```

### Step 3: _index.json 에서 부분 일치 검색

```bash
INDEX_FILE="$HAMSTERN_DATA/projects/_index.json"
[ ! -f "$INDEX_FILE" ] && { echo "프로젝트 없음. /hams:init 으로 첫 프로젝트 생성." >&2; exit 1; }

MATCHES=$(python3 -c "
import json, sys
idx = json.load(open(r'$INDEX_FILE'))
q = '$QUERY'.lower()
hits = [(uuid, info) for uuid, info in idx.items() if q in info['name'].lower()]
for uuid, info in hits:
  print(f\"{uuid}\\t{info['name']}\\t{info['last_active']}\")
")
```

### Step 4: 매칭 결과 처리

```bash
COUNT=$(echo "$MATCHES" | grep -c .)

if [ "$COUNT" = "0" ]; then
  echo "'$QUERY' 매칭 프로젝트 없음."
  # AskUserQuestion: "/hams:init \"$QUERY\" 로 새로 생성?" yes/no
  exit 0
elif [ "$COUNT" = "1" ]; then
  UUID=$(echo "$MATCHES" | cut -f1)
  NAME=$(echo "$MATCHES" | cut -f2)
else
  # AskUserQuestion 으로 사용자 선택 (각 옵션: [name (last_active)])
  echo "$COUNT 개 후보:"
  echo "$MATCHES" | awk -F'\t' '{print "  - " $2 " (" $3 ", uuid=" substr($1,1,8) "...)" }'
  # 사용자가 선택 → UUID, NAME 결정
fi
```

### Step 5: active-project.json 갱신

```bash
ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
python3 -c "
import json
json.dump({
  'uuid': '$UUID',
  'name': '$NAME',
  'hamstern_data_path': r'$HAMSTERN_DATA',
  'linked_at': '$ISO'
}, open(r'$ACTIVE_CONFIG', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"

echo "✅ 바인딩: $NAME ($UUID)"
echo "   /hams:record 로 결정사항 기록 / /hams:remind 로 환기."
```
