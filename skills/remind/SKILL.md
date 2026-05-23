---
name: remind
description: |
  과거 세션의 결정사항을 현재 세션에 환기. /clear 후 또는 다른 세션의 작업 맥락이 필요할 때 명시적으로 호출.
  CLAUDE.md 안 건드림 — 호출한 그 세션에만 영향.
  사용법:
    /hams:remind            # .hamstern/decisions.md 환기
allowed-tools:
  - Read
  - Bash
---

# /hams:remind

`.hamstern/decisions.md` (현재 결정사항) 를 한 번 환기시킨다.

## 왜 자동 주입이 아닌가

- `/clear` = 진짜 컨텍스트 비우기. 거기에 자동으로 뭔가 채워넣으면 GC 효과가 반감된다.
- 모든 작업이 결정사항을 필요로 하지 않는다 — 가벼운 질문엔 빈 컨텍스트가 더 빠르고 정확하다.
- 사용자가 `/hams:remind` 의 출력을 눈으로 보면서 "지금 이 결정들이 적용 중" 인지 의식적으로 인지할 수 있다.

따라서 컨텍스트 환기는 **사용자가 명시적으로 `/hams:remind` 를 부른 그 시점에만** 일어난다.

## 실행

```bash
/hams:remind          # decisions.md
```

## Claude 실행 절차

1. **decisions.md 경로 해석**:
   ```bash
   ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT=$(pwd)
   path="$ROOT/.hamstern/decisions.md"
   ```

2. **파일 존재 확인 후 본문 출력**:
   ```bash
   cat "$path"
   ```

3. **출력 후 응답에 한 줄 메모 추가**:
   ```
   > _위 결정사항이 이 세션에 환기됨. 진짜 컨텍스트 정리는 /clear._
   ```

### 파일이 없을 때

```
decisions.md 없음.
/hams:record 로 결정사항을 기록한 후 다시 호출하세요.
```

## 두 세션 워크플로우

```
세션1: 작업 → /hams:record           (sessions/{id}.md + decisions.md 작성)
세션2: /hams:remind                   (decisions.md 환기)
```

## 다른 컨텍스트 정리 방법

진짜 GC (어텐션 비우기) 는 호스트만 가능하다. Claude Code 의 진입점:

| 방법 | GC 강도 |
|---|---|
| `/clear` | 완전 리셋 — 자동 주입 없음. 필요하면 `/hams:remind` 로 따로 환기. |
| `/compact` | 모델이 요약, 일부 보존 — 동일 |
| 새 worktree + 새 세션 | 완전 격리 |

운영 패턴: **`/clear` → (필요시) `/hams:remind`**.
