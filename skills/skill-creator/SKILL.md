---
name: skill-creator
description: Use when the user just successfully completed a complex multi-step workflow (deploy/build/CI 설정/외부 서비스 연동/migration/fastlane/Play Store 업로드 등) — especially after 2-3 failed attempts — and wants it captured for reuse. Trigger phrases: "이걸 스킬로 만들어줘", "다음에도 쓰게 저장해", "또 설명하기 싫다", "save as skill", "make this reusable".
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# /hams:skill-creator

## Overview

Captures a workflow that just succeeded in the current session and writes it as a reusable SKILL.md to the **current project's** `./.claude/skills/<name>/`. Never touches the hams plugin itself. Failures from earlier attempts become the "Common Mistakes" section — that's the highest-value output.

## When to Use

다음 신호 중 하나라도 있으면 호출하세요.

- 사용자가 복잡한 절차(예: Android Play Store 업로드 + fastlane, GitHub Actions 새 워크플로, DB 마이그레이션, OAuth 클라이언트 등록, 외부 API 첫 연동)를 막 성공시킨 직후
- 사용자가 "다음번에는 이걸 자동으로 하고 싶다", "또 설명하기 귀찮다", "이거 스킬로 만들어줘" 같은 발화를 했을 때
- 세션에 명백한 "실패 → 재시도 → 최종 성공" 패턴이 보일 때 (가장 가치 있는 케이스)

호출하지 않을 때:
- 한 줄짜리 단순 작업 (typo 수정, 단일 파일 rename 등)
- 이미 잘 문서화되어 있는 표준 작업 (`git commit`, `npm install` 등)
- 다른 도구가 더 적합한 경우 (CLAUDE.md 항목, 단순 스크립트, alias)

## Workflow

호출 즉시 다음 단계를 순서대로 수행합니다.

### Step 1: 컨텍스트 추출

현재 세션의 다음 정보를 분석합니다.

- 사용자 발화 (최근 N턴 — 최소 워크플로 시작점부터)
- Claude가 호출한 도구 (Bash 명령어, 읽은/수정한 파일 경로, 실행한 스크립트)
- 발생한 오류와 그것을 어떻게 우회/수정했는지 (실패 경로)
- 최종적으로 통한 단계의 순서

워크플로 경계가 모호하면 사용자에게 한 번만 확인합니다 ("이 스킬은 X부터 Y까지 캡처하면 될까요?"). 명확하면 묻지 마세요.

성공 경로는 **Steps**로, 실패 경로는 **Common Mistakes**로 분리합니다.

### Step 2: 스킬 초안 생성 (메모리 내)

이 단계에서는 파일을 작성하지 않습니다. 다음 요소를 모두 갖춘 초안을 만듭니다.

**Frontmatter**
- `name`: kebab-case, 의도가 분명한 동사구. 예: `android-fastlane-deploy`, `bigquery-monthly-report`, `oauth-client-register`. snake_case·camelCase·공백 금지.
- `description`: 반드시 "Use when..."로 시작 (영어든 한국어 "...할 때 호출"이든 트리거 시그널 형태). 워크플로 요약 금지. 트리거가 되는 도구·파일·에러 메시지 키워드를 포함. 1024자 이하.
- `allowed-tools`: 워크플로 실행에 실제로 필요한 도구만.

**본문 섹션**
- `When to Use` — 이 스킬을 호출해야 할 신호. 증상·키워드·파일 패턴.
- `Required Inputs` — 다음번 호출 시 사용자가 알려줘야 할 값. 절대 하드코딩하지 않음. 예: bundle ID, service account JSON 경로, 대상 환경(staging/prod).
- `Steps` — 이번에 실제로 통한 순서. 명령어와 경로 그대로. 각 단계는 "왜 필요한지" 한 줄 설명 포함.
- `Common Mistakes` — 이번 세션에서 실패한 시도들 + 다음에 같은 함정을 피하는 방법. 가장 중요.
- (선택) `Verification` — 마지막에 성공을 확인하는 방법.

**금지사항** (자가 검토)
- description이 "이 스킬은 X를 한다" 식의 워크플로 요약 → 거부 후 트리거 형태로 재작성
- 절대 경로(`/Users/ssarm/...`), 개인 자격증명, 프로젝트별 ID를 본문에 하드코딩 → `Required Inputs`로 분리해 placeholder 처리
- 실패 흔적 무시 → Common Mistakes가 비어 있으면 "정말 실패가 없었는가?" 재검토

### Step 3: 미리보기 + 승인 (AskUserQuestion 1회)

사용자에게 초안 전체 텍스트를 보여준 뒤 `AskUserQuestion`으로 묻습니다.

옵션 3개:
1. **이대로 저장** — Step 4로 진행
2. **수정 사항 알려주기** — 사용자가 텍스트로 수정 지시 → Step 2로 복귀해 반영 → Step 3 재진행
3. **취소** — 종료. 아무것도 저장하지 않음.

승인 없이 파일을 절대 작성하지 않습니다.

### Step 4: 파일 작성 + 자가검증

1. 저장 경로 결정: `./.claude/skills/<name>/SKILL.md` (cwd 기준 상대 경로).
2. `./.claude/skills/<name>/` 디렉터리가 이미 존재하면:
   - 동일 이름 SKILL.md가 있는 경우 → 사용자에게 "덮어쓰기 / 새 이름(<name>-2) / 취소" 확인.
3. 디렉터리 생성 (`mkdir -p`).
4. SKILL.md 작성 (`Write` 도구 사용).
5. 자가검증:
   - frontmatter `name`이 `^[a-z][a-z0-9-]{0,63}$` 패턴인지
   - `description`이 "Use when" 또는 "...할 때 호출"로 시작하는지, 1024자 이하인지
   - 본문에 `Steps`와 `Common Mistakes` 섹션이 모두 있는지
   - 검증 실패 시 사용자에게 어떤 검증이 실패했는지 보고하고 작성한 파일 경로를 알려줌 (수동 수정 가능하도록)
6. 완료 메시지:
   ```
   ✅ 스킬 생성: ./.claude/skills/<name>/SKILL.md
   ▶ 새 세션에서 /<name> 또는 description 트리거로 자동 호출됩니다.
   ```

## Common Mistakes (skill-creator 자체)

- **세션 발화를 verbatim 복사** → "Use when" 시그널이 죽고 description이 워크플로 요약이 됨. 항상 트리거 조건으로 재진술.
- **하드코딩된 절대 경로/자격증명** → 다른 프로젝트나 다른 사용자에게 무용지물. `Required Inputs`로 분리.
- **실패 흔적을 버림** → 이 스킬의 가장 중요한 출력은 Common Mistakes. 실패가 없는 듯 보여도 다시 확인.
- **hams 플러그인 디렉터리에 작성 시도** → 절대 금지. `~/.claude/plugins/...` 경로에 어떤 파일도 만들지 않음. 결과물은 반드시 cwd의 `.claude/skills/`로.
- **승인 없이 작성** → 항상 Step 3 미리보기·승인 후 Step 4.
- **파일 작성 후 검증 누락** → frontmatter가 잘못되면 Claude Code가 스킬을 인식 못 함. 자가검증 필수.

## Out of Scope (YAGNI)

- 스킬용 자동 테스트 생성 (RED→GREEN→REFACTOR)
- 스킬 버전 관리·마이그레이션
- 글로벌(`~/.claude/skills/`) 저장 옵션 — 현재는 프로젝트 로컬 고정
- 자동 git commit — 사용자가 명시적으로 결정
- 다른 프로젝트의 `.claude/skills/`를 읽어 중복 검사
