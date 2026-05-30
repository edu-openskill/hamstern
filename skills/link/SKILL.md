---
name: link
description: |
  hamstern-data 의 기존 프로젝트로 active 바인딩 (부분 이름 검색).
  --repo URL 로 다른 컴퓨터에서 첫 사용 시 자동 clone 가능.
  query 생략 시 전체 프로젝트 목록 보여주고 선택.
  사용법:
    /hams:link "프로젝트 이름 또는 부분"
    /hams:link --repo https://github.com/me/hamstern-data.git           # 새 컴퓨터 첫 사용 (전체 목록 보여줌)
    /hams:link --repo https://github.com/me/hamstern-data.git "이름"   # 새 컴퓨터 + 이름 매칭
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# /hams:link

기존 hamstern 프로젝트를 현 세션의 active 로 바인딩.

**진입 시나리오:**
- **A. 같은 컴퓨터에서 다른 프로젝트로 전환**: `/hams:link "name"` — 기존 hamstern-data에서 부분 매칭
- **B. 새 컴퓨터에서 첫 사용**: `/hams:link --repo URL` — hamstern-data를 clone 후 전체 프로젝트 목록 보여주고 선택 (또는 `--repo URL "name"`으로 직접 매칭)
- **C. query 생략**: 현재 hamstern-data의 모든 프로젝트 목록 보여주고 선택

## Claude 실행 절차

### Step 1: 인자 파싱 (--repo URL 우선 처리)

```bash
REPO_URL=""
QUERY=""

# 인자 파싱
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO_URL="$2"; shift 2 ;;
    *) [ -z "$QUERY" ] && QUERY="$1"; shift ;;
  esac
done

ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
mkdir -p "$HOME/.config/hamstern"

# --repo 지정 시: 새 컴퓨터 첫 사용 시나리오
if [ -n "$REPO_URL" ]; then
  # hamstern-data 경로 결정 (active-project.json 있으면 그 경로, 없으면 기본)
  if [ -f "$ACTIVE_CONFIG" ]; then
    HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
  else
    HAMSTERN_DATA="$HOME/.claude/hamstern-data"
  fi
  # clone 또는 pull
  if [ ! -d "$HAMSTERN_DATA/.git" ]; then
    git clone "$REPO_URL" "$HAMSTERN_DATA" || { echo "❌ clone 실패: $REPO_URL" >&2; exit 1; }
    echo "✅ cloned $REPO_URL → $HAMSTERN_DATA"
  else
    (cd "$HAMSTERN_DATA" && git pull origin main 2>&1 | tail -2 || echo "⚠️ pull failed.")
  fi
elif [ -f "$ACTIVE_CONFIG" ]; then
  HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
else
  echo "❌ active-project.json 없음 + --repo 없음." >&2
  echo "   첫 사용이면: /hams:init \"name\" 으로 프로젝트 생성" >&2
  echo "   새 컴퓨터면: /hams:link --repo <GitHub URL>" >&2
  exit 1
fi
```

### Step 2: hamstern-data git pull (최신 상태로 — --repo 경로 아닌 경우만)

`--repo`로 들어온 경우 Step 1에서 이미 clone/pull 했으므로 스킵.

```bash
# --repo 미지정 (기존 active-project 사용)일 때만 pull
if [ -z "$REPO_URL" ]; then
  cd "$HAMSTERN_DATA"
  git pull origin main 2>&1 | tail -2 || echo "⚠️ pull failed. 기존 로컬 상태로 진행." >&2
  cd - > /dev/null
fi
```

### Step 3: _index.json 에서 부분 일치 검색 (QUERY 비면 전체 반환)

```bash
INDEX_FILE="$HAMSTERN_DATA/projects/_index.json"
[ ! -f "$INDEX_FILE" ] && { echo "프로젝트 없음. /hams:init 으로 첫 프로젝트 생성." >&2; exit 1; }

MATCHES=$(python3 -c "
import json, sys
idx = json.load(open(r'$INDEX_FILE'))
q = '$QUERY'.lower()
# QUERY가 비면 전체, 있으면 부분 매칭
hits = [(uuid, info) for uuid, info in idx.items() if (not q or q in info['name'].lower())]
# last_active 내림차순 (최근 작업한 게 위로)
hits.sort(key=lambda x: x[1].get('last_active', ''), reverse=True)
for uuid, info in hits:
  print(f\"{uuid}\\t{info['name']}\\t{info['last_active']}\")
")
```

### Step 4: 매칭 결과 처리

```bash
COUNT=$(echo "$MATCHES" | grep -c .)

if [ "$COUNT" = "0" ]; then
  if [ -z "$QUERY" ]; then
    echo "hamstern-data에 프로젝트가 없습니다. /hams:init 으로 첫 프로젝트를 생성하세요." >&2
  else
    echo "'$QUERY' 매칭 프로젝트 없음."
    # AskUserQuestion: "/hams:init \"$QUERY\" 로 새로 생성?" yes/no
  fi
  exit 0
elif [ "$COUNT" = "1" ] && [ -n "$QUERY" ]; then
  # 단일 매칭 + 명시적 query → 자동 선택
  UUID=$(echo "$MATCHES" | cut -f1)
  NAME=$(echo "$MATCHES" | cut -f2)
else
  # 다중 매칭 또는 QUERY 비어있음 → AskUserQuestion으로 선택
  # 각 옵션: "이름 (last_active, uuid=xxxx...)"
  echo "$COUNT 개 프로젝트 — 선택:"
  echo "$MATCHES" | awk -F'\t' '{print "  - " $2 " (" $3 ", uuid=" substr($1,1,8) "...)" }'
  # 사용자가 선택 → UUID, NAME 결정 (AskUserQuestion으로)
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
