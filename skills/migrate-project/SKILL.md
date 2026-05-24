---
name: migrate-project
description: |
  현 프로젝트의 .hamstern/ 디렉터리를 hamstern-data/projects/{uuid}/ 로 이전 (1회성).
  사용법:
    /hams:migrate-project [--delete-original]
allowed-tools:
  - Read
  - Write
  - Bash
  - AskUserQuestion
---

# /hams:migrate-project

기존 프로젝트 repo 의 `.hamstern/` 디렉터리를 사용자의 `hamstern-data` 로 이전.

본 skill 은 **1회성 도구**다. 한 프로젝트의 데이터가 hamstern-data 로 옮겨진 뒤에는 다시 호출되지 않는다. 이전이 끝난 프로젝트의 `.hamstern/` 는 기본적으로 보존되고 (`MIGRATED.md` 메모와 함께), `--delete-original` 옵션으로만 삭제된다.

## Claude 실행 절차

### Step 1: 현 프로젝트 .hamstern/ 확인

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT=$(pwd)
HAMS_DIR="$ROOT/.hamstern"
[ ! -d "$HAMS_DIR" ] && {
  echo "현 프로젝트에 .hamstern/ 가 없습니다. 이전할 것 없음." >&2
  exit 0
}
```

이미 `MIGRATED.md` 가 있는 경우는 이전이 이미 끝났다는 신호. 그 경우 사용자에게 다시 진행할지 AskUserQuestion 으로 확인.

### Step 2: 프로젝트 이름 추정 + 확정

```bash
# git remote 의 repo 이름 fallback
REPO_NAME=$(cd "$ROOT" && git remote get-url origin 2>/dev/null | sed -E 's|.*[:/]([^/]+)\.git$|\1|' | sed -E 's|.*[:/]([^/]+)$|\1|')
[ -z "$REPO_NAME" ] && REPO_NAME=$(basename "$ROOT")

# AskUserQuestion: "프로젝트 이름을 '$REPO_NAME' 로 할까요?" (사용자가 수정 가능)
NAME="<사용자 확정>"
```

### Step 3: /hams:init 호출 (UUID 생성 + scaffolding)

```bash
# init 호출 시 --repo 인자에 현 프로젝트의 remote URL 자동 추가
REPO_URL=$(cd "$ROOT" && git remote get-url origin 2>/dev/null)
# 이 절차는 SKILL.md 의 init 호출 흐름을 직접 inline 실행
# (Claude 가 init SKILL.md 의 step 들을 따라 UUID 부여 + meta.json + _index.json 갱신)
```

Claude 는 `/hams:init "$NAME" --repo "$REPO_URL"` 의 흐름을 inline 으로 수행한다 (init SKILL.md 의 Step 1~6). 이 단계가 끝나면 `ACTIVE_UUID`, `HAMSTERN_DATA`, `PROJ_DIR` 환경변수 셋업 + active-project.json 갱신 + 첫 commit·push 완료 상태가 된다.

### Step 4: 파일 복사

```bash
# init 이후 ACTIVE_UUID, HAMSTERN_DATA, PROJ_DIR 셋업됨
mkdir -p "$PROJ_DIR/sessions"

[ -f "$HAMS_DIR/decisions.md" ] && cp "$HAMS_DIR/decisions.md" "$PROJ_DIR/decisions.md"
[ -f "$HAMS_DIR/decisions-log.md" ] && cp "$HAMS_DIR/decisions-log.md" "$PROJ_DIR/decisions-log.md"
[ -d "$HAMS_DIR/sessions" ] && cp -r "$HAMS_DIR/sessions/"*.md "$PROJ_DIR/sessions/" 2>/dev/null
```

### Step 5: 원본 처리

`--delete-original` 플래그가 있으면 원본 삭제, 없으면 보존 + MIGRATED.md 메모 작성.

```bash
ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [ "$DELETE_ORIGINAL" = "1" ]; then
  # AskUserQuestion: "원본 .hamstern/ 를 삭제할까요? (되돌릴 수 없음)" yes/no
  rm -rf "$HAMS_DIR"
  echo "원본 .hamstern/ 삭제됨."
else
  # 기본: 보존 + MIGRATED.md 메모
  cat > "$HAMS_DIR/MIGRATED.md" <<EOF
# .hamstern/ — 마이그레이션됨

이 디렉터리의 내용은 $ISO 에 다음 위치로 이전되었습니다:

$HAMSTERN_DATA/projects/$ACTIVE_UUID/

UUID: $ACTIVE_UUID
Project name: $NAME

이전 데이터 자체는 그대로 보존됩니다. \`--delete-original\` 옵션으로 다시 호출하면 삭제 가능합니다.
EOF
  echo "원본 .hamstern/ 보존됨. MIGRATED.md 메모 생성."
fi
```

`MIGRATED.md` 는 향후 사용자가 `.hamstern/` 를 다시 보더라도 어디로 옮겨졌는지 즉시 확인 가능하게 함.

### Step 6: hamstern-data 에 commit + push

(init 단계에서 이미 commit·push 된 빈 scaffolding 위에) record 같은 commit:

```bash
cd "$HAMSTERN_DATA"
git add "projects/$ACTIVE_UUID/"
git commit -m "migrate: $NAME (from $REPO_NAME)"
git push origin main 2>&1 || echo "⚠️ push failed." >&2
cd - > /dev/null
```

### Step 7: _index.json 카운트 갱신 (decision/session count)

record 의 Step 5 와 같은 로직 — `decisions.md` 의 `- ` 줄 카운트, `sessions/*.md` 개수:

```bash
INDEX_FILE="$HAMSTERN_DATA/projects/_index.json"
python3 -c "
import json, os
idx = json.load(open(r'$INDEX_FILE'))
proj = idx.get('$ACTIVE_UUID', {})
dec_file = r'$PROJ_DIR/decisions.md'
dec_count = sum(1 for line in open(dec_file) if line.startswith('- ')) if os.path.exists(dec_file) else 0
sess_dir = r'$PROJ_DIR/sessions'
sess_count = len([f for f in os.listdir(sess_dir) if f.endswith('.md')]) if os.path.isdir(sess_dir) else 0
proj['decision_count'] = dec_count
proj['session_count'] = sess_count
proj['last_active'] = '$ISO'
idx['$ACTIVE_UUID'] = proj
json.dump(idx, open(r'$INDEX_FILE', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"

cd "$HAMSTERN_DATA"
git add projects/_index.json
git commit -m "migrate: $NAME 카운트 갱신" || true
git push origin main 2>&1 || echo "⚠️ push failed." >&2
cd - > /dev/null
```

### Step 8: 사용자 보고

```
✅ 마이그레이션 완료
   $REPO_NAME 의 .hamstern/  →  $HAMSTERN_DATA/projects/$ACTIVE_UUID/
   이름: $NAME / UUID: $ACTIVE_UUID
   결정 N개 / 세션 M개 이전됨.
   원본은 $([ "$DELETE_ORIGINAL" = "1" ] && echo "삭제됨" || echo "보존 + MIGRATED.md 메모 추가")
   현 세션은 새 프로젝트로 자동 바인딩됨.
```

## 다른 진입점과의 관계

- `/hams:init` 의 흐름을 inline 으로 재사용 (Step 3). 본 skill 만의 추가는 파일 복사 + 원본 처리.
- 본 skill 이 끝나면 active-project.json 이 새 UUID 로 바인딩된 상태. 이후 `/hams:record` / `/hams:remind` 가 자연스럽게 hamstern-data 경로로 동작.
- 1회성 도구 — 한 프로젝트당 한 번만 실행. `MIGRATED.md` 가 이미 존재하면 재실행 전 사용자 확인 필수.
