# Hamstern Plugin Conventions

> 모든 hamstern 스킬·hook 이 따르는 공통 규약. 신규 스킬 추가 시 이 문서를 먼저 읽고 따른다.

## 1. 표준 저장소 레이아웃

```
{project_root}/.hamstern/
  baby-hamster/         # 원본 턴 로그 (hook 자동 append, CLI 전용)
  mom-hamster/
    mom.md              # 세션별 baby 집계본 (Stop hook 자동 갱신)
  boss-hamster/
    decisions.md        # 현재 결정사항 (hot, 카테고리별)         ← record/dashboard 공동 쓰기
    decisions-log.md    # append-only 전체 이력 (cold)            ← record 가 append
{project_root}/.claude/rules/{topic}.md (+references/)  # 영구 룰 (자동 로드)
```

`{project_root}` = `git rev-parse --show-toplevel` 결과, 실패 시 `pwd`.

## 2. 경로 해석 의사코드

모든 스킬은 다음 두 함수를 본문 첫 단계에 호출한다 (의사코드 — Claude 가 Bash 도구로 실행):

```
resolve_root():
  try:
    r = $(git rev-parse --show-toplevel 2>/dev/null)
    if r is empty: r = $(pwd)
  except: r = $(pwd)
  return r

ensure_store(r):
  try:
    mkdir -p {r}/.hamstern/boss-hamster
    return OK
  except (no FS, EACCES, ENOENT, sandbox):
    return FALLBACK_TEXT

store_paths(r):
  return {
    decisions: {r}/.hamstern/boss-hamster/decisions.md,
    log:       {r}/.hamstern/boss-hamster/decisions-log.md,
    mom:       {r}/.hamstern/mom-hamster/mom.md
  }
```

## 3. 능력 프로브 패턴 (FS-try + Text-fallback)

환경 식별 변수 (`CLAUDE_CODE_REMOTE` 등) 에 **의존하지 않는다**. 대신 항상 FS 쓰기를 시도하고 실패 시 텍스트 폴백:

```
try:
  ensure_store(r)
  write decisions.md
  write decisions-log.md
on failure:
  output the same markdown to chat
  instruct user to paste into CLI session
```

이 패턴은 Claude Code CLI 에서는 FS 모드, Claude Desktop App sandbox 에서는 텍스트 폴백으로 자연스럽게 분기된다.

## 4. `decisions.md` 포맷

```markdown
# 프로젝트 결정사항

_마지막 업데이트: {ISO timestamp}_

## {카테고리: Architecture | Performance | UI | Testing | Deployment | Other}
- {결정 내용} (이유: {왜}) <!-- session: {id} -->

## 실패·폐기 (왜 안 했나)
- {시도 내용} → 폐기: {이유} <!-- session: {id} -->

## 열린 질문
- {미정 사항} <!-- session: {id} -->
```

규칙:
- 헤더 `# 프로젝트 결정사항` 은 고정
- `_마지막 업데이트: ...` 라인은 매 쓰기마다 갱신
- `## {카테고리}` 는 위 6개 + 특별 카테고리 (`실패·폐기`, `열린 질문`)
- 항목 끝의 `<!-- session: {id} -->` 마커로 idempotent 재호출 시 갱신 매칭
- 중복 판정: Jaccard 유사도 > 0.7 (dashboard 의 dedup 임계와 동일)

## 5. `decisions-log.md` 포맷 (append-only)

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

## 6. 진입점 분리 (P6)

| 진입점 | 성격 | 쓰기 대상 |
|--------|------|-----------|
| hook (`UserPromptSubmit`, `Stop`) | 자동 (CLI 전용), raw turn append | `baby-hamster/*.md`, `mom-hamster/mom.md` |
| `/hams:record` | 수동 (CLI + Desktop), distilled decision | `boss-hamster/decisions.md`, `decisions-log.md` |
| `/hams:dashboard` | 수동 (CLI), Opus 분석 + 사용자 핀 | `boss-hamster/decisions.md` |

세 진입점은 **서로 호출하지 않는다**. 같은 저장소 포맷만 공유.
