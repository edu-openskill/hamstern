---
name: remind
description: |
  [DEPRECATED 2026-05-30] 결정만 환기는 /hams:context-decisions, 세션 풀상세 환기는 /hams:context-resume 사용. --from URL 옵션은 두 신규 스킬에도 동일하게 있음.
allowed-tools:
  - Bash
---

# /hams:remind (DEPRECATED)

이 스킬은 2026-05-30 폐기되었습니다. 용도에 따라 둘로 분리되었습니다:

| 원하는 것 | 새 스킬 |
|----------|--------|
| decisions.md만 빠르게 환기 (가벼움) | **`/hams:context-decisions`** |
| 세션의 풀상세 환기 (맥락·ADR 결정·미정·다음 작업·참조) | **`/hams:context-resume`** |

두 신규 스킬 모두 `--from URL` 지원 — 다른 컴퓨터에서 한 줄로 진입 가능.

## 왜 분리됐는가

remind는 decisions + 최근 sessions를 둘 다 보여줬지만, sessions에는 결정만 들어 있어서 풍부함이 부족했음. 이제:
- context-save가 세션을 5섹션으로 풍부하게 저장
- 환기도 "결정만" vs "풀상세" 두 모드로 분리
- 각 사용 빈도에 맞는 무게 (decisions = 자주, resume = 가끔)
