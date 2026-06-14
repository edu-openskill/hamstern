---
name: guard
description: |
  커밋 전, 지금 변경(git diff HEAD)이 과거에 내린 결정(decisions.md)을 뒤집는지
  독립 3인 패널로 판단해 시끄럽게 경고. read-only — 경고만, supersede는 audit-decisions.
  사용법: /hams:guard   (프로젝트 repo 안에서, 커밋 전 실행)
allowed-tools:
  - Bash
  - Agent
---

# /hams:guard

커밋 전 re-litigation(과거 결정을 모르고 번복) 차단. 프로젝트 repo 안에서 실행.
설계: `docs/discussions/2026-06-14-decision-guard-design.md`.

## 절차 (Claude 가 순서대로 수행)

### 1. diff 수집
Bash: `git diff HEAD`. 출력이 비어있으면
"변경 없음 — 커밋할 diff가 없습니다." 출력 후 **종료**.

### 2. 결정 파싱
Bash: `python3 skills/guard/parse_decisions.py` — active 프로젝트 decisions.md를
번호매긴 JSON(`[{n, category, text, reason, session}]`)으로 출력.
빈 배열 `[]` 이면 "결정 없음 — decisions.md가 비어있어 검사할 수 없습니다." 출력 후 **종료**.

### 3. 독립 3인 패널 (병렬 디스패치)
서브에이전트 3개(general-purpose)를 **한 번에 동시** 디스패치. 셋 모두에게 **동일한**
입력만 준다 — diff 전문 + 번호매긴 결정 목록. **변경의 이유·맥락·작성자 의도는 절대
주지 않는다**(독립성의 핵심).

각 에이전트 프롬프트:
> 아래는 어떤 프로젝트의 커밋 전 diff와, 과거에 내린 결정 목록(번호)입니다.
> 이 diff가 이 결정들 중 **무엇을 뒤집거나 모순되는지** 판단하세요.
> 회의적으로: 무관하거나 결정과 공존 가능한 변경은 플래그하지 마세요.
> **명백히 결정을 번복하는 것만**. 각 플래그는 결정 번호 + diff의 어느 부분이 왜 그
> 결정과 충돌하는지 한 문장.
> 출력은 JSON 한 줄: `[{"n": 결정번호, "why": "모순 근거"}]`. 충돌 없으면 `[]`.
>
> --- DIFF ---
> {git diff HEAD 전문}
> --- 결정 목록 ---
> {parse_decisions.py JSON: 번호·결정·이유·카테고리}

### 4. 다수결 집계
세 에이전트의 플래그를 번호별로 카운트. **번호 n을 ≥2명이 플래그하면 확정**.
각 확정 결정의 모순 근거는 그 번호를 플래그한 에이전트들의 why를 종합.

### 5. 리포트
확정 플래그가 있으면 (시끄럽게):

```
⚠️ 이 변경이 결정을 뒤집는 것 같습니다

[결정 {n}] {text} (이유: {reason}) — {category} · session {session}  (3인 중 {count}명 동의)
[모순] {종합된 why}

(확정 결정마다 반복)

→ 의도한 변경이면: /hams:audit-decisions 로 해당 결정을 supersede 후 진행
→ 실수면: 변경을 되돌리세요
```

확정 플래그가 없으면:

```
✅ 결정 충돌 없음 · 검토한 결정 {N}개
```

## 원칙

- **read-only** — decisions.md를 수정하거나 커밋을 막지 않는다. 경고만, 사용자가 판단.
- **독립성** — 판단자에게 변경 이유를 숨겨 자기합리화 편향을 차단.
- **회의적** — 무관한 변경 플래그 금지(cry-wolf 방지). 다수결(≥2)이 외톨이 과민을 거른다.
