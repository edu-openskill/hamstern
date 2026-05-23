# Hamstern Plugin Conventions

> 모든 hamstern 스킬·hook 이 따르는 공통 규약. 신규 스킬 추가 시 이 문서를 먼저 읽고 따른다.

## 1. 표준 저장소 레이아웃

```
{project_root}/.hamstern/
  sessions/{session_id}.md   # 세션별 distill (결정 + 실패·폐기 + 열린 질문)  ← record 가 작성
  decisions.md               # 현재 결정사항 (카테고리별, hot)                ← record 가 append
  decisions-log.md           # append-only 전체 이력 (cold)                  ← record 가 append
{project_root}/.claude/rules/{topic}.md (+references/)  # 영구 룰 (자동 로드)
```

`{project_root}` = `git rev-parse --show-toplevel` 결과, 실패 시 `pwd`.

> 옛 3-tier 구조 (`baby-hamster/`, `mom-hamster/`, `boss-hamster/`) 는 Sub-C 에서 제거됨. record 첫 호출 시 자동 마이그레이션 (`.hamstern.bak.{ts}/` 백업 후 새 구조로 mv).

## 2. 경로 해석 의사코드

모든 스킬은 다음 두 함수를 본문 첫 단계에 호출한다:

```
resolve_root():
  try:
    r = $(git rev-parse --show-toplevel 2>/dev/null)
    if r is empty: r = $(pwd)
  except: r = $(pwd)
  return r

ensure_store(r):
  try:
    mkdir -p {r}/.hamstern/sessions
    return OK
  except (no FS, EACCES, ENOENT, sandbox):
    return FALLBACK_TEXT

store_paths(r):
  return {
    sessions:  {r}/.hamstern/sessions/,
    decisions: {r}/.hamstern/decisions.md,
    log:       {r}/.hamstern/decisions-log.md
  }
```

## 3. 능력 프로브 패턴 (FS-try + Text-fallback)

환경 식별 변수 (`CLAUDE_CODE_REMOTE` 등) 에 **의존하지 않는다**. 항상 FS 쓰기를 시도하고 실패 시 텍스트 폴백:

```
try:
  ensure_store(r)
  write sessions/{id}.md
  write decisions.md
  write decisions-log.md
on failure:
  output the same markdown to chat
  instruct user to paste into CLI session
```

이 패턴은 Claude Code CLI 에서는 FS 모드, Claude Desktop App sandbox 에서는 텍스트 폴백으로 자연스럽게 분기된다.

## 4. `sessions/{session_id}.md` 포맷

```markdown
# Session {session_id}

_기록: {ISO timestamp}_

## 결정
- {결정 내용} (이유: {왜})

## 실패·폐기
- {시도 내용} → 폐기: {이유}

## 열린 질문
- {미정 사항}
```

규칙:
- 헤더 `# Session {id}` 고정, `_기록: ...` 라인은 매 record 호출마다 갱신
- 같은 session_id 로 재호출 시 in-place replace (append 아님 — 세션은 단일 distill)
- 빈 카테고리는 헤더만 남기거나 헤더도 생략 가능 (일관성만 유지)

## 5. `decisions.md` 포맷

```markdown
# 프로젝트 결정사항

_마지막 업데이트: {ISO timestamp}_

## {카테고리: Architecture | Performance | UI | Testing | Deployment | Other}
- {결정 내용} (이유: {왜}) <!-- session: {id} -->
```

규칙:
- 헤더 `# 프로젝트 결정사항` 고정
- `_마지막 업데이트: ...` 매 쓰기마다 갱신
- `## {카테고리}` 는 위 6개 중 하나
- 항목 끝 `<!-- session: {id} -->` 마커로 idempotent 재호출 시 갱신 매칭
- 중복 판정: Jaccard 유사도 > 0.7
- **실패·폐기와 열린 질문은 decisions.md 에 쓰지 않는다** — sessions/{id}.md 에만 보존. decisions.md 는 "현재 유효한 결정의 집합" 만.

## 6. `decisions-log.md` 포맷 (append-only)

```markdown
# Decisions Log
<!-- append-only. 수동 편집 금지. -->

## {YYYY-MM-DD HH:MM} · session {id}
+ [결정] {…}
+ [실패] {…}
+ [열림] {…}
```

규칙:
- 첫 줄 헤더는 파일 생성 시 한 번만
- 매 record 호출마다 `## {timestamp} · session {id}` 블록 1개 append
- 같은 session 재호출 시 새 블록을 append (decisions.md 와 달리 갱신 X — log 는 추적용)

## 7. 진입점 단일화 (Sub-C 이후)

| 진입점 | 역할 |
|--------|------|
| `/hams:record` | **유일한 capture 진입점**. sessions/{id}.md + decisions.md + decisions-log.md 에 atomic dual-write. |
| `/hams:remind` | 읽기 전용. `decisions.md` 를 현재 세션에 환기. |
| `/hams:audit-decisions` | 읽기 + 갱신. `decisions.md` 와 `sessions/*.md` 를 재검토하고 사용자 승인 시 `decisions.md` 갱신. |
| `/hams:dashboard` | UI. `sessions/*.md` + `decisions.md` 표시 + toggle/remove. Sub-D 에서 github.io static + 편집 UI 로 재설계. |

write 는 record 만, 다른 스킬은 reader 또는 reader+editor. hook 은 Sub-C 에서 제거됨 — 자동 캡쳐 없음.
