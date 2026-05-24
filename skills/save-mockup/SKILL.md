---
name: save-mockup
description: |
  현 세션의 HTML/이미지 등 mockup 을 active 프로젝트의 hamstern-data 에 보존.
  사용법:
    /hams:save-mockup "제목" [파일 경로] [--description "..."]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - AskUserQuestion
---

# /hams:save-mockup

cross-session 보존을 위해 mockup 파일 (HTML/PNG/JPG/SVG 등) 을 hamstern-data 의 active 프로젝트 `mockups/` 에 복사 + `_index.json` 갱신 + commit·push. 이후 GitHub Pages 의 per-project URL 로 어디서든 접근.

## 왜 별도 skill?

- 세션마다 임시로 만든 HTML/이미지 mockup 은 세션이 닫히면 컨텍스트에서 사라짐.
- 단순히 프로젝트 repo 에 커밋하면 다른 디바이스에서 잘 보이지 않고, 또 본 repo 와 무관한 디자인 산출물이 섞임.
- hamstern-data 에 모아두면 **모든 디바이스에서 동일 URL 로 접근** + 단일 dashboard 에서 한눈에 검토 가능.

## Claude 실행 절차

### Step 1: active-project + 인자 확인

```bash
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
if [ ! -f "$ACTIVE_CONFIG" ]; then
  echo "active project 없음. 먼저 /hams:link \"name\" 또는 /hams:init \"name\" 호출하세요." >&2
  exit 1
fi
ACTIVE_UUID=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['uuid'])")
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
PROJ_DIR="$HAMSTERN_DATA/projects/$ACTIVE_UUID"

[ ! -d "$PROJ_DIR" ] && {
  echo "active UUID $ACTIVE_UUID 디렉터리 없음. /hams:rebuild-index 또는 /hams:link 다시." >&2
  exit 1
}

TITLE="$1"
SRC_FILE="$2"   # 옵션 — 비우면 자동 탐지
DESCRIPTION=""  # --description 인자에서 채움

[ -z "$TITLE" ] && {
  echo "Usage: /hams:save-mockup \"title\" [file] [--description \"...\"]" >&2
  exit 1
}
```

`--description "..."` 는 argv 에서 분리 파싱. Claude 가 자연어로 받은 설명을 여기 채움.

### Step 2: 소스 파일 결정

`SRC_FILE` 가 비어 있으면 자동 탐지:

```bash
if [ -z "$SRC_FILE" ]; then
  CANDIDATES=$(find . -maxdepth 2 -type f \( \
      -name "*.html" -o -name "*.png" -o -name "*.jpg" \
      -o -name "*.jpeg" -o -name "*.svg" -o -name "*.gif" \
    \) -mtime -1 2>/dev/null | head -5)

  if [ -z "$CANDIDATES" ]; then
    echo "최근 mockup 후보 없음. 파일 경로를 직접 알려주세요." >&2
    # AskUserQuestion: "저장할 mockup 파일 경로?"
    exit 1
  fi
  # AskUserQuestion 으로 후보 중 선택 또는 직접 path 입력
  SRC_FILE="<사용자 선택>"
fi

[ ! -f "$SRC_FILE" ] && { echo "파일 없음: $SRC_FILE" >&2; exit 1; }

# 크기 확인 (10MB 경고)
SIZE=$(python3 -c "import os; print(os.path.getsize(r'$SRC_FILE'))")
if [ "$SIZE" -gt 10485760 ]; then
  echo "⚠️ 10MB 초과 ($((SIZE / 1024 / 1024)) MB) — git LFS 도입 검토 권장"
  # AskUserQuestion: "계속 진행?" yes/no — yes 가 아니면 exit 0
fi
```

### Step 3: slug + 목적지 경로 결정

```bash
EXT="${SRC_FILE##*.}"
SLUG=$(python3 -c "
import re
title = '''$TITLE'''
# 한글/영문/숫자/하이픈/언더스코어 보존, 나머지는 -
slug = re.sub(r'[^a-zA-Z0-9가-힣\\-_]+', '-', title).strip('-').lower()
print(slug or 'untitled')
")
DST="$PROJ_DIR/mockups/$SLUG.$EXT"

# 충돌 시 -1, -2 suffix
COUNTER=1
ORIG_DST="$DST"
while [ -f "$DST" ]; do
  DST="${ORIG_DST%.*}-$COUNTER.$EXT"
  COUNTER=$((COUNTER + 1))
done
FNAME=$(basename "$DST")
```

### Step 4: 복사 + mockups/_index.json 갱신

```bash
mkdir -p "$PROJ_DIR/mockups"
cp "$SRC_FILE" "$DST"

ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
MIME=$(python3 -c "
import mimetypes
print(mimetypes.guess_type(r'$DST')[0] or 'application/octet-stream')
")

# 현 세션의 sessions/*.md 파일명 추정 (record 가 마지막에 만든 파일)
CURRENT_SESSION_FILE=$(ls -t "$PROJ_DIR/sessions"/*.md 2>/dev/null | head -1 | xargs -I{} basename {} 2>/dev/null || echo "")

python3 -c "
import json, os
idx_file = r'$PROJ_DIR/mockups/_index.json'
if not os.path.exists(idx_file):
    json.dump({}, open(idx_file, 'w', encoding='utf-8'))
idx = json.load(open(idx_file))
idx['$FNAME'] = {
  'title': '''$TITLE''',
  'description': '''$DESCRIPTION''',
  'source_session': '$CURRENT_SESSION_FILE',
  'mime_type': '$MIME',
  'size_bytes': $SIZE,
  'created_at': '$ISO'
}
json.dump(idx, open(idx_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"
```

### Step 5: projects/_index.json 의 mockup_count + last_active 갱신

```bash
python3 -c "
import json
idx_file = r'$HAMSTERN_DATA/projects/_index.json'
idx = json.load(open(idx_file))
proj = idx.get('$ACTIVE_UUID', {})
proj['mockup_count'] = proj.get('mockup_count', 0) + 1
proj['last_active'] = '$ISO'
idx['$ACTIVE_UUID'] = proj
json.dump(idx, open(idx_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"
```

### Step 6: commit + push + 사용자 보고

```bash
cd "$HAMSTERN_DATA"
git add "projects/$ACTIVE_UUID/mockups/$FNAME" \
        "projects/$ACTIVE_UUID/mockups/_index.json" \
        "projects/_index.json"
git commit -m "save-mockup: $TITLE"
git push origin main 2>&1 || echo "⚠️ push failed (offline?). local commit 됨. 다음 호출 시 재시도." >&2
cd - > /dev/null

# SSH (`git@host:owner/repo.git`) 와 HTTPS (`https://host/owner/repo[.git]`) 양쪽 지원.
# 주의: `|` 가 alternation 으로 쓰이므로 sed delimiter 는 `#` 사용.
ORIGIN_URL=$(cd "$HAMSTERN_DATA" && git remote get-url origin)
OWNER=$(echo "$ORIGIN_URL" | sed -E 's#^(https?://[^/]+/|git@[^:]+:)([^/]+)/.*#\2#')
REPO=$(echo "$ORIGIN_URL" | sed -E -e 's#/$##' -e 's#\.git$##' -e 's#.*/##')
URL="https://$OWNER.github.io/$REPO/p/$ACTIVE_UUID/mockups/$FNAME"

echo "✅ 저장됨"
echo "   제목:   $TITLE"
echo "   파일:   $PROJ_DIR/mockups/$FNAME"
echo "   크기:   $SIZE bytes"
echo "   URL:    $URL"
echo ""
echo "다른 디바이스나 세션에서 /hams:remind --mockups 로 확인 가능."
```

## 다른 진입점과의 관계

- **`/hams:record`** — 세션 결정/대화는 sessions/*.md 로 보존. mockup 파일 자체는 save-mockup 이 담당.
- **`/hams:remind --mockups`** — 저장된 mockup 메타 + URL 출력.
- **`/hams:dashboard`** — per-project view 에서 mockups column 노출 (Sub-F Task 11).

## 실패 시나리오

| 실패 | 동작 |
|---|---|
| active-project.json 없음 | exit 1 + /hams:link 안내 |
| 소스 파일 없음 | exit 1 |
| 10MB 초과 | 경고 + 사용자 확인 |
| push 실패 (오프라인) | local commit 만 진행, 다음 호출 시 재시도 안내 |
| slug 충돌 | -1, -2, ... suffix 자동 |
