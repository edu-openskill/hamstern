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

`projects/_index.json` 이 디렉터리 상태와 어긋났을 때 (수동 편집·외부 도구·동기화 충돌 등) 재생성하는 복구 도구.

본 skill 은 idempotent — 재실행해도 같은 입력에 대해 동일한 출력 생성. 변경 없으면 commit 자체를 만들지 않는다.

## Claude 실행 절차

### Step 1: hamstern-data path 확인

active-project.json 에서 `hamstern_data_path` 읽기 (Task 1 의 standard helper-1):

```bash
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
if [ ! -f "$ACTIVE_CONFIG" ]; then
  echo "no active project. run /hams:link \"name\" or /hams:init \"name\" first." >&2
  exit 1
fi
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")

[ ! -d "$HAMSTERN_DATA/projects" ] && {
  echo "hamstern-data/projects 디렉터리 없음: $HAMSTERN_DATA" >&2
  exit 1
}
```

### Step 2: projects/ 디렉터리 스캔

각 서브디렉터리 (`_` 로 시작하지 않는) 의 `meta.json` 을 읽어 카운트 산출:

- decisions: `decisions.md` 의 `- ` 로 시작하는 줄 개수
- sessions: `sessions/` 의 `*.md` 파일 개수
- mockups: `mockups/_index.json` 의 엔트리 수

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

각 엔트리 필드: `name`, `last_active`, `decision_count`, `session_count`, `mockup_count`.

`meta.json` 이 없는 디렉터리는 skip + stderr 로 경고만 출력 (스캔 자체는 계속). `_` 로 시작하는 디렉터리는 `_index.json` 같은 메타 파일이므로 자동 제외.

### Step 3: commit + push (변경 있을 때만)

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

`git status --short` 로 변경 여부 확인 — 디렉터리 상태가 이미 일관성 있을 때 (예상 결과) 는 빈 commit 만들지 않음. 이게 idempotency 의 핵심.

## 다른 진입점과의 관계

- 평상시에는 호출 불필요. `/hams:record` 와 `/hams:save-mockup` 가 매번 `projects/_index.json` 의 카운트를 직접 갱신하기 때문에 정상 흐름에서는 인덱스가 자동 정합.
- 호출 시점: (a) 수동으로 `_index.json` 을 편집했거나, (b) 외부 도구 / 다른 디바이스가 디렉터리를 직접 수정했거나, (c) dashboard 가 보여주는 카운트가 실제와 어긋날 때.
- `/hams:link` 의 검색은 `_index.json` 을 읽으므로, 인덱스가 stale 하면 본 skill 로 복구 후 다시 link.
