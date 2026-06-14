# Decision Guard (sub-project B) — Design

- 날짜: 2026-06-14
- 대상 repo: `edu-openskill/hamstern` (이 repo)
- 성격: 설계 스펙 (구현 전). 후속 = writing-plans → 구현
- 배경: `docs/discussions/2026-06-14-hamstern-spec-drift-gate.md` — 두 게이트 중 사전·blocking·판단 게이트
- 관계: A(freshness, 사후·advisory·deterministic)와 짝. B는 사전·loud·reasoning.

## 1. 목적과 범위

스펙 드리프트의 두 충돌 중 **"내력벽 충돌"**(변경이 과거의 의도적 결정을 *모르고* 뒤집는 re-litigation)을 커밋 전에 잡는다. `/hams:guard` = 커밋 전 수동 실행, `git diff HEAD`가 `decisions.md`의 결정을 뒤집는지 **독립 3인 패널**로 판단해 시끄럽게 경고.

**비범위:** 자동 hook/blocking(hamstern은 hook 제거 — B는 경고, 사용자가 판단), decisions.md 수정(supersede는 audit-decisions가), A의 freshness.

## 2. 아키텍처 + 흐름

새 스킬 `/hams:guard` — Claude-오케스트레이션(`why`처럼 SKILL.md가 단계 지시 + 서브에이전트 디스패치):

```
1. diff 수집   : git diff HEAD (working tree vs HEAD = 커밋 예정 변경 전부)
                 비어있으면 → "변경 없음" 안내 후 종료
2. decisions   : active 프로젝트 decisions.md 로드 → '- ' 줄 단위 파싱
   파싱          (결정 목록: {category, text, reason, session}). 비면 "결정 없음, 검사 불가"
3. 독립 판단   : 3인 패널 — 각 서브에이전트에 (diff + 결정 목록)만 전달 (변경 이유 X)
   (3 서브에이전트  질문: "이 diff가 이 결정들 중 무엇을 뒤집나? 각각 [결정]+[왜 모순]
    병렬)          인용. 회의적으로 — 무관한 변경은 플래그 금지, 진짜 번복만."
4. 집계        : 결정별 플래그 카운트. ≥2/3 동의 시 확정 플래그.
5. 리포트      : 플래그된 결정 + 모순 근거 + 두 출구 (시끄럽게). 충돌 0 → ✅
```

**핵심 결정:**
1. **diff = `git diff HEAD`** — staged 여부 무관하게 커밋 예정 변경 전부 포착.
2. **decisions 파싱은 deterministic** — `- {결정} (이유) <!-- session -->` 줄을 기계적 추출해 판단자 입력 한정(토큰 절약, 깔끔).
3. **판단자는 diff + 결정만, 변경 이유는 숨김** — 독립성의 핵심(자기합리화 차단).
4. **회의적 프롬프트** — 무관한 변경 플래그 금지, 진짜 번복만 (cry-wolf 방지).

## 3. 판단자 — 3인 패널 + 다수결

loud 게이트는 거짓 음성(번복 놓침)·거짓 양성(cry-wolf) 둘 다 아프다. 3인 패널 + 다수결로 균형:
- 여러 눈 → 미묘한 번복 포착(거짓 음성↓).
- **결정 하나를 ≥2/3가 플래그해야 확정** → 외톨이 과민 무시(거짓 양성↓).
- B는 수동·중요 커밋에만 → 3회 서브에이전트 비용 감당 가능.
- 집계: 파서가 결정 목록에 **번호(1..N)를 매겨** 판단자에게 제시 → 각 판단자는 `[{n: 번호, why: 모순근거}]`로 플래그한 번호만 반환 → 번호별 카운트 ≥2면 확정. (번호로 매칭하므로 판단자 간 표현 차이 무관)
- `why`가 이미 4 서브에이전트 병렬을 쓰는 패턴과 동일. deeptalk의 "adversarial verify".

## 4. 출력 + 해소 흐름

```
⚠️ 이 변경이 결정을 뒤집는 것 같습니다 (3인 중 N명 동의)

[결정] {결정 내용} (이유: {왜}) — {카테고리} · session {id}
[모순] {판단자들이 제시한 — 이 diff가 왜 이 결정과 충돌하는지}

→ 의도한 변경이면: /hams:audit-decisions 로 이 결정을 supersede 후 진행
→ 실수면: 변경을 되돌리세요

(충돌 0 → "✅ 결정 충돌 없음 · 검토한 결정 N개")
```

**핵심 결정:**
1. **B는 read-only** — diff·decisions 읽고 보고만. decisions.md 수정·커밋 차단 안 함. supersede는 `/hams:audit-decisions`로 사용자가 별도 실행. (hamstern "사람이 소유")
2. **두 출구 명시** — 의도면 supersede(audit 연결), 실수면 revert.
3. **명확한 verdict 종료** — ⚠️ 충돌 N건 / ✅ clean. (지금은 보고가 전부, 나중에 DoD·hook이 이 신호 사용 가능)

## 5. 스킬 정체성 + 규율

- **새 스킬 `/hams:guard`** (audit-decisions의 모드 아님 — 목적이 다름: 들어오는 변경 검사 vs 기존 결정 재검토).
- marketplace.json 등록 + plugin.json·marketplace.json 1.5.0 → 1.6.0.
- 구현: `skills/guard/SKILL.md`(오케스트레이션) + `skills/guard/parse_decisions.py`(파서 헬퍼). 판단은 SKILL.md의 Agent 디스패치 지시.

## 6. 테스트 + dogfood

**deterministic → pytest (`skills/guard/test_parse_decisions.py`):**
- decisions.md 파서: 표준 줄 → `{category, text, reason, session}`; 카테고리 헤더 추적; 빈 파일 → []; 비표준/헤더 줄 무시.
- (diff 헬퍼가 스크립트면 포함; 아니면 SKILL.md의 Bash 단계)

**판단(3 서브에이전트) → 비결정적 → dogfood:**
- **양성**: 알려진 결정을 명백히 뒤집는 diff → `/hams:guard` → 그 결정 플래그 확인.
- **음성**: 무관한 diff → "✅ 충돌 없음".
- hamstern-plugin이 hamstern-data에 자체 decisions.md 없으면 dogfood용 시나리오 임시 구성(테스트 결정 + 번복 diff).
- 판단 단계는 본질상 reasoning이라 단위테스트 불가 — 파서만 pytest, 판단은 dogfood.

## 7. 합격 기준 (DoD)

- [ ] `/hams:guard` 스킬: git diff HEAD 수집 → decisions 파싱 → 3 판단자 디스패치 → ≥2 다수결 집계 → loud 리포트
- [ ] 파서가 decisions.md 줄을 {category, text, reason, session}로 정확히 파싱 (pytest)
- [ ] 빈 diff / 빈 decisions 우아한 처리
- [ ] 판단자는 diff+결정만 받음(변경 이유 숨김), 회의적 프롬프트
- [ ] read-only — decisions.md 미수정, 출력에 supersede(audit-decisions)·revert 두 출구
- [ ] marketplace.json 등록 + 1.6.0 bump
- [ ] dogfood: 번복 diff → 플래그, 무관 diff → clean
