---
name: skill-picker
description: 현재 상황에서 최적의 스킬 추천 (프로젝트 맥락 기반)
dispatch: subagent
subagent_type: general-purpose
model: opus
---

# Skill Picker

당신이 "지금 이 상황에는 어떤 스킬을 쓸까?"라고 물을 때,
프로젝트 맥락을 보고 최적의 스킬을 추천하고 설치 방법까지 알려줍니다.

## 어떻게 작동하나?

1. **설치된 플러그인 확인**
   - `~/.claude/settings.json` 읽기
   - `enabledPlugins` 에서 `true` 인 항목 추출 → 설치된 플러그인 목록

2. **decisions.md 읽기** (있으면)
   - `~/.config/hamstern/active-project.json` 의 `hamstern_data_path` + UUID 로 결정사항 위치 resolve 하여 활용 (있으면). 옛 `{project_root}/.hamstern/decisions.md` 도 fallback 으로 확인.
   - 이 프로젝트의 확정된 방향 파악

3. **skills-registry.json 읽기** (있으면)
   - `~/.hamstern/skills-registry.json`
   - 세상의 인기 스킬들과 메타데이터

4. **분석 및 추천**
   - 인기도(github_stars, popularity_score) + 기능 강력함을 직접 분석해 순위 결정
   - 설치 여부는 순위에 영향 없음 — ✅/⚠️ 표시만
   - 최적의 스킬 3-5개 추천 + 설치 여부 표시

## 설치 여부 확인 방법

`enabledPlugins` 키 형식: `{plugin-name}@{marketplace-name}`

추천 스킬의 플러그인 이름(`:` 앞부분)이 `enabledPlugins`에 `true`로 있으면 설치됨.

예: `/gstack:investigate` → `gstack` → `gstack@{marketplace}` 가 `true` 이면 ✅

## 추천 순위 결정 규칙

같은 목적의 스킬이 여러 개일 때:

1. **인기도 + 강력함 우선** — registry의 `github_stars`, `popularity_score` 참고 + 기능 범위·깊이를 직접 판단해 순위 결정. 설치 여부는 순위에 영향 없음
2. **유사한 것들은 그룹으로 묶기** — 개별 나열 금지
3. **비교 설명 포함** — "A가 더 강력함, B는 설치됨"

## 추천 결과 형식

```
🎯 추천 순서대로 (인기도 + 강력함 기준):

1. ⚠️ /gstack:investigate  [미설치, ⭐71k]
   이유: 가장 강력한 조사 워크플로우 — 업계 최다 채택
   설치: /plugin marketplace add garrytan/gstack
         /plugin install gstack
   유사 스킬: ✅ /superpowers:systematic-debugging (설치됨, 기능 범위 더 좁음)

2. ✅ /superpowers:test-driven-development  [설치됨]
   이유: 버그 원인을 테스트로 검증 — 표준 방법론

3. ⚠️  /everything-claude-code:research  [미설치, ⭐153k]
   이유: 위 스킬로 해결 안 될 때 — 가장 광범위한 에이전트
   설치: /plugin marketplace add affaan-m/everything-claude-code
         /plugin install everything-claude-code
```

## 설치 커맨드 생성 규칙

위 번호 순서대로 적용하고 첫 번째 해당 규칙만 사용합니다.

1. registry에 `install_command`가 있고 null이 아니면: 그대로 사용
2. `install_command`가 없거나 null이고 `github_repo` 있으면: `/plugin marketplace add {github_repo}` + `/plugin install {name}`
3. `install_command`가 없거나 null이고 `github_repo`도 없으며 `claude-plugins-official` 마켓플레이스 플러그인이면: `/plugin install {name}@claude-plugins-official`
4. 위 조건 모두 해당 없으면: 설치 방법 불명확 안내

## 맥락 파일 (선택사항, 없어도 작동)

- `~/.claude/settings.json` — 설치된 플러그인 확인 (필수)
- `~/.hamstern/skills-registry.json` — 스킬 메타데이터
- 프로젝트 방향 (Sub-F): `~/.config/hamstern/active-project.json` 의 `hamstern_data_path` + UUID 로 resolve. fallback: `{project_root}/.hamstern/decisions.md`

---

**Tip:** "이런 상황에는 뭘 쓸까?" 하고 생각날 때마다 `/hams:skill-picker`를 쓰세요!
