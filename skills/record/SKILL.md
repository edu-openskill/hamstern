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

## 왜 record 인가

- `/hams:dashboard` 는 mom→boss 분석·핀 흐름이라 CLI 전용 (Opus 호출 + 백그라운드 서버).
- Stop hook 은 baby/mom 자동 캡쳐라 CLI 전용 + 자동.
- **Desktop App 에서도 결정을 같은 저장소에 남기려면 사용자 트리거 슬래시 명령이 필요** — 그게 record.
- 진입점 분리: hook=raw turn, record=distilled decision, dashboard=Opus 정리. 셋 모두 종착지 `decisions.md` 동일.

자세한 규약은 [`docs/conventions.md`](../../docs/conventions.md) 참조.

## Claude 실행 절차

### Step 1 — 경로 해석 + 자동 마이그레이션 + 저장소 보장

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT=$(pwd)
echo "resolved root: $ROOT"
```

사용자에게 resolved root 를 echo 해서 잘못된 경우 즉시 abort 가능하게 한다.

#### 자동 마이그레이션 (idempotent, 안전 백업)

옛 구조 (`baby-hamster/`, `mom-hamster/`, `boss-hamster/`) 가 존재하면 첫 record 호출 시 자동 이전:

```bash
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
  echo "마이그레이션 완료. 옛 데이터는 $BACKUP 에 보존."
fi
```

마이그레이션 실패 시 (권한 등) record 진행 중단 + 에러 메시지 출력. 사용자가 백업 디렉토리로 수동 복구 가능.

#### 저장소 보장

```bash
mkdir -p "$ROOT/.hamstern/sessions" 2>/dev/null
```

`mkdir` 가 실패하면 (sandbox, EACCES 등) → **Step 5 (텍스트 폴백)** 으로.
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

한 번 record 호출 = 두 파일에 동시 쓰기. 둘은 sequential 이지만 다음 호출이 idempotent 라 부분 실패도 자동 복구.

#### (a) `sessions/{session_id}.md` — full distill 저장

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

#### (b) `decisions.md` — 결정 부분만 카테고리별 append

각 채택된 결정 후보에 대해:

1. **세션 마커 매칭**: 같은 `<!-- session: {id} -->` 마커가 이미 있으면 그 항목을 **갱신**.
2. **Jaccard 매칭**: 새 항목 텍스트 vs 기존 항목 텍스트의 Jaccard 유사도 > 0.7 → **skip**.
3. **신규**: 위 두 케이스 아니면 해당 카테고리 (`## {Architecture|Performance|UI|Testing|Deployment|Other}`) 섹션 끝에 **append**. 카테고리 섹션이 없으면 새로 생성.

쓰기 시 `_마지막 업데이트: ...` 라인을 현재 ISO timestamp 로 갱신.

실패·폐기와 열린 질문은 decisions.md 에는 쓰지 않는다 (sessions/{id}.md 에만 보존). decisions.md 는 "현재 유효한 결정의 집합" 만 보유.

#### (c) `decisions-log.md` — append-only 이력

```markdown
## {YYYY-MM-DD HH:MM} · session {id}
+ [결정] 포터블 경로는 git-root → pwd 폴백
+ [실패] 환경변수 기반 환경 판단 → 폐기
+ [열림] decisions.md hot 영역 상한 결정 방식
```

`decisions-log.md` 가 없으면 첫 줄에 `# Decisions Log\n<!-- append-only. 수동 편집 금지. -->\n` 추가 후 블록 append.

### Step 5 — 텍스트 폴백 (FS 쓰기 차단 시)

```
⚠️ 파일 시스템 쓰기 불가 환경입니다 (예: Claude Desktop sandbox).
아래 마크다운을 CLI 세션에서 {project_root}/.hamstern/ 에 직접 병합하세요.

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

세 블록 모두 포맷 동일 → 사용자가 복붙하면 CLI 의 record 호출과 같은 저장소로 수렴.

## 사용 예시

```bash
# 마일스톤 끝에 한 번
/hams:record

# 긴 세션의 정리 패스 (확인 생략)
/hams:record --yes
```

## 다른 진입점과의 관계

- **`/hams:record` 가 hamstern 의 단일 capture 진입점**. hook (이전 CLI 자동 캡쳐) 은 Sub-C 에서 제거됨. start/stop 라이프사이클도 없음 — record 첫 호출 시 `.hamstern/sessions/` 가 자동 생성됨.
- **/hams:remind** 는 record 가 쓴 `decisions.md` 를 그대로 환기 — 포맷 호환성이 핵심.
- **/hams:audit-decisions** 는 record 가 쓴 `decisions.md` 와 `sessions/*.md` 를 재검토.
- **/hams:dashboard** 는 read + 편집 (toggle/remove) — record 가 쓴 데이터 위에서 작동. Sub-D 가 github.io static + 브라우저 편집 UI 로 재설계 예정.
