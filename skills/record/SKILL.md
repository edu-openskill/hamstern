---
name: record
description: |
  hamstern 의 단일 capture 진입점 — 지금 세션을 sessions/{id}.md 에 저장 + 결정사항을 decisions.md 에 누적.
  CLI·Desktop 양쪽 동작, FS 쓰기 불가 시 텍스트 폴백.
  옛 baby/mom/boss 구조는 첫 호출 시 자동 마이그레이션.
  사용법:
    /hams:record         # 후보 확인 모드 (기본)
    /hams:record --yes   # 후보 자동 채택 (긴 세션 끝)
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# /hams:record

지금 세션에서 합의된 결정·실패·열린질문을 추출(distill)해 프로젝트의 `decisions.md` 에 병합한다. CLI·Desktop 양쪽에서 동일하게 동작 — Desktop sandbox 처럼 FS 쓰기가 안 되면 동일 마크다운을 채팅에 출력해 사용자가 CLI 에서 복붙할 수 있게 한다.

## 왜 record 인가 (단일 진입점)

- **수동 = universal**: CLI · Desktop · (향후) 다른 클라이언트 모두에서 동작. hook 같은 자동 캡쳐는 환경 의존성·silent failure 위험.
- **사용자 통제**: 사용자가 의식적으로 호출한 시점의 distill 만 남음. 노이즈 적음.
- **단일 저장소**: sessions/{id}.md (세션 저널) + decisions.md (누적 결정) 두 파일에 atomic dual-write. dashboard 는 viewer + × 제거만, 쓰기는 record 한 곳에서만.

자세한 규약은 [`docs/conventions.md`](../../docs/conventions.md) 참조.

## Claude 실행 절차

### Step 1 — active project 해석 + 자동 마이그레이션 (옛 구조) + 저장소 보장

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
echo "resolved active project: $ACTIVE_UUID → $PROJ_DIR"
```

사용자에게 resolved active project 를 echo 해서 잘못된 경우 즉시 abort 가능하게 한다.

#### 자동 마이그레이션 (옛 baby/mom/boss → 평탄 구조, idempotent, 안전 백업)

옛 구조 (`baby-hamster/`, `mom-hamster/`, `boss-hamster/`) 가 *프로젝트 repo 내 `.hamstern/`* 에 존재하면 자동 이전:

> **Sub-F 이후**: 이 자동 마이그레이션은 *프로젝트 repo 내 .hamstern/* 의 옛 구조 한정. 이미 hamstern-data 로 이전된 사용자는 트리거 안 됨. 옛 `.hamstern/` 가 있는 프로젝트는 `/hams:migrate-project` 로 hamstern-data 로 이전.

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT=$(pwd)
NEEDS_MIGRATE=0
for d in baby-hamster mom-hamster boss-hamster; do
  [ -d "$ROOT/.hamstern/$d" ] && NEEDS_MIGRATE=1
done

if [ "$NEEDS_MIGRATE" = "1" ]; then
  TS=$(date -u +%Y%m%dT%H%M%S)
  BACKUP="$ROOT/.hamstern.bak.$TS"
  cp -r "$ROOT/.hamstern" "$BACKUP"
  echo "백업 생성: $BACKUP"

  mkdir -p "$ROOT/.hamstern/sessions"
  if [ -d "$ROOT/.hamstern/baby-hamster" ]; then
    mv "$ROOT/.hamstern/baby-hamster"/*.md "$ROOT/.hamstern/sessions/" 2>/dev/null
    rmdir "$ROOT/.hamstern/baby-hamster" 2>/dev/null
  fi
  if [ -f "$ROOT/.hamstern/boss-hamster/decisions.md" ]; then
    mv "$ROOT/.hamstern/boss-hamster/decisions.md" "$ROOT/.hamstern/decisions.md"
  fi
  if [ -f "$ROOT/.hamstern/boss-hamster/decisions-log.md" ]; then
    mv "$ROOT/.hamstern/boss-hamster/decisions-log.md" "$ROOT/.hamstern/decisions-log.md"
  fi
  rm -rf "$ROOT/.hamstern/mom-hamster" "$ROOT/.hamstern/boss-hamster" 2>/dev/null
  echo "마이그레이션 완료. 옛 데이터는 $BACKUP 에 보존. /hams:migrate-project 로 hamstern-data 이전 권장."
fi
```

마이그레이션 실패 시 (권한 등) record 진행 중단 + 에러 메시지 출력. 사용자가 백업 디렉토리로 수동 복구 가능.

#### 저장소 보장

```bash
mkdir -p "$PROJ_DIR/sessions" 2>/dev/null
```

`mkdir` 가 실패하면 (sandbox, EACCES 등) → **Step 7 (텍스트 폴백)** 으로.
성공하면 → Step 2 로.

### Step 2 — Distill (현재 세션 컨텍스트에서 추출)

지금까지의 대화에서 다음 세 종류를 분리해 후보 추출:

1. **결정 (decision)** — 이번 세션에 확정한 것 + 이유 한 줄
   - 예: "포터블 경로는 git-root → pwd 폴백 (이유: 비-git 디렉토리에서도 동작 보장)"
2. **실패·폐기 (rejected)** — 시도했다 버린 것 + 이유 한 줄
   - 예: "환경변수 기반 환경 판단 → 폐기 (이유: CLAUDE_CODE_REMOTE 같은 변수는 미문서, 의존하면 깨짐)"
3. **열린 질문 (open)** — 미정 상태로 남은 것
   - 예: "decisions.md hot 영역 상한을 토픽당 N개로 할지 총 토큰으로 할지"

**중요**:
- 원본 턴 로그는 만들지 않는다 (그건 hook 의 baby 영역).
- 후보 5–15 개 정도가 적정. 너무 많으면 사용자가 검토 부담.
- 각 항목에 `category` 라벨 한 줄 (Architecture/Performance/UI/Testing/Deployment/Other) 부착.

### Step 3 — 사용자 확인 (헛것 방지)

`AskUserQuestion` 으로 카테고리별 후보 표 제시. 각 항목에 keep/drop 선택.

`AskUserQuestion` 이 동작하지 않는 환경 (e.g., Desktop 일부) 에서는 폴백으로 다음 패턴 사용:

```
[ 후보 ]
1. (Architecture) 포터블 경로는 git-root → pwd 폴백 (이유: ...)
2. (실패·폐기) 환경변수 기반 환경 판단 → 폐기 (이유: ...)
3. (열린 질문) decisions.md hot 영역 상한 결정 방식

drop 할 번호를 쉼표로 답하세요 (없으면 enter):
```

호출 인자에 `--yes` 가 있으면 이 확인 단계 skip 하고 전부 채택.

### Step 4 — 원자적 이중 쓰기 (sessions/{id}.md + decisions.md)

한 번 record 호출 = 두 파일에 동시 쓰기. 모든 경로는 `$PROJ_DIR = $HAMSTERN_DATA/projects/$ACTIVE_UUID` 기준. 둘은 sequential 이지만 다음 호출이 idempotent 라 부분 실패도 자동 복구.

#### (a) `$PROJ_DIR/sessions/{session_id}.md` — full distill 저장

기존 파일이 있고 같은 session_id 면 in-place 갱신 (replace), 없으면 새로 생성. 포맷:

```markdown
# Session {session_id}

_기록: {ISO timestamp}_

## 결정
- {결정 1} (이유: {왜})
- {결정 2} (이유: {왜})

## 실패·폐기
- {시도} → 폐기: {이유}

## 열린 질문
- {미정 사항}
```

빈 카테고리는 헤더만 남기거나 헤더도 생략 가능 (양쪽 다 acceptable, 일관성만 유지).

#### (b) `$PROJ_DIR/decisions.md` — 결정 부분만 카테고리별 append

각 채택된 결정 후보에 대해:

1. **세션 마커 매칭**: 같은 `<!-- session: {id} -->` 마커가 이미 있으면 그 항목을 **갱신**.
2. **Jaccard 매칭**: 새 항목 텍스트 vs 기존 항목 텍스트의 Jaccard 유사도 > 0.7 → **skip**.
3. **신규**: 위 두 케이스 아니면 해당 카테고리 (`## {Architecture|Performance|UI|Testing|Deployment|Other}`) 섹션 끝에 **append**. 카테고리 섹션이 없으면 새로 생성.

쓰기 시 `_마지막 업데이트: ...` 라인을 현재 ISO timestamp 로 갱신.

실패·폐기와 열린 질문은 `$PROJ_DIR/decisions.md` 에는 쓰지 않는다 (`$PROJ_DIR/sessions/{id}.md` 에만 보존). decisions.md 는 "현재 유효한 결정의 집합" 만 보유.

#### (c) `$PROJ_DIR/decisions-log.md` — append-only 이력

```markdown
## {YYYY-MM-DD HH:MM} · session {id}
+ [결정] 포터블 경로는 git-root → pwd 폴백
+ [실패] 환경변수 기반 환경 판단 → 폐기
+ [열림] decisions.md hot 영역 상한 결정 방식
```

`$PROJ_DIR/decisions-log.md` 가 없으면 첫 줄에 `# Decisions Log\n<!-- append-only. 수동 편집 금지. -->\n` 추가 후 블록 append.

### Step 5 — `_index.json` 갱신

쓰기 완료 후 `$HAMSTERN_DATA/projects/_index.json` 의 active 프로젝트 항목을 갱신:

```bash
INDEX_FILE="$HAMSTERN_DATA/projects/_index.json"
ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
python3 -c "
import json, os
idx = json.load(open(r'$INDEX_FILE'))
proj = idx.get('$ACTIVE_UUID', {})
dec_file = r'$PROJ_DIR/decisions.md'
sess_dir = r'$PROJ_DIR/sessions'
dec_count = sum(1 for line in open(dec_file) if line.startswith('- ')) if os.path.exists(dec_file) else 0
sess_count = len([f for f in os.listdir(sess_dir) if f.endswith('.md')]) if os.path.isdir(sess_dir) else 0
proj['decision_count'] = dec_count
proj['session_count'] = sess_count
proj['last_active'] = '$ISO'
idx['$ACTIVE_UUID'] = proj
json.dump(idx, open(r'$INDEX_FILE', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"
```

### Step 6 — hamstern-data git commit + push

```bash
cd "$HAMSTERN_DATA"
git add "projects/$ACTIVE_UUID/" projects/_index.json
git commit -m "record: 세션 distill ${ISO}"
git push origin main 2>&1 || echo "⚠️ push failed (offline?). local commit 됨." >&2
cd - > /dev/null
```

push 실패는 치명적이지 않다 (local commit 은 보존됨). 다음 record 호출이 누적 push 한다.

### Step 7 — 텍스트 폴백 (FS 쓰기 차단 시)

```
⚠️ 파일 시스템 쓰기 불가 환경입니다 (예: Claude Desktop sandbox).
아래 마크다운을 CLI 세션에서 hamstern-data/projects/$ACTIVE_UUID/ 에 직접 병합하세요.

=== sessions/{session_id}.md (전체 교체) ===
# Session {session_id}

_기록: {ISO timestamp}_

## 결정
- ...

## 실패·폐기
- ...

## 열린 질문
- ...

=== decisions.md (병합용) ===
(전체 decisions.md 내용을 Step 4(b) 규칙대로 합성해 출력)

=== decisions-log.md (append 블록) ===
## {ts} · session {id}
+ [결정] ...
+ [실패] ...
+ [열림] ...
```

세 블록 모두 포맷 동일 → 사용자가 복붙하면 CLI 의 record 호출과 같은 저장소 (`hamstern-data/projects/$ACTIVE_UUID/`) 로 수렴.

## 사용 예시

```bash
# 마일스톤 끝에 한 번
/hams:record

# 긴 세션의 정리 패스 (확인 생략)
/hams:record --yes
```

## 다른 진입점과의 관계

- **`/hams:record` 가 hamstern 의 단일 capture 진입점**. hook (이전 CLI 자동 캡쳐) 은 Sub-C 에서 제거됨. start/stop 라이프사이클도 없음 — record 첫 호출 시 `$PROJ_DIR/sessions/` 가 자동 생성됨.
- **/hams:remind** 는 record 가 쓴 `decisions.md` 를 그대로 환기 — 포맷 호환성이 핵심.
- **/hams:audit-decisions** 는 record 가 쓴 `decisions.md` 와 `sessions/*.md` 를 재검토.
- **/hams:dashboard** 는 read + 편집 (toggle/remove) — record 가 쓴 데이터 위에서 작동. Sub-D 가 github.io static + 브라우저 편집 UI 로 재설계 예정.
- Sub-F 이후 record 의 출력은 사용자의 personal hamstern-data repo. 프로젝트 자체 repo 는 건드리지 않음.
- /hams:init / /hams:link 가 record 의 active project 를 결정.
