# Decision Guard (sub-project B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/hams:guard` 스킬 — 커밋 전 `git diff HEAD`가 `decisions.md`의 결정을 뒤집는지 독립 3인 패널로 판단해 시끄럽게 경고(read-only).

**Architecture:** deterministic 파서(`parse_decisions.py`, pytest-TDD)가 decisions.md를 번호매긴 JSON으로 출력 → `SKILL.md`가 Claude-오케스트레이션(why 패턴)으로 diff 수집·3 서브에이전트 병렬 판단·다수결 집계·loud 리포트. 판단은 본질상 reasoning이라 파서만 단위테스트, 판단은 dogfood.

**Tech Stack:** Python 3 (stdlib), Claude 오케스트레이션 SKILL.md + Agent 디스패치, pytest. 레퍼런스: `skills/why/SKILL.md`(서브에이전트 병렬), `skills/audit-decisions/remove.py`(session 마커 정규식·active-project 경로), `docs/conventions.md §5`(decisions.md 포맷).

**Base:** repo `edu-openskill/hamstern`, branch `feat/decision-guard`. 스펙: `docs/discussions/2026-06-14-decision-guard-design.md`.

---

## File Structure

| 파일 | 변경 | 책임 |
|---|---|---|
| `skills/guard/parse_decisions.py` | 생성 | `parse_decisions(text)` 순수 파서 + active 프로젝트 decisions.md→번호매긴 JSON main |
| `skills/guard/test_parse_decisions.py` | 생성 | 파서 단위테스트 |
| `skills/guard/SKILL.md` | 생성 | 오케스트레이션: diff→파싱→3판단자→다수결→리포트 |
| `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json` | 수정 | guard 등록 + 1.5.0→1.6.0 |

**파싱 결과 형식:** `{"n": int, "category": str|None, "text": str, "reason": str|None, "session": str|None}`.

---

### Task 1: parse_decisions.py (TDD)

**Files:**
- Create: `skills/guard/parse_decisions.py`
- Test: `skills/guard/test_parse_decisions.py`

- [ ] **Step 1: Write the failing test** — `skills/guard/test_parse_decisions.py`:

```python
import importlib.util, pathlib

_spec = importlib.util.spec_from_file_location(
    "pd", pathlib.Path(__file__).parent / "parse_decisions.py")
pd = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(pd)


def test_parses_standard_line():
    text = "## Architecture\n- use HEAD not branch (이유: 기본 브랜치 리다이렉트) <!-- session: s1 -->\n"
    assert pd.parse_decisions(text) == [
        {"n": 1, "category": "Architecture", "text": "use HEAD not branch",
         "reason": "기본 브랜치 리다이렉트", "session": "s1"}]


def test_tracks_categories_and_numbers():
    text = ("## Architecture\n- A (이유: x) <!-- session: s1 -->\n"
            "## Testing\n- B (이유: y) <!-- session: s2 -->\n")
    ds = pd.parse_decisions(text)
    assert [(d["n"], d["category"], d["text"]) for d in ds] == [
        (1, "Architecture", "A"), (2, "Testing", "B")]


def test_decision_text_with_parens_keeps_reason_separate():
    text = "## Architecture\n- L1/L2 model (L1 dev/L2 biz) (이유: 분배) <!-- session: s1 -->\n"
    d = pd.parse_decisions(text)[0]
    assert d["text"] == "L1/L2 model (L1 dev/L2 biz)"
    assert d["reason"] == "분배"


def test_no_reason_and_no_session():
    text = "## Other\n- bare decision\n"
    assert pd.parse_decisions(text) == [
        {"n": 1, "category": "Other", "text": "bare decision",
         "reason": None, "session": None}]


def test_empty_and_non_decision_lines_ignored():
    text = "# 프로젝트 결정사항\n\n_마지막 업데이트: x_\n\n## Architecture\n"
    assert pd.parse_decisions(text) == []


def test_reason_with_inner_parens():
    text = "## Other\n- d (이유: foo (bar) baz) <!-- session: s1 -->\n"
    d = pd.parse_decisions(text)[0]
    assert d["reason"] == "foo (bar) baz"
    assert d["text"] == "d"
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest skills/guard/test_parse_decisions.py -v`
Expected: FAIL (`No such file` / `AttributeError: parse_decisions`)

- [ ] **Step 3: Implement** — `skills/guard/parse_decisions.py`:

```python
"""decisions.md 파서 + active 프로젝트 resolve.

parse_decisions(text) → [{n, category, text, reason, session}] (번호 1..N).
main: active 프로젝트 decisions.md를 읽어 번호매긴 JSON 출력 (SKILL.md가 소비).
"""
import json
import os
import re
import sys

SESSION_RE = re.compile(r"<!--\s*session:\s*(\S+?)\s*-->\s*$")
REASON_RE = re.compile(r"\s*\(이유:\s*(.*)\)\s*$")


def parse_decisions(text):
    decisions = []
    category = None
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            category = s[3:].strip()
            continue
        if not s.startswith("- "):
            continue
        body = s[2:].strip()
        session = None
        m = SESSION_RE.search(body)
        if m:
            session = m.group(1)
            body = SESSION_RE.sub("", body).rstrip()
        reason = None
        rm = REASON_RE.search(body)
        if rm:
            reason = rm.group(1).strip()
            body = REASON_RE.sub("", body).rstrip()
        n += 1
        decisions.append({"n": n, "category": category,
                          "text": body, "reason": reason, "session": session})
    return decisions


def _decisions_path():
    home = (os.environ.get("HOME") or os.environ.get("USERPROFILE")
            or os.path.expanduser("~"))
    cfg = os.path.join(home, ".config", "hamstern", "active-project.json")
    if not os.path.isfile(cfg):
        sys.exit('❌ active project 없음. /hams:link 또는 /hams:init 먼저.')
    with open(cfg, encoding="utf-8") as f:
        c = json.load(f)
    return os.path.join(c["hamstern_data_path"], "projects", c["uuid"], "decisions.md")


def main():
    path = _decisions_path()
    text = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
    print(json.dumps(parse_decisions(text), ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run, verify PASS**

Run: `python -m pytest skills/guard/test_parse_decisions.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add skills/guard/parse_decisions.py skills/guard/test_parse_decisions.py
git commit -m "feat(guard): decisions.md 파서 (번호매긴 JSON)"
```

---

### Task 2: SKILL.md — 오케스트레이션

**Files:**
- Create: `skills/guard/SKILL.md`

- [ ] **Step 1: Create `skills/guard/SKILL.md` with EXACTLY this content:**

````markdown
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
````

- [ ] **Step 2: 검증 (구조)**

Run: `python3 -c "import re,sys; t=open('skills/guard/SKILL.md',encoding='utf-8').read(); assert t.startswith('---'); assert 'name: guard' in t; assert 'git diff HEAD' in t; assert 'parse_decisions.py' in t; assert t.count('### ')>=5; print('SKILL.md ok')"`
Expected: `SKILL.md ok`

- [ ] **Step 3: Commit**

```bash
git add skills/guard/SKILL.md
git commit -m "feat(guard): SKILL.md 오케스트레이션 (3인 패널 다수결)"
```

---

### Task 3: 매니페스트 등록 + 버전 bump

**Files:**
- Modify: `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`

- [ ] **Step 1: marketplace.json** — `plugins[0].skills` 배열 끝(`"./skills/ssot"` 다음)에 `"./skills/guard"` 추가, `metadata.version` `1.5.0`→`1.6.0`.

- [ ] **Step 2: plugin.json** — `version` `1.5.0`→`1.6.0`.

- [ ] **Step 3: 검증**

Run: `python -c "import json; mp=json.load(open('.claude-plugin/marketplace.json')); pj=json.load(open('.claude-plugin/plugin.json')); assert './skills/guard' in mp['plugins'][0]['skills']; assert mp['metadata']['version']=='1.6.0'; assert pj['version']=='1.6.0'; print('OK guard 1.6.0')"`
Expected: `OK guard 1.6.0`
Run: `python -m pytest skills/guard/ -v`
Expected: 6 passed (회귀 없음)

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/marketplace.json .claude-plugin/plugin.json
git commit -m "feat(guard): 매니페스트 등록 + 1.5.0→1.6.0 bump"
```

---

### Task 4: Dogfood (controller 실행 — 오케스트레이션 검증)

> ⚠️ 이 태스크는 `/hams:guard`의 전체 오케스트레이션(3 서브에이전트 디스패치)을 실제로
> 돌려 검증한다. 서브에이전트가 다시 서브에이전트를 디스패치하는 중첩은 취약하므로,
> **메인 세션(controller)이 SKILL.md 절차를 직접 수행**한다.

- [ ] **Step 1: 양성 시나리오 셋업** — active 프로젝트 decisions.md에 있는 실제 결정
  "record/remind 폐기 + context-save/resume/decisions 3 신규 스킬"을 뒤집는 diff를 만든다:
  hamstern-plugin repo에서 `skills/record/SKILL.md`를 stub로 생성(`# record\n캡처 진입점.` 등) →
  이게 "record 폐기" 결정을 번복하는 변경.
  Run: `git diff HEAD` 로 diff가 잡히는지 확인.

- [ ] **Step 2: guard 절차 수행** — SKILL.md 절차대로:
  `python3 skills/guard/parse_decisions.py`로 결정 JSON 획득 → diff + 결정목록으로 3
  서브에이전트 병렬 디스패치(변경 이유 숨김, 회의적 프롬프트) → 다수결 집계.
  **합격 기준:** "record/remind 폐기" 결정이 ≥2명에게 플래그되어 ⚠️ 리포트에 나타남.

- [ ] **Step 3: 음성 시나리오** — stub 삭제(`git checkout -- . ; rm -rf skills/record` 또는 stub만 제거)
  후, 무관한 사소 변경(예: README 오타 수정) diff로 절차 재수행 →
  **합격 기준:** "✅ 결정 충돌 없음" (또는 그 변경과 무관한 결정은 플래그 안 됨).

- [ ] **Step 4: 정리** — dogfood용 stub/임시 변경 모두 제거. `git status`가 깨끗한지 확인.

- [ ] **Step 5: 커밋 없음** (실행 검증 단계)

---

## 합격 기준 (Definition of Done)

- [ ] `parse_decisions(text)`가 표준 줄을 {n, category, text, reason, session}로 파싱 (괄호 포함 텍스트·이유 분리, 마커/이유 없는 줄, 빈 입력) — pytest 6개 통과
- [ ] `parse_decisions.py` main이 active 프로젝트 decisions.md를 번호매긴 JSON으로 출력
- [ ] `SKILL.md`: git diff HEAD 수집(빈 종료) → 파싱(빈 종료) → 3 서브에이전트 병렬(변경 이유 숨김·회의적) → ≥2 다수결 → loud 리포트(supersede/revert 두 출구) / ✅
- [ ] read-only (decisions.md 미수정)
- [ ] marketplace.json 등록 + 1.6.0
- [ ] dogfood: 번복 diff(record 부활)→플래그, 무관 diff→clean
