# Sub-project F — hamstern-data Repo + UUID per Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** hamstern 의 데이터를 사용자의 개별 personal `hamstern-data` GitHub repo 로 옮겨, `projects/{uuid}/` 디렉터리 격리 + cross-device sync + 단일 multi-project dashboard 구현.

**Architecture:** git-as-DB 패턴. 단일 personal repo (`hamstern-data`) 안에 `projects/{uuid}/{decisions.md, decisions-log.md, sessions/*.md, mockups/*}` 격리. 각 디바이스는 `~/.config/hamstern/active-project.json` 에 현재 active UUID 캐시. Sub-D/E 의 `build.py` + `serve.py` + 정적 자산 (`docs/*`) 재사용, multi-project 라우팅으로 확장.

**Tech Stack:** Python 3 (stdlib only — pathlib, json, uuid, subprocess), bash + jq, Sub-D/E 의 정적 viewer 자산. pytest.

**Reference Spec:** `docs/discussions/2026-05-24-sub-f-hamstern-data-repo-design.md` (commit `fb02454`)

---

## 파일 구조 결정

### 신규 skill 디렉터리

| 경로 | 책임 |
|---|---|
| `skills/init/SKILL.md` | UUID 생성 + projects/{uuid}/ scaffolding + active-project 바인딩 |
| `skills/link/SKILL.md` | _index.json 부분 일치 검색 + active-project 갱신 |
| `skills/save-mockup/SKILL.md` | 파일 복사 + mockups/_index.json 갱신 + commit·push |
| `skills/migrate-project/SKILL.md` | 기존 .hamstern/ → hamstern-data/projects/{uuid}/ 이전 (1회성) |
| `skills/rebuild-index/SKILL.md` | _index.json 디렉터리 스캔 재생성 (복구용) |

### 수정 대상

| 경로 | 변경 |
|---|---|
| `skills/record/SKILL.md` | active-project 확인 + hamstern-data 경로로 출력 + commit·push |
| `skills/remind/SKILL.md` | hamstern-data 의 active project 디렉터리 읽기 + N=2 sessions + 8KB cap |
| `skills/dashboard/SKILL.md` | multi-project 메인 페이지 + per-project 라우팅 |
| `skills/dashboard/build.py` | multi-project 번들 (projects/* 순회), mockup 메타 포함 |
| `skills/dashboard/test_build.py` | multi-project 케이스 추가 |
| `skills/dashboard/serve.py` | `/data/p/{uuid}/...` path 분기 |
| `skills/dashboard/test_serve.py` | multi-project 라우팅 케이스 추가 |
| `skills/audit-decisions/remove.py` | `--data-root` 인자 추가 |
| `skills/audit-decisions/test_remove.py` | data-root 인자 케이스 추가 |
| `skills/audit-decisions/SKILL.md` | hamstern-data 경로 사용 |
| `docs/index.html` | 메인 페이지 (프로젝트 목록 + 검색) 신규 |
| `docs/app.js` | mockups column + project 라우팅 추가 |
| `docs/style.css` | mockups column 스타일 |
| `.claude-plugin/marketplace.json` | 5 신규 skill 등록 |
| `README.md` | hamstern-data 셋업 가이드 + Sub-F changelog |
| `docs/conventions.md` | git-as-DB 모델 + projects/{uuid}/ 규약 |

### 신규 데이터 / 설정 파일

| 경로 | 역할 |
|---|---|
| `~/.config/hamstern/active-project.json` | 디바이스별 {uuid, name, hamstern_data_path, linked_at} |
| `hamstern-data/projects/_index.json` | 전체 프로젝트 인덱스 |
| `hamstern-data/projects/{uuid}/meta.json` | 프로젝트 메타 |
| `hamstern-data/projects/{uuid}/mockups/_index.json` | 프로젝트별 mockup 메타 |

### 신규 verification 산출물

| 경로 | 작성 시점 |
|---|---|
| `docs/plans/2026-05-24-sub-f-hamstern-data-repo-verification.md` | 마지막 task |

---

## Task 1: 사전 점검 + active-project.json 스키마 결정

**Files:** (코드 변경 없음 — 셋업 검증)

- [ ] **Step 1: HEAD + 작업 트리 상태 확인**

Run:
```
cd hamstern-plugin
git log --oneline -3
git status --short
```

Expected: HEAD = `fb02454 docs(spec): Sub-project F ...`. 작업 트리에 unrelated dirty state 있을 수 있음 (skills/why/SKILL.md, .claude/worktrees/, 두 record-handoff-redesign 파일) — 건드리지 말 것.

- [ ] **Step 2: active-project.json 스키마 표준 결정**

`~/.config/hamstern/active-project.json` 스키마:
```json
{
  "uuid": "01HXY4P8Z6QK4R5T8V9W0X1Y2Z",
  "name": "포트폴리오 V2",
  "hamstern_data_path": "/c/Users/me/.claude/hamstern-data",
  "linked_at": "2026-05-24T10:30:00Z"
}
```

`hamstern_data_path` 는 사용자 머신의 hamstern-data clone 위치 (절대 경로). 첫 셋업에서 결정.

- [ ] **Step 3: bash helper snippet 결정** (각 SKILL.md 에서 재사용)

다음 두 helper 를 모든 신규 skill 의 SKILL.md 에 표준 사용:

```bash
# helper-1: active-project 읽기 (없으면 exit 1)
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
if [ ! -f "$ACTIVE_CONFIG" ]; then
  echo "no active project. run /hams:link \"name\" or /hams:init \"name\" first." >&2
  exit 1
fi
ACTIVE_UUID=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['uuid'])")
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
PROJ_DIR="$HAMSTERN_DATA/projects/$ACTIVE_UUID"

# helper-2: hamstern-data git push (네트워크 실패 시 경고)
push_or_warn() {
  cd "$HAMSTERN_DATA"
  git push origin main 2>&1 || echo "⚠️ push failed (offline?). local commit 만 됐어요. 다음 호출 시 재시도." >&2
  cd - > /dev/null
}
```

본 task 는 plan 문서에 표준 helper 를 박는 것이 목적. 실제 채용은 Task 2 부터 SKILL.md 작성 시.

- [ ] **Step 4: commit 없음** — 코드 변경 없음.

---

## Task 2: `/hams:init` skill — 기본 골격 + 첫 commit 흐름

**Files:**
- Create: `skills/init/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

```markdown
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
```

- [ ] **Step 2: 파일 확인**

```
cat skills/init/SKILL.md | wc -l
grep -n "UUID" skills/init/SKILL.md | head -5
```

대략 100줄 안팎.

- [ ] **Step 3: commit**

```
git add skills/init/SKILL.md
git commit -m "feat(init): /hams:init skill for new project scaffolding (Sub-F)"
```

---

## Task 3: `/hams:link` skill

**Files:**
- Create: `skills/link/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

```markdown
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
```

- [ ] **Step 2: commit**

```
git add skills/link/SKILL.md
git commit -m "feat(link): /hams:link skill for binding existing project (Sub-F)"
```

---

## Task 4: `/hams:record` SKILL.md 갱신 — hamstern-data 경로로 출력 + _index.json 갱신

**Files:**
- Modify: `skills/record/SKILL.md`

- [ ] **Step 1: 현 SKILL.md 의 Step 1 (경로 해석) 을 교체**

기존 (Sub-C):
```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT=$(pwd)
mkdir -p "$ROOT/.hamstern/sessions"
```

신규 (Sub-F):
```bash
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
[ ! -f "$ACTIVE_CONFIG" ] && {
  echo "active project 없음. 먼저 /hams:link \"name\" 또는 /hams:init \"name\" 호출하세요." >&2
  exit 1
}
ACTIVE_UUID=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['uuid'])")
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
PROJ_DIR="$HAMSTERN_DATA/projects/$ACTIVE_UUID"

[ ! -d "$PROJ_DIR" ] && {
  echo "active UUID $ACTIVE_UUID 의 디렉터리가 없습니다. /hams:rebuild-index 또는 /hams:link 다시." >&2
  exit 1
}
mkdir -p "$PROJ_DIR/sessions"
```

- [ ] **Step 2: 자동 마이그레이션 섹션 — 비범위로 표시**

기존 자동 마이그레이션 (baby/mom/boss → 평탄) 섹션은 그대로 유지하되 다음 문장 추가:

> **Sub-F 이후**: 이 자동 마이그레이션은 *프로젝트 repo 내 .hamstern/* 의 옛 구조 한정. 이미 hamstern-data 로 이전된 사용자는 트리거 안 됨. 옛 `.hamstern/` 가 있는 프로젝트는 `/hams:migrate-project` 로 hamstern-data 로 이전.

- [ ] **Step 3: Step 4 (atomic dual-write) 의 경로 갱신**

기존:
```
{r}/.hamstern/sessions/{id}.md
{r}/.hamstern/decisions.md
{r}/.hamstern/decisions-log.md
```

신규:
```
$PROJ_DIR/sessions/{id}.md
$PROJ_DIR/decisions.md
$PROJ_DIR/decisions-log.md
```

(SKILL.md 안의 모든 path 참조 일괄 갱신)

- [ ] **Step 4: 새 Step 5 추가 — _index.json 갱신**

쓰기 완료 후:
```bash
INDEX_FILE="$HAMSTERN_DATA/projects/_index.json"
python3 -c "
import json
idx = json.load(open(r'$INDEX_FILE'))
proj = idx.get('$ACTIVE_UUID', {})
# decision_count = decisions.md 의 '- ' 줄 개수
dec_count = sum(1 for line in open(r'$PROJ_DIR/decisions.md') if line.startswith('- '))
# session_count = sessions/*.md 파일 개수
import os
sess_count = len([f for f in os.listdir(r'$PROJ_DIR/sessions') if f.endswith('.md')]) if os.path.isdir(r'$PROJ_DIR/sessions') else 0
proj['decision_count'] = dec_count
proj['session_count'] = sess_count
proj['last_active'] = '$ISO'
idx['$ACTIVE_UUID'] = proj
json.dump(idx, open(r'$INDEX_FILE', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"
```

- [ ] **Step 5: 새 Step 6 추가 — hamstern-data git commit + push**

```bash
cd "$HAMSTERN_DATA"
git add "projects/$ACTIVE_UUID/" projects/_index.json
git commit -m "record: $NAME 세션 ${ISO}"
git push origin main 2>&1 || echo "⚠️ push failed (offline?). local commit 됨." >&2
cd - > /dev/null
```

- [ ] **Step 6: 기존 Step 5 (텍스트 폴백) 의 path 도 갱신**

폴백 출력 안내 메시지에서 `{project_root}/.hamstern/` → `hamstern-data/projects/$ACTIVE_UUID/` 로 변경.

- [ ] **Step 7: SKILL.md 끝의 "다른 진입점과의 관계" 섹션 갱신**

다음 추가:
```
- Sub-F 이후 record 의 출력은 사용자의 personal hamstern-data repo. 프로젝트 자체 repo 는 건드리지 않음.
- /hams:init / /hams:link 가 record 의 active project 를 결정.
```

- [ ] **Step 8: 확인 grep**

```
grep -c "ACTIVE_UUID" skills/record/SKILL.md   # 5+ (여러 곳에서 사용)
grep -c "PROJ_DIR" skills/record/SKILL.md      # 8+
grep -c ".hamstern/sessions" skills/record/SKILL.md   # 1 — 옛 구조 마이그레이션 섹션만
grep -c "HAMSTERN_DATA" skills/record/SKILL.md  # 3+
```

- [ ] **Step 9: commit**

```
git add skills/record/SKILL.md
git commit -m "feat(record): hamstern-data 경로로 출력 + _index.json 갱신 (Sub-F)"
```

---

## Task 5: `/hams:remind` SKILL.md 갱신 — hamstern-data 읽기 + N=2 sessions + 8KB cap

**Files:**
- Modify: `skills/remind/SKILL.md`

- [ ] **Step 1: SKILL.md 의 "실행" 섹션 교체**

기존:
```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT=$(pwd)
path="$ROOT/.hamstern/decisions.md"
cat "$path"
```

신규:
```bash
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
[ ! -f "$ACTIVE_CONFIG" ] && {
  echo "active project 없음. /hams:link \"name\" 호출 후 다시." >&2
  exit 1
}
ACTIVE_UUID=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['uuid'])")
ACTIVE_NAME=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['name'])")
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
PROJ_DIR="$HAMSTERN_DATA/projects/$ACTIVE_UUID"

# 인자 파싱
DEEP=0
INCLUDE_MOCKUPS=0
for arg in "$@"; do
  case "$arg" in
    --deep) DEEP=1 ;;
    --mockups) INCLUDE_MOCKUPS=1 ;;
  esac
done
SESSION_N=$([ "$DEEP" = "1" ] && echo 5 || echo 2)

# 자동 pull (선택적; --no-pull 옵션은 v2)
cd "$HAMSTERN_DATA"
git pull origin main 2>&1 | tail -2 || true
cd - > /dev/null

# 1) decisions.md 전체 출력
echo "## 결정사항 (프로젝트: $ACTIVE_NAME)"
cat "$PROJ_DIR/decisions.md"

# 2) 최근 N sessions 출력 (8KB cap)
echo ""
echo "## 최근 세션 (N=$SESSION_N)"
python3 -c "
import os, glob
files = sorted(glob.glob(r'$PROJ_DIR/sessions/*.md'), key=os.path.getmtime, reverse=True)[:$SESSION_N]
total = 0
CAP = 8 * 1024
for f in files:
    content = open(f, encoding='utf-8').read()
    if total + len(content.encode('utf-8')) > CAP:
        remaining = CAP - total
        if remaining > 200:
            print('### ' + os.path.basename(f) + ' (truncated)')
            print(content[:remaining])
            print('... (truncated to 8KB total budget)')
        break
    print('### ' + os.path.basename(f))
    print(content)
    print()
    total += len(content.encode('utf-8'))
"

# 3) mockups (옵션)
if [ "$INCLUDE_MOCKUPS" = "1" ]; then
  echo ""
  echo "## 최근 mockups"
  python3 -c "
import json, os
idx_file = r'$PROJ_DIR/mockups/_index.json'
if os.path.exists(idx_file):
    idx = json.load(open(idx_file))
    items = sorted(idx.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)[:5]
    for fname, info in items:
        url = f\"https://<owner>.github.io/hamstern-data/p/$ACTIVE_UUID/mockups/{fname}\"
        print(f\"- [{info['title']}]({url}) — {info.get('description', '')}\")
"
fi

echo ""
echo "> _$ACTIVE_NAME 컨텍스트 환기 완료. (decisions 전체 + sessions $SESSION_N개${INCLUDE_MOCKUPS:+ + mockups})_"
```

- [ ] **Step 2: SKILL.md 의 "왜 자동 주입이 아닌가" + "두 세션 워크플로우" 섹션 갱신**

옛 단일 프로젝트 모델 (`.hamstern/decisions.md`) 언급을 hamstern-data + active project 로 갱신.

- [ ] **Step 3: 확인 grep**

```
grep -c "ACTIVE_UUID" skills/remind/SKILL.md          # 3+
grep -c "PROJ_DIR" skills/remind/SKILL.md             # 5+
grep -c "8 \* 1024" skills/remind/SKILL.md            # 1 (cap)
grep -c "git rev-parse" skills/remind/SKILL.md         # 0 (옛 흐름 제거)
grep -c "git pull" skills/remind/SKILL.md              # 1 (자동 pull)
```

- [ ] **Step 4: commit**

```
git add skills/remind/SKILL.md
git commit -m "feat(remind): hamstern-data 읽기 + N=2 sessions + 8KB cap + --deep/--mockups (Sub-F)"
```

---

## Task 6: `/hams:save-mockup` skill 신규

**Files:**
- Create: `skills/save-mockup/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

```markdown
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

cross-session 보존을 위해 mockup 파일을 hamstern-data 의 active 프로젝트에 저장.

## Claude 실행 절차

### Step 1: active-project + 인자 확인

(Task 1 의 standard helper-1 사용)

```bash
TITLE="$1"
SRC_FILE="$2"  # 옵션
[ -z "$TITLE" ] && { echo "Usage: /hams:save-mockup \"title\" [file]" >&2; exit 1; }
```

### Step 2: 소스 파일 결정

```bash
if [ -z "$SRC_FILE" ]; then
  # 자동 탐지: 현 디렉터리의 최근 HTML/이미지 후보
  CANDIDATES=$(find . -maxdepth 2 -type f \( -name "*.html" -o -name "*.png" -o -name "*.jpg" -o -name "*.svg" \) -mtime -1 2>/dev/null | head -5)
  # AskUserQuestion: "어느 파일을 저장할까요?" 또는 사용자가 직접 path 입력
  SRC_FILE="<사용자 선택>"
fi

[ ! -f "$SRC_FILE" ] && { echo "파일 없음: $SRC_FILE" >&2; exit 1; }

# 크기 확인 (10MB 경고)
SIZE=$(python3 -c "import os; print(os.path.getsize(r'$SRC_FILE'))")
if [ "$SIZE" -gt 10485760 ]; then
  echo "⚠️ 10MB 초과 — git LFS 도입 검토 권장"
  # AskUserQuestion: "계속 진행?" yes/no
fi
```

### Step 3: slug + 목적지 경로 결정

```bash
EXT="${SRC_FILE##*.}"
SLUG=$(python3 -c "
import re
title = '''$TITLE'''
slug = re.sub(r'[^a-zA-Z0-9가-힣\\-_]+', '-', title).strip('-').lower()
print(slug)
")
DST="$PROJ_DIR/mockups/$SLUG.$EXT"

# 충돌 시 -1, -2 등 suffix
COUNTER=1
ORIG_DST="$DST"
while [ -f "$DST" ]; do
  DST="${ORIG_DST%.*}-$COUNTER.$EXT"
  COUNTER=$((COUNTER + 1))
done
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
FNAME=$(basename "$DST")

python3 -c "
import json, os
idx_file = r'$PROJ_DIR/mockups/_index.json'
if not os.path.exists(idx_file):
    json.dump({}, open(idx_file, 'w', encoding='utf-8'))
idx = json.load(open(idx_file))
idx['$FNAME'] = {
  'title': '''$TITLE''',
  'description': '''$DESCRIPTION''',
  'source_session': '$CURRENT_SESSION_FILE',  # 현 세션의 sessions/*.md 파일명 추정
  'mime_type': '$MIME',
  'size_bytes': $SIZE,
  'created_at': '$ISO'
}
json.dump(idx, open(idx_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"
```

### Step 5: _index.json 의 mockup_count 증가

```bash
python3 -c "
import json
idx = json.load(open(r'$HAMSTERN_DATA/projects/_index.json'))
idx['$ACTIVE_UUID']['mockup_count'] = idx['$ACTIVE_UUID'].get('mockup_count', 0) + 1
idx['$ACTIVE_UUID']['last_active'] = '$ISO'
json.dump(idx, open(r'$HAMSTERN_DATA/projects/_index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"
```

### Step 6: commit + push + 사용자 보고

```bash
cd "$HAMSTERN_DATA"
git add "projects/$ACTIVE_UUID/mockups/$FNAME" "projects/$ACTIVE_UUID/mockups/_index.json" "projects/_index.json"
git commit -m "save-mockup: $TITLE"
git push origin main 2>&1 || echo "⚠️ push failed. local commit 됨." >&2
cd - > /dev/null

OWNER=$(cd "$HAMSTERN_DATA" && git remote get-url origin | sed -E 's|.*[:/]([^/]+)/.+|\1|')
URL="https://$OWNER.github.io/hamstern-data/p/$ACTIVE_UUID/mockups/$FNAME"
echo "✅ 저장됨: $URL"
```
```

- [ ] **Step 2: commit**

```
git add skills/save-mockup/SKILL.md
git commit -m "feat(save-mockup): /hams:save-mockup skill for cross-session HTML/이미지 보존 (Sub-F)"
```

---

## Task 7: `/hams:audit-decisions/remove.py` 갱신 — `--data-root` 인자

**Files:**
- Modify: `skills/audit-decisions/remove.py`
- Modify: `skills/audit-decisions/test_remove.py`
- Modify: `skills/audit-decisions/SKILL.md`

- [ ] **Step 1: remove.py 의 main() 에 --data-root 추가**

기존 `main()`:
```python
def main():
    parser = argparse.ArgumentParser(...)
    parser.add_argument("text", help="...")
    parser.add_argument("--project", default=".", help="프로젝트 루트")
    args = parser.parse_args()
    result = run(project_root=Path(args.project).resolve(), text=args.text)
    ...
```

신규:
```python
def main():
    parser = argparse.ArgumentParser(description="Remove a decision by exact body match")
    parser.add_argument("text", help="결정 본문 (앞의 '- ' 와 trailing session 마커 제외)")
    parser.add_argument("--project", default=".", help="프로젝트 루트 (Sub-F 이전 호환용)")
    parser.add_argument("--data-root", help="hamstern-data project 디렉터리 (Sub-F)")
    args = parser.parse_args()
    
    if args.data_root:
        # Sub-F mode: data_root 가 직접 가리키는 projects/{uuid}/
        project_root = Path(args.data_root).resolve()
        # run() 은 project_root/.hamstern/ 을 기대하므로 임시로 그 구조처럼 보이게
        # → 또는 run() 시그니처를 base_dir 로 generalize. 후자가 깔끔.
    else:
        project_root = Path(args.project).resolve()
    
    result = run(project_root=project_root, text=args.text)
    ...
```

- [ ] **Step 2: run() 시그니처 generalize — base_dir 인자 추가**

```python
def run(project_root: Path = None, text: str = "", base_dir: Path = None) -> RemoveResult:
    """
    Sub-F 이전: project_root 지정 → project_root/.hamstern/decisions.md
    Sub-F 이후: base_dir 지정 → base_dir/decisions.md (직접 hamstern-data 의 projects/{uuid}/)
    """
    if base_dir is None:
        base_dir = Path(project_root) / ".hamstern"
    
    decisions_file = base_dir / "decisions.md"
    log_file = base_dir / "decisions-log.md"
    # ... 나머지 동일
```

main() 에서 --data-root 지정 시 base_dir=Path(args.data_root) 로 호출.

- [ ] **Step 3: test_remove.py 에 새 케이스 추가**

```python
def test_run_with_base_dir_arg(tmp_path):
    """Sub-F: base_dir 직접 지정 (hamstern-data/projects/{uuid}/)."""
    base = tmp_path / "uuid-abc"
    base.mkdir()
    (base / "decisions.md").write_text("# d\n\n## A\n- foo\n", encoding="utf-8")
    
    result = removemod.run(base_dir=base, text="foo")
    
    assert result.removed is True
    new = (base / "decisions.md").read_text(encoding="utf-8")
    assert "- foo" not in new
```

- [ ] **Step 4: 기존 5 케이스 + 신규 1 케이스 그린 확인**

```
cd hamstern-plugin
python3 -m pytest skills/audit-decisions/test_remove.py -v
```

Expected: 6 passed.

- [ ] **Step 5: SKILL.md 의 "사용 방법" 섹션 갱신**

다음 추가:
```
### Sub-F 이후 사용

dashboard 의 [×] 클릭이 클립보드에 복사하는 명령에 --data-root 자동 포함:

```
/hams:audit-decisions remove "<text>" --data-root "$HAMSTERN_DATA/projects/$UUID"
```

또는 active-project.json 기반 자동 결정 (Claude 가 SKILL.md 의 다음 패턴 사용):

```bash
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
UUID=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['uuid'])")
python3 skills/audit-decisions/remove.py "<text>" --data-root "$HAMSTERN_DATA/projects/$UUID"
```

이후 hamstern-data 에서 git commit + push.
```

- [ ] **Step 6: commit**

```
git add skills/audit-decisions/remove.py skills/audit-decisions/test_remove.py skills/audit-decisions/SKILL.md
git commit -m "feat(audit-decisions): remove.py --data-root 인자 + Sub-F 사용법 (Sub-F)"
```

---

## Task 8: `build.py` multi-project 확장

**Files:**
- Modify: `skills/dashboard/build.py`
- Modify: `skills/dashboard/test_build.py`

- [ ] **Step 1: test_build.py 에 multi-project 케이스 추가**

```python
def test_build_multiproject_writes_each_uuid(tmp_path):
    """Sub-F: hamstern-data/projects/{uuid}/* → docs/data/p/{uuid}/* 번들."""
    hd = tmp_path / "hamstern-data"
    (hd / "projects" / "uuid-1").mkdir(parents=True)
    (hd / "projects" / "uuid-1" / "decisions.md").write_text("# d1\n- a\n", encoding="utf-8")
    (hd / "projects" / "uuid-2").mkdir(parents=True)
    (hd / "projects" / "uuid-2" / "decisions.md").write_text("# d2\n- b\n", encoding="utf-8")
    
    import json
    (hd / "projects" / "_index.json").write_text(json.dumps({
        "uuid-1": {"name": "Proj 1", "last_active": "2026-05-24T00:00:00Z",
                   "decision_count": 1, "session_count": 0, "mockup_count": 0},
        "uuid-2": {"name": "Proj 2", "last_active": "2026-05-23T00:00:00Z",
                   "decision_count": 1, "session_count": 0, "mockup_count": 0}
    }), encoding="utf-8")
    
    out = tmp_path / "docs" / "data"
    build.run_multiproject(hamstern_data=hd, out_dir=out)
    
    assert (out / "p" / "uuid-1" / "decisions.md").read_text(encoding="utf-8") == "# d1\n- a\n"
    assert (out / "p" / "uuid-2" / "decisions.md").read_text(encoding="utf-8") == "# d2\n- b\n"
    
    root_manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert root_manifest["schema_version"] == 2  # Sub-F bumps
    assert set(root_manifest["projects"].keys()) == {"uuid-1", "uuid-2"}
    assert root_manifest["projects"]["uuid-1"]["name"] == "Proj 1"
```

- [ ] **Step 2: 실패 확인**

```
python3 -m pytest skills/dashboard/test_build.py::test_build_multiproject_writes_each_uuid -v
```

Expected: AttributeError (run_multiproject 없음).

- [ ] **Step 3: build.py 에 run_multiproject 추가**

기존 `run()` 함수 아래:

```python
SCHEMA_VERSION_MULTI = 2


def run_multiproject(hamstern_data: Path, out_dir: Path) -> dict:
    """Sub-F: hamstern-data/projects/* 전체를 docs/data/p/{uuid}/ 로 번들 + root manifest 생성."""
    hamstern_data = Path(hamstern_data)
    out_dir = Path(out_dir)
    
    # stale 정리
    if out_dir.exists():
        for child in out_dir.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # _index.json 로드
    index_file = hamstern_data / "projects" / "_index.json"
    if not index_file.exists():
        # 빈 hamstern-data
        root_manifest = {
            "schema_version": SCHEMA_VERSION_MULTI,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "projects": {}
        }
        (out_dir / "manifest.json").write_text(
            json.dumps(root_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )
        return root_manifest
    
    index = json.loads(index_file.read_text(encoding="utf-8"))
    
    root_manifest = {
        "schema_version": SCHEMA_VERSION_MULTI,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "projects": {}
    }
    
    p_out = out_dir / "p"
    p_out.mkdir(exist_ok=True)
    
    for uuid, info in index.items():
        proj_src = hamstern_data / "projects" / uuid
        if not proj_src.is_dir():
            continue  # _index.json 에는 있지만 디렉터리 없음 — skip
        proj_out = p_out / uuid
        proj_out.mkdir(exist_ok=True)
        
        # run() 의 단일-프로젝트 로직 재사용: data_root = proj_src
        # 단 .hamstern/ 부분 없이 직접 proj_src 가 base
        proj_manifest = run_single_project(proj_src, proj_out)
        
        root_manifest["projects"][uuid] = {
            "name": info["name"],
            "last_active": info.get("last_active", ""),
            "decision_count": info.get("decision_count", 0),
            "session_count": info.get("session_count", 0),
            "mockup_count": info.get("mockup_count", 0),
            "has_decisions": proj_manifest["decisions"],
            "has_log": proj_manifest["decisions_log"],
            "sessions": proj_manifest["sessions"],
            "mockups": proj_manifest.get("mockups", [])
        }
    
    (out_dir / "manifest.json").write_text(
        json.dumps(root_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    return root_manifest
```

- [ ] **Step 4: 기존 run() 을 run_single_project 으로 generalize**

기존:
```python
def run(project_root: Path, out_dir: Path) -> dict:
    ...
    src = project_root / ".hamstern"
    ...
```

신규: 새 함수 `run_single_project` 추가, 기존 `run` 은 wrapper 로 유지 (Sub-D/E 호환):

```python
def run_single_project(src_dir: Path, out_dir: Path) -> dict:
    """직접 source 디렉터리를 받아 out 으로 번들. .hamstern 가정 없음.
    Sub-F: src_dir = hamstern-data/projects/{uuid}/
    """
    src_dir = Path(src_dir)
    out_dir = Path(out_dir)
    
    # stale 정리 (기존 run() 의 로직 복사)
    if out_dir.exists():
        for child in out_dir.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decisions": False,
        "decisions_log": False,
        "sessions": [],
        "mockups": []   # Sub-F
    }
    
    decisions_src = src_dir / "decisions.md"
    if decisions_src.is_file():
        shutil.copy2(decisions_src, out_dir / "decisions.md")
        manifest["decisions"] = True
    
    log_src = src_dir / "decisions-log.md"
    if log_src.is_file():
        shutil.copy2(log_src, out_dir / "decisions-log.md")
        manifest["decisions_log"] = True
    
    sessions_src = src_dir / "sessions"
    if sessions_src.is_dir():
        sessions_out = out_dir / "sessions"
        sessions_out.mkdir(exist_ok=True)
        names = []
        for f in sorted(sessions_src.glob("*.md"),
                        key=lambda p: (-p.stat().st_mtime, p.name)):
            shutil.copy2(f, sessions_out / f.name)
            names.append(f.name)
        manifest["sessions"] = names
    
    # Sub-F: mockups
    mockups_src = src_dir / "mockups"
    if mockups_src.is_dir():
        mockups_out = out_dir / "mockups"
        mockups_out.mkdir(exist_ok=True)
        mockup_names = []
        for f in sorted(mockups_src.iterdir(), key=lambda p: p.name):
            if f.is_file() and f.name != "_index.json":
                shutil.copy2(f, mockups_out / f.name)
                mockup_names.append(f.name)
        # _index.json 도 복사
        idx = mockups_src / "_index.json"
        if idx.exists():
            shutil.copy2(idx, mockups_out / "_index.json")
        manifest["mockups"] = mockup_names
    
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    return manifest


def run(project_root: Path, out_dir: Path) -> dict:
    """Sub-D/E 호환: project_root/.hamstern → out_dir."""
    return run_single_project(Path(project_root) / ".hamstern", out_dir)
```

- [ ] **Step 5: 신규 + 기존 테스트 모두 통과 확인**

```
python3 -m pytest skills/dashboard/test_build.py -v
```

Expected: 6 기존 + 1 신규 = 7 passed.

- [ ] **Step 6: main() 에 --hamstern-data 인자 추가**

```python
def main():
    parser = argparse.ArgumentParser(description="Bundle hamstern data -> docs/data")
    parser.add_argument("--project", default=".", help="Sub-D/E 호환: 프로젝트 루트")
    parser.add_argument("--out", default="docs/data", help="출력 디렉터리")
    parser.add_argument("--hamstern-data", help="Sub-F: hamstern-data 루트 (지정 시 multi-project)")
    args = parser.parse_args()
    
    if args.hamstern_data:
        project = Path(args.hamstern_data).resolve()
        out = Path(args.out) if Path(args.out).is_absolute() else project / args.out
        manifest = run_multiproject(hamstern_data=project, out_dir=out)
        print(f"multi-project bundle: {len(manifest['projects'])} projects")
    else:
        project = Path(args.project).resolve()
        out = Path(args.out)
        if not out.is_absolute():
            out = project / out
        manifest = run_single_project(project / ".hamstern", out)
        print(f"single-project bundle: decisions={manifest['decisions']} sessions={len(manifest['sessions'])}")
```

- [ ] **Step 7: commit**

```
git add skills/dashboard/build.py skills/dashboard/test_build.py
git commit -m "feat(dashboard): build.py multi-project (run_multiproject + run_single_project) (Sub-F)"
```

---

## Task 9: `serve.py` multi-project path 라우팅

**Files:**
- Modify: `skills/dashboard/serve.py`
- Modify: `skills/dashboard/test_serve.py`

- [ ] **Step 1: 새 테스트 추가**

```python
def test_route_multiproject_p_uuid_routes_to_project_dir(tmp_path):
    """Sub-F: /data/p/{uuid}/decisions.md → data_dir/p/{uuid}/decisions.md."""
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (data_dir / "p" / "uuid-1").mkdir(parents=True)
    (data_dir / "p" / "uuid-1" / "decisions.md").write_text("# proj 1", encoding="utf-8")
    
    result = _route(plugin_dir, data_dir, "/data/p/uuid-1/decisions.md")
    assert result == data_dir / "p" / "uuid-1" / "decisions.md"


def test_route_root_manifest_at_data_root(tmp_path):
    """Sub-F: /data/manifest.json (root, multi-project)."""
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (data_dir / "manifest.json").write_text('{"projects":{}}', encoding="utf-8")
    
    result = _route(plugin_dir, data_dir, "/data/manifest.json")
    assert result == data_dir / "manifest.json"
```

- [ ] **Step 2: 실패 확인**

```
python3 -m pytest skills/dashboard/test_serve.py -v
```

Expected: 9 기존은 통과 (route 로직이 이미 `/data/*` 를 generic 하게 처리하니 둘 다 자동 통과 가능). 두 신규도 통과해야 함.

만약 신규가 실패하면 `_route_path` 의 `/data/` 분기가 깊은 path 도 처리하는지 확인. 현재 구현:
```python
if path.startswith("/data/"):
    return _safe_join(data_dir, path[len("/data/"):])
```

이건 이미 `/data/p/{uuid}/...` 를 `data_dir/p/{uuid}/...` 로 매핑함. **추가 코드 불필요.** 테스트 그대로 통과해야 함.

- [ ] **Step 3: serve.py 변경 — 사실상 변경 없음, 테스트만 추가**

확인용:
```
python3 -m pytest skills/dashboard/test_serve.py -v
```

Expected: 11 passed (9 기존 + 2 신규).

- [ ] **Step 4: commit**

```
git add skills/dashboard/test_serve.py
git commit -m "test(dashboard): serve.py multi-project routing regression (Sub-F)"
```

(serve.py 자체는 변경 없음 — 기존 _route_path 가 이미 multi-project 지원.)

---

## Task 10: `docs/index.html` 메인 페이지 (프로젝트 목록)

**Files:**
- Create: `docs/index.html` (Sub-D 의 기존 index.html 을 `docs/p/__template__.html` 로 이동 후 신규 작성)

- [ ] **Step 1: 기존 index.html 백업**

```bash
cd hamstern-plugin
mkdir -p docs/p
mv docs/index.html docs/p/_project.html
# (per-project view 용 템플릿으로 보존)
```

- [ ] **Step 2: 신규 docs/index.html 작성 (프로젝트 목록 페이지)**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🐹 hamstern</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <span class="logo">🐹</span>
  <h1>hamstern</h1>
  <span class="spacer"></span>
  <input id="search" type="search" placeholder="프로젝트 검색…" class="search-input">
  <span class="generated" id="generated">…</span>
</header>

<main class="main main-list">
  <div id="projects-list"><div class="empty">…</div></div>
</main>

<script src="https://cdn.jsdelivr.net/npm/marked@14.1.3/marked.min.js"
        integrity="sha384-k8o8HikHweyzW55Wd3wl18ovJj6vHVYNQeQbeSM0fxx+0WiH4TcccOG9uz8Xd2JR"
        crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.1.7/dist/purify.min.js"
        integrity="sha384-XQqX/4yiUGu+oyr87jvWzRuqBUK/adrY0DunhL+tID9m/9dwSpV8h9Fk/Sg6ifVQ"
        crossorigin="anonymous"></script>
<script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 3: docs/p/_project.html — 기존 index.html 을 per-project 페이지로 적용**

기존 index.html 의 `data/manifest.json` fetch 경로를 `../../data/p/{UUID}/manifest.json` 로 변경. 이건 app.js 의 routing 으로 동적으로 처리 가능 (다음 task).

당장은 `<title>` 과 헤더만 조정:

```html
<title>🐹 hamstern — Project</title>
```

본문 body 의 `data-...` attribute 들은 그대로 두고 app.js 가 URL 의 ?p={uuid} 또는 path 에서 UUID 추출하게.

- [ ] **Step 4: commit**

```
git add docs/index.html docs/p/_project.html
git commit -m "feat(dashboard): docs/index.html 프로젝트 목록 메인 페이지 + p/_project.html 분리 (Sub-F)"
```

---

## Task 11: `docs/app.js` multi-project 라우팅 + mockups column

**Files:**
- Modify: `docs/app.js`

- [ ] **Step 1: 현 app.js 의 load() 함수를 라우팅 분기로 교체**

기존:
```js
async function load() {
  let manifest;
  try {
    manifest = await fetchJSON(`${DATA_PATH}/manifest.json`);
  } catch (e) { ... }
  ...
}
```

신규:
```js
async function load() {
  const path = window.location.pathname;
  
  // Sub-F: /p/{uuid}/... → per-project view
  const projectMatch = path.match(/\/p\/([^/]+)\//);
  if (projectMatch) {
    await loadProject(projectMatch[1]);
    return;
  }
  
  // 기본: 프로젝트 목록 (index.html)
  await loadProjectList();
}


async function loadProjectList() {
  let rootManifest;
  try {
    rootManifest = await fetchJSON(`data/manifest.json`);
  } catch (e) {
    renderEmpty(document.getElementById('projects-list'),
      'hamstern-data 가 아직 publish 안 됨.<br>'
      + 'Claude 세션에서 <code>/hams:dashboard --publish</code> 호출 후 재방문.');
    return;
  }
  setGenerated(rootManifest.generated_at);
  
  const projects = Object.entries(rootManifest.projects || {})
    .sort((a, b) => (b[1].last_active || '').localeCompare(a[1].last_active || ''));
  
  if (projects.length === 0) {
    renderEmpty(document.getElementById('projects-list'),
      '프로젝트 없음. <code>/hams:init "이름"</code> 으로 첫 프로젝트 생성.');
    return;
  }
  
  const el = document.getElementById('projects-list');
  el.innerHTML = projects.map(([uuid, info]) => `
    <a href="p/${encodeURIComponent(uuid)}/" class="project-card">
      <div class="project-name">${DOMPurify.sanitize(info.name)}</div>
      <div class="project-meta">
        decisions: ${info.decision_count} · sessions: ${info.session_count} · mockups: ${info.mockup_count}
      </div>
      <div class="project-last">last: ${info.last_active || '—'}</div>
    </a>
  `).join('');
  
  // 검색 필터
  const searchInput = document.getElementById('search');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.toLowerCase();
      document.querySelectorAll('.project-card').forEach(card => {
        const visible = card.textContent.toLowerCase().includes(q);
        card.style.display = visible ? '' : 'none';
      });
    });
  }
}


async function loadProject(uuid) {
  // 기존 단일 프로젝트 흐름. DATA_PATH 만 갱신.
  const dataPath = `../../data/p/${encodeURIComponent(uuid)}`;
  let manifest;
  try {
    manifest = await fetchJSON(`${dataPath}/manifest.json`);
  } catch (e) {
    renderEmpty(document.getElementById('decisions-list'),
      'Dashboard 데이터 미생성.<br>Claude 세션에서 <code>/hams:dashboard --publish</code> 호출 후 재방문.');
    return;
  }
  setGenerated(manifest.generated_at);
  
  if (manifest.decisions) {
    const md = await fetchText(`${dataPath}/decisions.md`);
    renderDecisions(md);
  } else {
    renderEmpty(document.getElementById('decisions-list'), '결정사항 없음');
  }
  
  renderSessionsList(manifest.sessions || []);
  // sessions 클릭 시 fetch path 가 dataPath 사용하도록 onSessionClick 의 fetchText 인자 조정
  // (전역 currentDataPath 변수로 처리)
  window._currentDataPath = dataPath;
  
  if (manifest.decisions_log) {
    const logMd = await fetchText(`${dataPath}/decisions-log.md`);
    renderLog(logMd);
  } else {
    renderEmpty(document.getElementById('log-list'), '로그 없음');
  }
  
  // Sub-F: mockups column
  renderMockupsList(manifest.mockups || [], uuid, dataPath);
}
```

- [ ] **Step 2: onSessionClick 갱신 — currentDataPath 사용**

```js
async function onSessionClick(e) {
  const item = e.target.closest('.session-item');
  if (!item) return;
  const file = item.dataset.file;
  const dataPath = window._currentDataPath || DATA_PATH;
  ...
  const md = await fetchText(`${dataPath}/sessions/${file}`);
  ...
}
```

- [ ] **Step 3: renderMockupsList 신규 함수 추가**

```js
async function renderMockupsList(mockupFilenames, uuid, dataPath) {
  const el = document.getElementById('mockups-list');
  if (!el) return; // 페이지에 mockups column 이 없으면 skip
  if (!mockupFilenames || mockupFilenames.length === 0) {
    renderEmpty(el, '목업 없음');
    return;
  }
  // _index.json fetch
  let metaIdx = {};
  try {
    metaIdx = await fetchJSON(`${dataPath}/mockups/_index.json`);
  } catch {}
  
  let html = '';
  for (const fname of mockupFilenames) {
    const meta = metaIdx[fname] || {};
    const title = meta.title || fname;
    const url = `${dataPath}/mockups/${fname}`;
    html += `<a href="${url}" target="_blank" class="mockup-item">
      <div class="mockup-title">${DOMPurify.sanitize(title)}</div>
      <div class="mockup-meta">${DOMPurify.sanitize(meta.description || fname)}</div>
    </a>`;
  }
  el.innerHTML = html;
}
```

- [ ] **Step 4: docs/p/_project.html 의 main 영역에 mockups column 추가**

기존 3-column 을 4-column 으로:
```html
<main class="main">
  <section class="col col-sessions" data-tab="sessions"> ... </section>
  <section class="col col-decisions" data-tab="decisions"> ... </section>
  <section class="col col-mockups" data-tab="mockups">
    <h2>Mockups</h2>
    <div id="mockups-list"><div class="empty">…</div></div>
  </section>
  <section class="col col-log" data-tab="log"> ... </section>
</main>
```

탭 nav 도 한 줄 추가: `<button data-tab="mockups">Mockups</button>`.

- [ ] **Step 5: docs/style.css 에 새 클래스 추가**

```css
.project-card {
  display: block;
  padding: 16px 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-bottom: 12px;
  text-decoration: none;
  color: inherit;
  transition: background 0.1s;
}
.project-card:hover { background: #f5f5f9; }
.project-name { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
.project-meta { font-size: 12px; color: #666; }
.project-last { font-size: 11px; color: #aaa; font-family: ui-monospace, monospace; margin-top: 4px; }

.search-input {
  padding: 6px 12px;
  border: 1px solid #888;
  border-radius: 4px;
  font-size: 13px;
  width: 200px;
}

.main-list {
  padding: 24px;
  background: white;
  display: block;
}

.mockup-item {
  display: block;
  padding: 10px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 6px;
  text-decoration: none;
  color: inherit;
}
.mockup-item:hover { background: #f9f9f9; }
.mockup-title { font-size: 13px; font-weight: 600; margin-bottom: 2px; }
.mockup-meta { font-size: 11px; color: #888; }

.col-mockups { width: 240px; flex-shrink: 0; }

@media (max-width: 768px) {
  .col-mockups { width: 100% !important; }
}
```

- [ ] **Step 6: 로컬 검증**

```
cd hamstern-plugin
python3 -m http.server 8765 --directory docs &
SERVER_PID=$!
sleep 1
# 브라우저: http://localhost:8765/ → "프로젝트 없음" 표시 (manifest.json 이 단일-프로젝트라 fail)
# (Task 12 의 dashboard SKILL.md 변경 후 실제 publish 로 검증)
kill $SERVER_PID
```

- [ ] **Step 7: commit**

```
git add docs/app.js docs/style.css docs/p/_project.html
git commit -m "feat(dashboard): app.js multi-project 라우팅 + mockups column (Sub-F)"
```

---

## Task 12: `/hams:dashboard` SKILL.md 갱신

**Files:**
- Modify: `skills/dashboard/SKILL.md`

- [ ] **Step 1: SKILL.md 의 "동작 (Claude 가 실행)" 섹션 갱신**

기존 publish 모드:
```bash
python3 "$PLUGIN_DIR/skills/dashboard/build.py" --project . --out docs/data
git add docs/data/ && git commit -m "..." && git push
```

신규 publish 모드:
```bash
# active-project 에서 hamstern-data path 얻기
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")

# build multi-project
python3 "$PLUGIN_DIR/skills/dashboard/build.py" \
  --hamstern-data "$HAMSTERN_DATA" \
  --out "$HAMSTERN_DATA/docs/data"

# commit + push (hamstern-data 안에서)
cd "$HAMSTERN_DATA"
if [ -n "$(git status --short docs/data/)" ]; then
  git add docs/data/
  git commit -m "chore(dashboard): refresh data $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git push origin main
fi
cd - > /dev/null

# URL: hamstern-data 의 owner/repo 에서 자동 추출
OWNER=$(cd "$HAMSTERN_DATA" && git remote get-url origin | sed -E 's|.*[:/]([^/]+)/.+|\1|')
URL="https://$OWNER.github.io/hamstern-data/"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) start "$URL" ;;
  Darwin) open "$URL" ;;
  Linux) command -v xdg-open >/dev/null && xdg-open "$URL" || echo "open manually: $URL" ;;
esac
```

기존 local 모드도 갱신:
```bash
# active-project 의 hamstern-data path
HAMSTERN_DATA=$(... 같은 helper)

# build multi-project to a temp dir
TMP_DATA="$HAMSTERN_DATA/.tmp-dashboard-data"
python3 "$PLUGIN_DIR/skills/dashboard/build.py" \
  --hamstern-data "$HAMSTERN_DATA" \
  --out "$TMP_DATA"

# 기존 dashboard.pid 정리, serve 기동
... (Sub-E 와 동일하지만 --data-dir 가 $TMP_DATA 가리킴)

# 정적 자산도 hamstern-data 의 docs/ 보다는 plugin install 의 docs/ 를 그대로 사용 (Sub-E)
```

- [ ] **Step 2: SKILL.md 의 책임 + 데이터 테이블 갱신**

| 모드 | 데이터 | 자산 출처 |
|---|---|---|
| **local** | `hamstern-data` 내용 → 임시 dir | plugin install 의 `docs/` |
| **publish** | `hamstern-data/docs/data/` | 같음 (hamstern-data 안 docs/) |

- [ ] **Step 3: commit**

```
git add skills/dashboard/SKILL.md
git commit -m "docs(dashboard): SKILL.md multi-project + hamstern-data 경로로 갱신 (Sub-F)"
```

---

## Task 13: `/hams:migrate-project` skill 신규

**Files:**
- Create: `skills/migrate-project/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

```markdown
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

### Step 4: 파일 복사

```bash
# init 이후 ACTIVE_UUID, HAMSTERN_DATA, PROJ_DIR 셋업됨
mkdir -p "$PROJ_DIR/sessions"

[ -f "$HAMS_DIR/decisions.md" ] && cp "$HAMS_DIR/decisions.md" "$PROJ_DIR/decisions.md"
[ -f "$HAMS_DIR/decisions-log.md" ] && cp "$HAMS_DIR/decisions-log.md" "$PROJ_DIR/decisions-log.md"
[ -d "$HAMS_DIR/sessions" ] && cp -r "$HAMS_DIR/sessions/"*.md "$PROJ_DIR/sessions/" 2>/dev/null
```

### Step 5: 원본 처리

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

(record 의 Step 5 와 같은 로직 — decisions.md 의 '-' 줄 카운트, sessions/*.md 개수)

### Step 8: 사용자 보고

```
✅ 마이그레이션 완료
   $REPO_NAME 의 .hamstern/  →  $HAMSTERN_DATA/projects/$ACTIVE_UUID/
   이름: $NAME / UUID: $ACTIVE_UUID
   결정 N개 / 세션 M개 이전됨.
   원본은 $([ "$DELETE_ORIGINAL" = "1" ] && echo "삭제됨" || echo "보존 + MIGRATED.md 메모 추가")
   현 세션은 새 프로젝트로 자동 바인딩됨.
```
```

- [ ] **Step 2: commit**

```
git add skills/migrate-project/SKILL.md
git commit -m "feat(migrate-project): /hams:migrate-project 1회성 이전 도구 (Sub-F)"
```

---

## Task 14: `/hams:rebuild-index` skill 신규

**Files:**
- Create: `skills/rebuild-index/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

```markdown
---
name: rebuild-index
description: |
  hamstern-data/projects/_index.json 을 디렉터리 스캔으로 재생성 (복구용).
  사용법:
    /hams:rebuild-index
allowed-tools:
  - Read
  - Write
  - Bash
---

# /hams:rebuild-index

`projects/_index.json` 이 디렉터리 상태와 어긋났을 때 (수동 편집·외부 도구 등) 재생성.

## Claude 실행 절차

### Step 1: hamstern-data path 확인

(Task 1 의 helper-1 사용)

### Step 2: projects/ 디렉터리 스캔

```bash
INDEX_FILE="$HAMSTERN_DATA/projects/_index.json"

python3 -c "
import os, json
projects_dir = r'$HAMSTERN_DATA/projects'
new_idx = {}
for entry in sorted(os.listdir(projects_dir)):
    p = os.path.join(projects_dir, entry)
    if not os.path.isdir(p) or entry.startswith('_'):
        continue
    meta_file = os.path.join(p, 'meta.json')
    if not os.path.exists(meta_file):
        print(f'skip (no meta.json): {entry}', file=__import__('sys').stderr)
        continue
    meta = json.load(open(meta_file))
    
    dec_file = os.path.join(p, 'decisions.md')
    dec_count = sum(1 for line in open(dec_file) if line.startswith('- ')) if os.path.exists(dec_file) else 0
    
    sess_dir = os.path.join(p, 'sessions')
    sess_count = len([f for f in os.listdir(sess_dir) if f.endswith('.md')]) if os.path.isdir(sess_dir) else 0
    
    mock_dir = os.path.join(p, 'mockups')
    mock_idx_file = os.path.join(mock_dir, '_index.json')
    mock_count = 0
    if os.path.exists(mock_idx_file):
        mock_count = len(json.load(open(mock_idx_file)))
    
    new_idx[meta['uuid']] = {
        'name': meta['name'],
        'last_active': meta.get('last_active', meta['created_at']),
        'decision_count': dec_count,
        'session_count': sess_count,
        'mockup_count': mock_count
    }

json.dump(new_idx, open(r'$INDEX_FILE', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'rebuilt: {len(new_idx)} projects')
"
```

### Step 3: commit + push

```bash
cd "$HAMSTERN_DATA"
if [ -n "$(git status --short projects/_index.json)" ]; then
  git add projects/_index.json
  git commit -m "chore: rebuild projects/_index.json"
  git push origin main 2>&1 || echo "⚠️ push failed." >&2
fi
cd - > /dev/null

echo "✅ _index.json 재생성 완료"
```
```

- [ ] **Step 2: commit**

```
git add skills/rebuild-index/SKILL.md
git commit -m "feat(rebuild-index): /hams:rebuild-index 복구 도구 (Sub-F)"
```

---

## Task 15: `marketplace.json` + README + conventions.md

**Files:**
- Modify: `.claude-plugin/marketplace.json`
- Modify: `README.md`
- Modify: `docs/conventions.md`

- [ ] **Step 1: marketplace.json 에 5 신규 skill 등록**

기존 `skills` 배열에 다음 5개 추가:
```json
"./skills/init",
"./skills/link",
"./skills/save-mockup",
"./skills/migrate-project",
"./skills/rebuild-index"
```

전체 후 배열은 (순서 정렬):
```json
"skills": [
  "./skills/skill-picker",
  "./skills/skill-creator",
  "./skills/init",
  "./skills/link",
  "./skills/record",
  "./skills/remind",
  "./skills/save-mockup",
  "./skills/audit-decisions",
  "./skills/migrate-project",
  "./skills/rebuild-index",
  "./skills/dashboard",
  "./skills/diary",
  "./skills/registry-collector",
  "./skills/why",
  "./skills/rule",
  "./skills/deeptalk"
]
```

- [ ] **Step 2: README.md 의 slash command 표에 5 신규 행 추가**

기존 표 안에 다음 추가:
```
| `/hams:init`             | 새 hamstern 프로젝트 생성 (UUID + scaffolding)                     |
| `/hams:link`             | 기존 프로젝트로 active 바인딩                                       |
| `/hams:save-mockup`      | HTML/이미지 mockup 을 hamstern-data 에 보존                       |
| `/hams:migrate-project`  | 기존 .hamstern/ → hamstern-data 이전 (1회성)                      |
| `/hams:rebuild-index`    | projects/_index.json 재생성 (복구용)                              |
```

기존 `/hams:dashboard` 행도 갱신:
```
| `/hams:dashboard` | multi-project dashboard (hamstern-data 기반). `--publish` 로 gh-pages |
```

- [ ] **Step 3: README.md 에 Sub-F changelog + hamstern-data 셋업 가이드 추가**

Sub-E changelog 다음에 삽입:
```markdown
### Sub-project F — hamstern-data Repo + UUID per Project (2026-05-24)

- **git-as-DB 패턴 도입** — 사용자의 personal `hamstern-data` repo 하나에 모든 프로젝트의 결정사항·세션·mockup 을 `projects/{uuid}/` 디렉터리 격리로 누적.
- **5 신규 skill**: `init` (프로젝트 생성), `link` (active 바인딩), `save-mockup` (HTML/이미지 cross-session 보존), `migrate-project` (기존 .hamstern/ 이전), `rebuild-index` (복구).
- **4 기존 skill 갱신**: `record`/`remind`/`dashboard`/`audit-decisions remove` 가 hamstern-data 경로 사용.
- **active-project.json** — 디바이스별 `~/.config/hamstern/active-project.json` 으로 active UUID 캐시. multi-device 자연 sync.
- **build.py multi-project** — `run_multiproject()` + root manifest (schema_version=2).
- **Multi-project dashboard** — 메인 페이지 (프로젝트 목록 + 검색) + per-project 4-column view (sessions/decisions/mockups/log).
- **remind 진화** — 모든 decisions + 최근 N=2 sessions (8KB cap). `--deep` 으로 N=5. `--mockups` 로 mockup 메타 포함.
- **diary 변경 없음** — Sub-D verification.md 의 결정 반영.
- Three 병렬 research (AI memory 도구, ADR 생태계, 객관 비교) 결과 git-backed 만장일치 추천.

#### hamstern-data 첫 셋업 가이드

1. GitHub 에서 새 repo 생성: `hamstern-data` (private 권장)
2. 사용자의 머신에 clone (기본 위치: `~/.claude/hamstern-data`)
3. Claude 세션에서 첫 호출: `/hams:init "내 첫 프로젝트"`
4. 자동으로 active 바인딩 + commit + push
5. (옵션) GitHub Settings → Pages → main /docs 활성화 → `/hams:dashboard --publish` 로 dashboard 게시
6. 추가 디바이스: hamstern-data clone + `/hams:link "프로젝트 이름"`
```

- [ ] **Step 4: docs/conventions.md 갱신**

기존 §1 (표준 저장소 레이아웃) 을 갱신해서 git-as-DB 모델 명시. Sub-F 이전 호환성:

```markdown
## 1. 표준 저장소 레이아웃 (Sub-F 이후)

```
{HAMSTERN_DATA}/                          # 사용자의 personal hamstern-data repo
├── projects/
│   ├── {uuid}/
│   │   ├── meta.json                     # {uuid, name, repos, created_at, last_active}
│   │   ├── decisions.md                  # 현재 결정사항 (Sub-C 포맷 유지)
│   │   ├── decisions-log.md              # append-only 이력
│   │   ├── sessions/{session_id}.md      # 세션별 distill
│   │   └── mockups/
│   │       ├── _index.json               # {filename: {title, description, ...}}
│   │       └── *.html|*.png|...
│   └── _index.json                       # {uuid: {name, last_active, counts}}
└── docs/                                  # gh-pages source
    ├── index.html                        # 프로젝트 목록 메인
    ├── p/{uuid}/                         # per-project view
    └── data/                              # build.py 산출물 (manifest + 각 프로젝트 데이터)

# 디바이스별 캐시 (모든 hamstern 사용 디바이스)
~/.config/hamstern/
└── active-project.json                   # {uuid, name, hamstern_data_path, linked_at}
```

옛 단일 `.hamstern/` 인접 모델 (Sub-A~E) 은 `/hams:migrate-project` 로 hamstern-data 모델로 이전.
```

- [ ] **Step 5: 검증 grep**

```
grep -c "Sub-project F" README.md             # 1+
grep -c "hamstern-data" README.md             # 5+
grep -c "/hams:init" README.md                 # 2+
grep -c "git-as-DB" docs/conventions.md        # 1
grep -c "active-project.json" docs/conventions.md  # 1
```

- [ ] **Step 6: commit**

```
git add .claude-plugin/marketplace.json README.md docs/conventions.md
git commit -m "docs: marketplace + README + conventions Sub-F (Sub-F)"
```

---

## Task 16: push + 매뉴얼 UAT + verification.md

**Files:**
- Create: `docs/plans/2026-05-24-sub-f-hamstern-data-repo-verification.md`

### Step 1: 모든 Sub-F commit push

```bash
cd hamstern-plugin
git log --oneline origin/main..main
git push origin main
```

### Step 2: Plugin 캐시 갱신 (Sub-E 와 같은 절차)

```bash
CACHE_DIR="$HOME/.claude/plugins/cache/hamstern/hams/b1146da6b548"
[ -d "$CACHE_DIR" ] && mv "$CACHE_DIR" "${CACHE_DIR}.bak-pre-sub-f"
mkdir -p "$CACHE_DIR"
cp -r "$HOME/workspace/hamstern/hamstern-plugin/." "$CACHE_DIR/"
rm -rf "$CACHE_DIR/.git" "$CACHE_DIR/.claude" "$CACHE_DIR/.pytest_cache"
find "$CACHE_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
```

### Step 3: 11 시나리오 UAT

(사용자 환경 — 새 Claude Code 세션 시작 후 진행)

1. **첫 셋업**: hamstern-data repo 없는 상태에서 `/hams:init "테스트"` → repo URL 입력 → clone + 첫 프로젝트 생성
2. **첫 프로젝트 record/remind**: `/hams:record` 두 번 → `/hams:remind` 로 decisions + 최근 2 sessions 환기
3. **두 번째 프로젝트**: `/hams:init "테스트 2"` → 자동 active 전환
4. **프로젝트 전환**: `/hams:link "테스트"` → 첫 프로젝트로 복귀
5. **mockup save**: `/hams:save-mockup "결제 mockup" payment.html` → 파일 복사 + commit + URL 출력
6. **dashboard local**: `/hams:dashboard` → background 서버 + 브라우저 메인 페이지 + 두 프로젝트 클릭 가능
7. **dashboard publish**: `/hams:dashboard --publish` → gh-pages 빌드 + `https://<owner>.github.io/hamstern-data/` 접근
8. **편집 흐름**: 결정 [×] 클릭 → 클립보드 `/hams:audit-decisions remove "..." --data-root "..."` → 붙여넣어 실행 → 결정 제거 확인
9. **migrate**: 기존 .hamstern/ 가 있는 프로젝트에서 `/hams:migrate-project` → UUID 부여 + 파일 이전 + MIGRATED.md
10. **두 디바이스 시뮬레이션**: 같은 hamstern-data 를 다른 디렉터리에 clone, 양쪽 record, push 충돌 발생 시 사용자 안내
11. **rebuild-index**: 수동으로 _index.json 손상 (한 줄 잘못 편집) → `/hams:rebuild-index` → 정상화

### Step 4: verification.md 작성

```markdown
# Sub-project F — hamstern-data Repo Verification

**Date:** 2026-05-24
**Plan:** `2026-05-24-sub-f-hamstern-data-repo-plan.md`
**Spec:** `2026-05-24-sub-f-hamstern-data-repo-design.md`

## 자동 테스트

| 테스트 | 케이스 수 | 결과 |
|---|---|---|
| `skills/dashboard/test_build.py` | 6 기존 + 1 신규 (multi-project) | ✅ |
| `skills/dashboard/test_serve.py` | 9 기존 + 2 신규 (multi-project routing) | ✅ |
| `skills/audit-decisions/test_remove.py` | 5 기존 + 1 신규 (base_dir 인자) | ✅ |
| `skills/record/test_record_format.py` (Sub-C 회귀) | 10 | ✅ |
| **합계** | **34** | ✅ |

## 수동 UAT

(위 11 시나리오를 사용자 환경에서 실행 후 체크박스 채움 + 발견 사항 기록)

### 발견 사항 / Sub-G 후보

- ...
```

### Step 5: commit + push

```bash
git add docs/plans/2026-05-24-sub-f-hamstern-data-repo-verification.md
git commit -m "test(verify): Sub-F hamstern-data verification log (Sub-F)"
git push origin main
```

---

## Self-Review (plan 작성자 본인 점검)

**Spec coverage:**
- ✅ git-as-DB 모델 (Task 1-3)
- ✅ 5 신규 skill 신설 (Task 2, 3, 6, 13, 14)
- ✅ 4 기존 skill 갱신 (Task 4, 5, 7, 12)
- ✅ build.py multi-project (Task 8)
- ✅ serve.py path routing (Task 9 — 이미 generic)
- ✅ docs/index.html 메인 + p/_project (Task 10)
- ✅ docs/app.js multi-project + mockups (Task 11)
- ✅ active-project.json 스키마 (Task 1)
- ✅ marketplace.json + README + conventions (Task 15)
- ✅ verification.md + UAT 11 시나리오 (Task 16)
- ✅ remind N=2 + 8KB cap + --deep/--mockups (Task 5)
- ✅ migration tool (Task 13)
- ✅ rebuild-index (Task 14)

**Placeholder scan:**
- "<사용자 입력>", "<사용자 확정>" 등 placeholder 는 SKILL.md 의 AskUserQuestion 자리 — 의도된 user input 영역. OK.
- "$CURRENT_SESSION_FILE" — save-mockup 의 source_session 자리. Claude 가 추정해 채움. SKILL.md 안에서 처리 흐름 명시되어 있음.
- 모든 grep 카운트 예상치 명시.

**Type consistency:**
- `ACTIVE_UUID`, `HAMSTERN_DATA`, `PROJ_DIR` 변수명 — 모든 SKILL.md 에서 일관
- `run_multiproject`, `run_single_project` 함수명 — Task 8 정의 + 이후 task 에서 호출 일관
- `_index.json` 경로 — `projects/_index.json` (root) vs `mockups/_index.json` (per-project) 구분 명확

**Risk:**
- plugin 캐시 갱신 (Sub-E 와 동일 문제) — Task 16 Step 2 에서 다룸
- 사용자가 hamstern-data repo 를 직접 생성해야 함 (수동 step) — README 가이드로 안내
- 두 디바이스 동시 push 의 merge conflict 흐름은 자동화 안 됨 — UAT 시나리오 10 으로 검증, 사용자 가이드만 제공
- mockup 의 source_session_file 추정 로직 — Claude 가 현 세션의 가장 최근 sessions/*.md 를 가정 (정확성 medium)
