---
name: audit-decisions
description: 과거 결정사항의 타당성 재검토 및 폐기 검증
---

# Audit Decisions

현재 프로젝트의 확정된 결정사항들을 재검토하고, 여전히 타당한지, 수정이 필요한지, 폐기해야 하는지 검증합니다.

## 동작 원리

1. **decisions.md 읽기** — 현재 프로젝트의 핀된 결정사항 로드
2. **배경 분석** — sessions/*.md 기록에서 각 결정의 배경 파악
3. **타당성 검증** — Opus가 Haiku 분석으로:
   - ✅ "이 결정은 여전히 타당합니다" (유지)
   - ⚠️ "수정이 필요합니다" (액션 제안 포함)
   - ❌ "폐기를 추천합니다" (사용자 승인 필수)
4. **사용자 확인** — 사용자가 ✅/⚠️/❌ 중 선택
5. **반영** — 승인된 변경사항을 decisions.md에 적용

## 사용 방법

### 인터랙티브 audit (기존)

```bash
/hams:audit-decisions
```

현재 프로젝트의 모든 결정사항을 Opus 분석으로 검토. 옵션 없음.

### 직접 제거 (Sub-D dashboard 가 발행하는 형식)

```bash
/hams:audit-decisions remove "<decision text>"
```

`.hamstern/decisions.md` 에서 본문이 `<text>` 와 정확히 일치하는 첫 `- ` 줄을 삭제 + `decisions-log.md` 에 제거 이벤트 append. `<text>` 는 leading `- ` 와 trailing `<!-- session: ... -->` 마커를 제외한 본문. `"` 가 본문에 있으면 백슬래시 escape (`\"`).

내부 구현: `skills/audit-decisions/remove.py`. Claude 가 다음을 실행:

```
python3 skills/audit-decisions/remove.py "<text>" --project .
```

매칭 0건이면 stderr 메시지 + non-zero exit. dashboard 의 `[×]` 가 발행하는 클립보드 명령에서 호출되는 게 주 사용 사례.

### Sub-F 이후 사용 (hamstern-data 경로)

dashboard 의 [×] 클릭이 클립보드에 복사하는 명령에 `--data-root` 자동 포함:

```
/hams:audit-decisions remove "<text>" --data-root "$HAMSTERN_DATA/projects/$UUID"
```

또는 active-project.json 기반 자동 결정 (Claude 가 SKILL.md 의 다음 패턴 사용):

```bash
ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
UUID=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['uuid'])")
python3 skills/audit-decisions/remove.py "<text>" --data-root "$HAMSTERN_DATA/projects/$UUID"
```

이후 hamstern-data 에서 git commit + push (record/save-mockup 와 동일 패턴).

## 출력 형식

각 결정에 대해 다음 정보 표시:

```
📌 결정사항: "sessions + decisions 2-tier 구조 확정"
├─ 카테고리: architecture
├─ 배경: (sessions/*.md 에서 추출한 배경 정보)
│  "이 2-tier 구조는..."
├─ 현재 상태: 이미 구현됨
└─ 타당성: ⬛⬛⬛⬛⬜ (4/5) — 높음

분석:
  ✅ 유지: 이 아키텍처는 여전히 프로젝트의 핵심 요구사항을 만족합니다.
```

---

```
📌 결정사항: "3-turn 요약 시스템 제거"
├─ 카테고리: performance-optimization
├─ 배경: (context.md에서 추출)
└─ 타당성: ⬛⬛⬜⬜⬜ (2/5) — 낮음

분석:
  ⚠️ 수정 필요:
  - 현재 record 가 sessions/{id}.md + decisions.md 양쪽에 쓰는데,
    decision 갱신 시 sessions 의 해당 항목도 동기화할지 미정.
  - 제안: 단방향 (sessions → decisions) 으로 유지 vs 양방향 sync 도입.
  - 액션: [수정 필요로 마크] 또는 [새 결정 생성]
```

---

```
📌 결정사항: "외부 도구 양보 메커니즘 유지"
├─ 카테고리: architecture
├─ 배경: (context.md에서 추출)
└─ 타당성: ⬛⬜⬜⬜⬜ (1/5) — 매우 낮음

분석:
  ❌ 폐기 추천:
  - 이 양보 메커니즘이 가정했던 외부 도구 (예: macOS 전용 동반 앱) 가
    사용자 환경에 더 이상 존재하지 않습니다.
  - 양보 로직이 남아 있으면 hook 동작을 무음으로 만들 수 있어
    디버깅을 어렵게 합니다.
  - 폐기하려면:
    1. 마커 체크 분기 제거
    2. 관련 테스트 케이스 정리
  - 유지하려면:
    1. 양보 대상 도구의 실제 사용 사례 1개 이상 제시

[폐기 승인] — 이 결정을 지우겠습니다 (⚠️ 돌이킬 수 없음)
[보류] — 더 생각해본 후 나중에
[유지] — 이대로 진행
```

## 사용자 액션

### 검토 결과 선택

각 결정에 대해:

- **✅ 유지** — decisions.md 유지 (변경 없음)
- **⚠️ 수정 필요** — 결정사항 그대로 두고, 편의상 주석만 추가
- **❌ 폐기** — decisions.md에서 제거 (최종 확인 필수)

### 폐기 시 최종 확인

```
❌ 정말로 이 결정사항을 폐기하시겠습니까?

📌 "외부 도구 양보 메커니즘 유지"
   (context에서 폐기된 이유 표시)

[폐기 확인 - 돌이킬 수 없음] [취소]
```

## 결과 저장

- **decisions.md** 자동 재생성

---

## 기술 세부사항

### 입력 데이터

1. `{project}/.hamstern/decisions.md` — 현재 확정 결정사항
2. `{project}/.hamstern/sessions/*.md` — 세션별 distill (결정/실패/열린질문)

### 분석 엔진

- **Opus**: 타당성 분석 (배경 파악 + 현재 상황 비교)
- **Haiku**: 개요 요약 (사용자가 빠르게 이해)

### 출력 데이터

변경 사항:

```
{project}/.hamstern/
└─ decisions.md (재생성)
```

---

## 팁

- **정기적 검토 권장**: 1-2주마다 한 번
- **맥락 파악 중요**: context.md를 먼저 읽으면 타당성 판단이 명확함
- **폐기는 신중히**: 폐기 전에 팀과 논의 권장
