---
name: context-decisions
description: |
  현 active 프로젝트의 decisions.md (현재 유효한 결정사항 누적)만 빠르게 환기.
  /clear 후 또는 결정 맥락만 필요할 때. 세션 상세는 보여주지 않음 (그건 /hams:context-resume).
  --from URL 로 다른 컴퓨터에서 한 줄 환기 가능.
  사용법:
    /hams:context-decisions               # decisions.md 전체 표시
    /hams:context-decisions --recent      # 최근 1세션의 결정만
    /hams:context-decisions --from URL    # 새 컴퓨터: clone+선택+결정 환기
allowed-tools:
  - Read
  - Bash
  - AskUserQuestion
---

# /hams:context-decisions

decisions.md만 빠르게 환기. 세션 narrative·미정·다음 작업은 안 보여줌 — 그건 `/hams:context-resume`의 영역.

## 두 환기 스킬의 분담

| 스킬 | 환기 범위 | 언제 |
|------|----------|------|
| `/hams:context-decisions` | decisions.md만 (가벼움) | 결정 룰만 확인하고 싶을 때, 작업 중 수시로 |
| `/hams:context-resume` | 세션 ① 맥락 요약 + ② ADR 풀상세 + ③ 미정 + ④ 다음 작업 + ⑤ 참조 (+ 옵션 ⑥) | 새 세션 시작 시, 작업 이어갈 때 |

## Claude 실행 절차

### Step 1: 인자 파싱 + --from URL 처리

```bash
FROM_URL=""
RECENT=0
QUERY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --from) FROM_URL="$2"; shift 2 ;;
    --recent) RECENT=1; shift ;;
    *) [ -z "$QUERY" ] && QUERY="$1"; shift ;;
  esac
done
```

`--from URL`이면 link --repo 워크플로우 내부 위임 (hamstern-data clone + 프로젝트 선택 + active 바인딩) 후 일반 환기 계속.

### Step 2: active project 해석

```bash
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
[ ! -f "$ACTIVE_CONFIG" ] && { echo "❌ active project 없음. /hams:link 또는 /hams:context-decisions --from URL 먼저." >&2; exit 1; }
UUID=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['uuid'])")
NAME=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['name'])")
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
PROJ_DIR="$HAMSTERN_DATA/projects/$UUID"
```

### Step 3: 자동 pull

```bash
if [ -z "$FROM_URL" ]; then
  (cd "$HAMSTERN_DATA" && git pull origin main 2>&1 | tail -2 || true)
fi
```

### Step 4: 출력

**기본 모드** — decisions.md 전체 표시:

```bash
echo "## 결정사항 (프로젝트: $NAME)"
cat "$PROJ_DIR/decisions.md"
```

**`--recent` 모드** — 가장 최근 세션의 결정만:

```bash
# 가장 최근 sessions/*.md를 찾아 그 session_id를 가진 결정만 grep
LATEST=$(find "$PROJ_DIR/sessions" -maxdepth 1 -name "*.md" -type f 2>/dev/null | sort -r | head -1)
LATEST_ID=$(basename "$LATEST" .md)
echo "## 최근 세션 결정 (session: $LATEST_ID)"
grep -- "<!-- session: $LATEST_ID -->" "$PROJ_DIR/decisions.md" || echo "(이 세션에 해당하는 결정 없음)"
```

### Step 5: 마지막 메모

```
─────
{N}개 결정 환기 완료. 세션 상세가 필요하면 /hams:context-resume.
```

## 자동 주입 안 함 — 사용자 명시 호출만

- `/clear`는 진짜 컨텍스트 비우기. 거기에 자동 주입하면 GC 효과 반감.
- 모든 작업이 결정사항을 필요로 하지 않음.
- 사용자가 출력을 눈으로 보면서 "지금 이 결정들이 적용 중" 의식 가능.

## 두 컴퓨터 워크플로우

```
컴퓨터 A: 작업 → /hams:context-save             (sessions 갱신 + decisions.md 갱신 + push)
컴퓨터 B: /hams:context-decisions --from URL    (clone + 프로젝트 선택 + decisions 환기)
또는:    /hams:context-resume --from URL      (clone + 세션 풀상세 환기)
```
