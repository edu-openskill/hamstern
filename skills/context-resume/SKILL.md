---
name: context-resume
description: |
  context-save로 저장된 세션의 상세 내용을 불러와 다음 세션을 이어감.
  맥락 요약 + 결정사항(ADR 풀상세) + 미정 + 다음 작업 + 참조를 그대로 보여주고, 다음 작업 첫 항목으로 작업 제안.
  여러 세션 중 선택 가능 (--list 또는 인자 없이 여럿 매칭 시).
  사용법:
    /hams:context-resume                  # 가장 최근 세션 환기
    /hams:context-resume "제목 단편"      # 제목 매칭
    /hams:context-resume --list           # 저장된 세션 전체 목록 → 선택
    /hams:context-resume --full           # ⑥ 세션 상세까지 표시 (저장 시 --full로 저장된 경우만)
    /hams:context-resume --from URL       # 새 컴퓨터에서 hamstern-data clone + 프로젝트 선택 + resume
allowed-tools:
  - Read
  - Bash
  - AskUserQuestion
---

# /hams:context-resume

context-save로 저장된 세션을 불러와 다음 세션을 이어가는 진입점.

## 핵심 — context-save와의 짝

| context-save가 만든 것 | context-resume이 보여주는 것 |
|----------------------|---------------------------|
| ① 맥락 요약 | 그대로 표시 (다음 세션 즉시 컨텍스트) |
| ② 결정사항 ADR 풀상세 | 그대로 표시 (모든 5필드) |
| ③ 미정 사항 | 그대로 표시 |
| ④ 다음 작업 | 그대로 표시 + 첫 항목 작업 시작 제안 |
| ⑤ 참조 | 그대로 표시 (parent chain 포함) |
| ⑥ 세션 상세 (--full 저장 시) | --full 옵션으로 표시 |

## Claude 실행 절차

### Step 1: 인자 파싱 + --from URL 처리

```bash
FROM_URL=""
LIST_ALL=0
SHOW_FULL=0
QUERY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --from) FROM_URL="$2"; shift 2 ;;
    --list) LIST_ALL=1; shift ;;
    --full) SHOW_FULL=1; shift ;;
    *) [ -z "$QUERY" ] && QUERY="$1"; shift ;;
  esac
done
```

`--from URL` 있으면: hamstern-data를 clone (또는 pull) 후 프로젝트 선택 → active 바인딩 → 일반 resume 계속. (link --repo 워크플로우 내부 위임. 새 컴퓨터에서 한 줄로 진입.)

### Step 2: active project + sessions dir

```bash
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
[ ! -f "$ACTIVE_CONFIG" ] && { echo "❌ active project 없음. /hams:link 또는 /hams:context-resume --from URL 먼저." >&2; exit 1; }
UUID=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['uuid'])")
NAME=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['name'])")
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
PROJ_DIR="$HAMSTERN_DATA/projects/$UUID"
SESS_DIR="$PROJ_DIR/sessions"
[ ! -d "$SESS_DIR" ] && { echo "저장된 세션 없음. /hams:context-save로 첫 저장 후 다시." >&2; exit 0; }
```

### Step 3: 자동 pull (cross-device sync)

`--from`이 아닌 경우만 (이미 Step 1에서 처리됨).

```bash
if [ -z "$FROM_URL" ]; then
  (cd "$HAMSTERN_DATA" && git pull origin main 2>&1 | tail -2 || true)
fi
```

### Step 4: 후보 찾기 + 선택

```bash
# filename YYYYMMDD-HHMMSS 정렬 (mtime 아님, 파일명이 canonical)
FILES=$(find "$SESS_DIR" -maxdepth 1 -name "*.md" -type f 2>/dev/null | sort -r | head -20)
[ -z "$FILES" ] && { echo "저장된 세션 없음."; exit 0; }
COUNT=$(echo "$FILES" | grep -c .)
```

선택 로직:
- `--list`: 항상 목록 → AskUserQuestion으로 선택
- QUERY 있음 (제목 단편): 매칭하는 파일들 → 1개면 자동 / 여러개면 AskUserQuestion
- QUERY 없음 + 후보 1개: 자동 선택
- QUERY 없음 + 후보 여럿: 가장 최근 자동 선택. 표시 끝에 "다른 세션 보려면 /hams:context-resume --list" 안내

목록 표시 형식 (AskUserQuestion 옵션):

```
1. 2026-05-30 11:45 - design-talk (default mode, decisions: 5)
2. 2026-05-30 10:00 - init (default mode, decisions: 1)
3. 2026-05-29 22:00 - exploration (full mode, decisions: 3)
```

### Step 5: 선택된 세션 표시

선택된 파일을 그대로 cat. 추가로 머리에 요약 메타:

```
═══════════════════════════════════════════════
RESUMING CONTEXT
프로젝트:    {project}
제목:        {title}
저장:        {timestamp} ({n분/시간/일 전})
Session ID:  {session_id}
Mode:        {default | full}
Parent:      {parent_session or "—"}
═══════════════════════════════════════════════
```

이후 파일 내용 그대로 출력 (① 맥락 요약 → ⑤ 참조).

`--full` 옵션 + 저장 시 --full 모드였으면 ⑥ 세션 상세도 표시. 그 외엔 ⑥ 생략 (또는 "⑥ 세션 상세는 --full로 호출 시 표시" 한 줄 안내).

### Step 6: 다음 단계 제안 (AskUserQuestion)

```
다음 어떻게 진행할까요?

A) ④ 다음 작업의 첫 항목부터 이어 작업 (추천)
B) 다른 다음 작업 항목 선택
C) 그냥 환기만, 직접 결정
D) parent 세션도 마저 환기 (parent_session 있으면)
```

A 선택 시: 첫 항목을 풀어 설명하고 "지금 시작할까요?" 확인.
D 선택 시: parent_session ID로 같은 흐름 재귀.

## 다른 컴퓨터 시나리오 (한 줄)

```
/hams:context-resume --from https://github.com/me/hamstern-data.git
→ clone + 프로젝트 선택 (목록) + 가장 최근 세션 환기 + 다음 작업 제안
```

## 옛 record 세션과의 호환

record로 저장된 sessions 파일은 frontmatter `mode` 필드 없음. resume이 읽을 때:
- frontmatter `mode` 없으면 → `mode: legacy` 처리
- legacy 세션은 "결정" + "열린 질문" 섹션만 있음. 그대로 표시하되 머리에 안내: "이 세션은 옛 record 포맷입니다. context-save로 새로 저장하면 더 풍부한 환기 가능."
