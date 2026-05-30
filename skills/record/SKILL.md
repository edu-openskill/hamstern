---
name: record
description: |
  [DEPRECATED 2026-05-30] /hams:context-save를 대신 사용하세요. record는 결정사항만 저장하지만, context-save는 세션 narrative + ADR 풀상세 결정 + 미정 + 다음 작업 + 참조까지 함께 저장 (--full 시 시간순 상세 narrative도).
allowed-tools:
  - Bash
---

# /hams:record (DEPRECATED)

이 스킬은 2026-05-30 폐기되었습니다. **`/hams:context-save`를 사용하세요.**

## 왜 폐기됐는가

record는 결정사항만 저장해서 다음 세션이 결정에 도달한 사고·맥락·뉘앙스를 모두 잃었습니다. context-save는 그 결함을 해결합니다.

| 비교 | record (옛) | context-save (신) |
|------|-----------|------------------|
| 결정 | 한 줄 + 이유 한 줄 | ADR 5필드 (결정·논의 맥락·왜 대안 아닌가·함의·참조) |
| 맥락 narrative | ❌ | ✅ ① 맥락 요약 (1~3 단락) |
| 미정 | ✅ | ✅ |
| 다음 작업 | ❌ | ✅ ④ 번호 매김 (구체 행동 권장) |
| 참조 (artifacts) | ❌ | ✅ ⑤ + parent_session 자동 연결 |
| 시간순 상세 narrative | ❌ | ✅ ⑥ --full 옵션 |

## 마이그레이션

옛 record로 저장된 sessions 파일은 `/hams:context-resume`이 그대로 읽을 수 있습니다 (legacy 모드). 그러나 새로운 풍부함은 못 누림.

지금부터 저장하는 건 `/hams:context-save` 사용.
