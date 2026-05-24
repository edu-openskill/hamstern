---
name: remind
description: |
  Active hamstern 프로젝트의 모든 결정사항 + 최근 N=2 세션을 현 Claude 세션에 환기.
  /clear 후 또는 다른 세션의 작업 맥락이 필요할 때 명시적으로 호출. CLAUDE.md 안 건드림.
  사용법:
    /hams:remind              # decisions 전체 + 최근 2 sessions (8KB cap)
    /hams:remind --deep        # sessions N=5 까지
    /hams:remind --mockups    # 최근 mockup 메타 5개도 포함
allowed-tools:
  - Read
  - Bash
---

# /hams:remind

Active hamstern 프로젝트의 `decisions.md` (현재 결정사항) + 최근 N=2 sessions 를 한 번 환기시킨다.

## 왜 자동 주입이 아닌가

- `/clear` = 진짜 컨텍스트 비우기. 거기에 자동으로 뭔가 채워넣으면 GC 효과가 반감된다.
- 모든 작업이 결정사항을 필요로 하지 않는다 — 가벼운 질문엔 빈 컨텍스트가 더 빠르고 정확하다.
- 사용자가 `/hams:remind` 의 출력을 눈으로 보면서 "지금 이 결정들이 적용 중" 인지 의식적으로 인지할 수 있다.
- Sub-F 이후 프로젝트가 여러 개 (hamstern-data/projects/{uuid}/) 라서, 어떤 프로젝트의 컨텍스트를 가져올지 active-project.json 으로 명시적 선택 — 자동 주입은 잘못된 프로젝트로 오염될 위험.

따라서 컨텍스트 환기는 **사용자가 명시적으로 `/hams:remind` 를 부른 그 시점에만** 일어난다.

## 실행

```bash
/hams:remind                # decisions 전체 + 최근 2 sessions
/hams:remind --deep          # sessions N=5
/hams:remind --mockups      # 최근 mockup 메타 5개
```

## Claude 실행 절차

1. **active-project + 경로 해석**:

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
   ```

2. **인자 파싱 (--deep, --mockups)**:

   ```bash
   DEEP=0
   INCLUDE_MOCKUPS=0
   for arg in "$@"; do
     case "$arg" in
       --deep) DEEP=1 ;;
       --mockups) INCLUDE_MOCKUPS=1 ;;
     esac
   done
   SESSION_N=$([ "$DEEP" = "1" ] && echo 5 || echo 2)
   ```

3. **hamstern-data 자동 pull (cross-device sync)**:

   ```bash
   cd "$HAMSTERN_DATA"
   git pull origin main 2>&1 | tail -2 || true
   cd - > /dev/null
   ```

4. **decisions.md 전체 출력**:

   ```bash
   echo "## 결정사항 (프로젝트: $ACTIVE_NAME)"
   cat "$PROJ_DIR/decisions.md"
   ```

5. **최근 N sessions 출력 — 8KB 총량 cap** (가장 최근부터, 예산 초과 시 마지막 항목 truncate):

   ```bash
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
   ```

6. **(옵션) --mockups 시 mockup 메타 출력**:

   ```bash
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
   ```

7. **마지막 줄 메모**:

   ```bash
   echo ""
   echo "> _$ACTIVE_NAME 컨텍스트 환기 완료. (decisions 전체 + sessions $SESSION_N개${INCLUDE_MOCKUPS:+ + mockups})_"
   echo "> _진짜 컨텍스트 정리는 /clear._"
   ```

### active project 가 없을 때

```
active project 없음. /hams:link "이름" 으로 기존 프로젝트에 바인딩하거나
/hams:init "이름" 으로 새 프로젝트를 생성하세요.
```

### decisions.md / sessions/ 가 비어있을 때

decisions.md 가 없거나 비어있으면 그냥 빈 섹션이 출력됨. `/hams:record` 로 첫 결정을 기록하면 다음 remind 호출부터 내용이 보임.

## 두 세션 워크플로우

```
세션1: 작업 → /hams:record           ($PROJ_DIR/sessions/{id}.md + decisions.md 갱신 + hamstern-data push)
세션2: /hams:remind                   (hamstern-data pull → decisions + 최근 sessions 환기)
```

cross-device: 디바이스 A 에서 record, 디바이스 B 에서 remind — `git pull` 단계가 다리.

## 다른 컨텍스트 정리 방법

진짜 GC (어텐션 비우기) 는 호스트만 가능하다. Claude Code 의 진입점:

| 방법 | GC 강도 |
|---|---|
| `/clear` | 완전 리셋 — 자동 주입 없음. 필요하면 `/hams:remind` 로 따로 환기. |
| `/compact` | 모델이 요약, 일부 보존 — 동일 |
| 새 worktree + 새 세션 | 완전 격리 |

운영 패턴: **`/clear` → (필요시) `/hams:remind`**.
