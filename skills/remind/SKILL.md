---
name: remind
description: |
  과거 세션 컨텍스트를 현재 세션에 환기. /clear 후 또는 다른 세션의 작업 맥락이 필요할 때 명시적으로 호출.
  CLAUDE.md 안 건드림 — 호출한 그 세션에만 영향.
  사용법:
    /hams:remind            # boss-hamster 결정사항(decisions.md) 로드 (기본)
    /hams:remind mom        # mom-hamster 세션 요약(mom.md) 로드 — ✅ 확정 전 자연 컨텍스트
allowed-tools:
  - Read
  - Bash
---

# /hams:remind

과거 세션의 컨텍스트를 현재 세션에 한 번 환기시킨다. 두 가지 모드:

| 인자 | 로드 대상 | 용도 |
|---|---|---|
| (없음) | `.hamstern/boss-hamster/decisions.md` | ✅ 확정된 결정사항 — 가장 정제된 형태 |
| `mom` | `.hamstern/mom-hamster/mom.md` | 세션 종료 시 Stop hook이 자동 집계한 baby 모음 — ✅ 확정 전 자연 컨텍스트 |

baby(turn 단위 raw 로그)는 노이즈가 많고 어떤 세션 파일을 골라야 할지 모호하므로 인터페이스로 노출하지 않는다.

## 왜 자동 주입이 아닌가

- `/clear` = 진짜 컨텍스트 비우기. 거기에 자동으로 뭔가 채워넣으면 GC 효과가 반감된다.
- 모든 작업이 결정사항을 필요로 하지 않는다 — 가벼운 질문엔 빈 컨텍스트가 더 빠르고 정확하다.
- 사용자가 `/hams:remind` 의 출력을 눈으로 보면서 "지금 이 결정들이 적용 중" 인지 의식적으로 인지할 수 있다.

따라서 컨텍스트 환기는 **사용자가 명시적으로 `/hams:remind` 를 부른 그 시점에만** 일어난다. SessionStart 훅으로 자동 주입하지 않는다.

## 실행

```bash
/hams:remind          # decisions.md
/hams:remind mom      # mom.md
```

## Claude 실행 절차

1. **인자 분기** — `$ARGUMENTS` 의 첫 토큰을 보고 분기:
   - 비어있음 → `target=boss`, `path=.hamstern/boss-hamster/decisions.md`
   - `mom` → `target=mom`, `path=.hamstern/mom-hamster/mom.md`
   - 그 외 토큰 → 사용법 출력 후 종료 (cat 호출 없음):
     ```
     usage: /hams:remind [mom]
       (인자 없음)  → boss-hamster 결정사항(decisions.md) 로드
       mom         → mom-hamster 세션 요약(mom.md) 로드
     ```

2. **파일 존재 확인 후 본문 출력**:
   ```bash
   cat <path>
   ```

3. **출력 후 응답에 한 줄 메모 추가** (target에 따라 분기):
   - boss: `> _위 결정사항이 이 세션에 환기됨. 진짜 컨텍스트 정리는 /clear._`
   - mom: `> _위 세션 요약이 이 세션에 환기됨. ✅ 확정 전 단계의 자연 컨텍스트입니다 — 결정으로 굳히려면 /hams:dashboard._`

### 파일이 없을 때

- decisions.md 부재 (boss 케이스):
  ```
  decisions.md 없음.
  /hams:dashboard 에서 Analyze → ✅ 확정 후 다시 호출하세요.
  ```
- mom.md 부재 (mom 케이스):
  ```
  mom.md 없음.
  Stop hook이 아직 한 번도 안 돌았거나 hamstern 활성 전입니다.
  - 첫 세션을 종료하면 자동 생성됩니다.
  - 또는 수동: python3 skills/dashboard/scripts/aggregate.py {cwd}
  ```

## 두 세션 워크플로우

```
세션1: 작업 → 종료              (Stop hook이 baby append + mom.md 자동 갱신)
세션2: /hams:remind mom         (세션1의 자연 컨텍스트 환기)
   ↓ (필요 시)
세션2: /hams:dashboard          (Analyze → ✅ 확정 → decisions.md 기록)
세션3: /hams:remind             (확정된 decisions.md 환기)
```

## 다른 컨텍스트 정리 방법

진짜 GC (어텐션 비우기) 는 호스트만 가능하다. Claude Code 의 진입점:

| 방법 | GC 강도 |
|---|---|
| `/clear` | 완전 리셋 — 자동 주입 없음. 필요하면 `/hams:remind` 로 따로 환기. |
| `/compact` | 모델이 요약, 일부 보존 — 동일 |
| 새 worktree + 새 세션 | 완전 격리 |

운영 패턴: **`/clear` → (필요시) `/hams:remind` 또는 `/hams:remind mom`**.
