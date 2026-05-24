# Sub-project F — hamstern-data Repo Verification

**Date:** 2026-05-24 (수동 UAT 는 사용자 다음 세션에서 갱신)
**Plan:** `2026-05-24-sub-f-hamstern-data-repo-plan.md`
**Spec:** `2026-05-24-sub-f-hamstern-data-repo-design.md`

## 자동 테스트

| 테스트 | 케이스 수 | 결과 |
|---|---|---|
| `skills/dashboard/test_build.py` (6 기존 + 1 신규 multi-project) | 7 | ✅ |
| `skills/dashboard/test_serve.py` (9 기존 + 2 신규 routing) | 11 | ✅ |
| `skills/audit-decisions/test_remove.py` (5 기존 + 1 base_dir + 1 project-uuid) | 7 | ✅ |
| `skills/record/test_record_format.py` (Sub-C 회귀) | 10 | ✅ |
| **합계** | **35** | ✅ 35 passed |

## 배포

| 항목 | 상태 |
|---|---|
| Sub-F 17 commits (Block A-H + final fixes) | ✅ push 완료 (origin/main = f7d144c) |
| Plugin cache (`~/.claude/plugins/cache/hamstern/hams/b1146da6b548/`) | ✅ Sub-F dev tree 로 갱신 (이전 cache 는 `.bak-pre-sub-f` 로 백업) |
| 5 신규 skill 디렉터리 cache 반영 | ✅ init, link, save-mockup, migrate-project, rebuild-index |

## Sub-F 의 핵심 산출물

- **5 신규 skill**: `init`, `link`, `save-mockup`, `migrate-project`, `rebuild-index`
- **4 기존 수정**: `record`, `remind`, `dashboard`, `audit-decisions`
- **build.py multi-project**: `run_multiproject` + `run_single_project` 분리 + Sub-D/E 호환 `run` wrapper
- **serve.py**: 코드 변경 없음 — 기존 `_route_path` 가 `/data/p/{uuid}/...` 자연 지원, 테스트 2개 추가
- **docs/index.html** 메인 페이지 (프로젝트 목록 + 검색) 신설
- **docs/app.js** multi-project routing + mockups column
- **docs/p/_project.html** per-project view 템플릿
- **SKILL.md (dashboard)** 두 모드 모두 hamstern-data 경로 + per-UUID index.html 복사 로직
- **active-project.json** 디바이스별 active UUID 캐시
- **regex 수정**: SSH URL 도 지원 (`git@github.com:user/repo.git`)
- **clipboard --project-uuid**: dashboard `[×]` 클릭이 `/hams:audit-decisions remove "X" --project-uuid <uuid>` 발행, remove.py 가 active-project.json 으로 hamstern_data_path 자동 resolve

## 수동 UAT 11 시나리오 (다음 세션에서 사용자 진행)

⚠️ **현 세션에서 검증 불가** — Claude 세션의 plugin cache 가 시작 시점에 로드. Sub-F SKILL.md 가 즉시 반영 안 됨. 사용자가 Claude Code 재시작 후 진행.

### 시나리오 1 — 첫 셋업
- [ ] hamstern-data repo 없는 상태에서 `/hams:init "테스트"` → repo URL 입력 → clone + 프로젝트 scaffolding + active 바인딩 + commit·push

### 시나리오 2 — 첫 record·remind
- [ ] 같은 세션에서 `/hams:record` 두 번 → `projects/{uuid}/{decisions.md, sessions/*.md}` 생성 + push
- [ ] `/hams:remind` → decisions 전체 + 최근 2 sessions 표시
- [ ] `/hams:remind --deep` → sessions 5 까지

### 시나리오 3 — 두 번째 프로젝트
- [ ] `/hams:init "테스트 2"` → 자동 active 전환 + 새 UUID 디렉터리

### 시나리오 4 — 프로젝트 전환
- [ ] `/hams:link "테스트"` → 첫 프로젝트로 active 복귀
- [ ] `/hams:link "존재안함"` → 0건 매칭 + init 안내

### 시나리오 5 — mockup save
- [ ] HTML 파일 만든 후 `/hams:save-mockup "제목"` → 자동 탐지 + 복사 + URL 출력
- [ ] mockups/_index.json + projects/_index.json 의 mockup_count 갱신

### 시나리오 6 — dashboard local
- [ ] `/hams:dashboard` → 임시 dir build + background 서버 + 브라우저 메인 페이지 표시
- [ ] 메인 페이지에 두 프로젝트 카드 보임
- [ ] 프로젝트 카드 클릭 → 4-column (Sessions/Decisions/Mockups/Log) view
- [ ] 검색 input 으로 프로젝트 필터링 동작

### 시나리오 7 — dashboard publish
- [ ] `/hams:dashboard --publish` → hamstern-data/docs/data + per-UUID index.html 갱신 + push
- [ ] (1회성) Settings → Pages → main /docs 활성화
- [ ] `https://<owner>.github.io/hamstern-data/` 메인 페이지 응답
- [ ] `https://<owner>.github.io/hamstern-data/p/{uuid}/` per-project view 응답

### 시나리오 8 — 편집 흐름 (final fix 검증)
- [ ] dashboard 에서 결정사항 `[×]` 클릭
- [ ] 클립보드: `/hams:audit-decisions remove "<text>" --project-uuid <uuid>` (UUID 포함 확인)
- [ ] 붙여넣어 실행 → `.hamstern/decisions.md` 에서 해당 줄 제거 + log append (active-project.json 자동 resolve)
- [ ] 다음 `/hams:dashboard` 호출 시 viewer 에서 사라짐

### 시나리오 9 — migrate
- [ ] 기존 `.hamstern/` 가 있는 프로젝트에서 `/hams:migrate-project` → 자동 init + 파일 복사 + MIGRATED.md 보존
- [ ] `--delete-original` 옵션 → 원본 삭제 confirm

### 시나리오 10 — 멀티 디바이스 시뮬
- [ ] 같은 hamstern-data 를 다른 dir 에 clone
- [ ] 양쪽에서 `/hams:record` 후 push → 두 번째 push 가 충돌
- [ ] git pull --rebase + 수동 해결

### 시나리오 11 — rebuild-index
- [ ] `_index.json` 한 줄 수동 손상
- [ ] `/hams:rebuild-index` → 디렉터리 스캔 후 정상화

## 알려진 환경 제약

- **현 사용자 환경 (Windows 11)** — SKILL.md 의 bash 스크립트는 git-bash / Bash tool 로 실행. raw PowerShell 직접 실행은 작동 안 함.
- **uuidv7 fallback** — Python <3.13 일 때 manual fallback 은 strict UUIDv7 아님 (time-ordered shape 만 보장). Python 3.13+ (= 사용자 환경) 에서는 `uuid.uuid7()` 사용.
- **bash → Python `-c` 보간 escape** — `$NAME`, `$TITLE`, `$QUERY` 에 single quote 포함 시 Python 리터럴 깨질 가능성. 단일 사용자 + 명령 직접 입력 환경이라 실제 위험 낮음. 추후 hardening pass 에 stdin/argv 전달로 개선 가능.
- **active-project.json 스키마 drift** — 사용자가 직접 편집해서 필드 누락 시 Python traceback. `/hams:link` 다시 호출로 재생성.

## 최종 commit 범위 (`f02bf9b..f7d144c`)

17 commits:
- Block A (Tasks 1-3): init + link (2)
- Block B (Tasks 4-5): record + remind 갱신 (2)
- Block C (Tasks 6-7): save-mockup + audit-decisions update (2)
- Block D (Tasks 8-9): build.py multi-project + serve.py tests (2)
- Block E (Tasks 10-11): docs frontend + per-project template (2)
- Block F (Task 12): dashboard SKILL.md 갱신 (1)
- Block G (Tasks 13-14): migrate + rebuild (2)
- Block H (Task 15): marketplace + README + conventions (1)
- final fixes (clipboard --project-uuid + SSH URL regex): 1
- (+verification.md = 본 문서): 1

## Definition of Done

- [x] 5 신규 skill 작성
- [x] 4 기존 skill 수정
- [x] build.py multi-project + pytest
- [x] serve.py routing 테스트
- [x] docs/{index.html, p/_project.html, app.js, style.css} 갱신
- [x] active-project.json 스키마 + 로딩
- [x] marketplace.json 5 신규 등록
- [x] README Sub-F changelog + 셋업 가이드
- [x] docs/conventions.md git-as-DB 모델 + active-project.json 섹션
- [x] verification.md (본 문서)
- [x] 최종 fix: clipboard `--project-uuid` + SSH URL regex
- [ ] 수동 UAT 11 시나리오 — **다음 세션에서 사용자 진행**

## 다음 단계 (사용자 액션)

1. Claude Code 재시작 (현 세션 cache 가 stale)
2. GitHub 에 `hamstern-data` repo 생성 (private 권장)
3. `/hams:init "테스트"` 호출 → repo URL 입력 → 시나리오 1-11 차례로 검증
4. 발견 사항 verification.md 의 "발견 사항" 섹션에 추가 후 commit

## Sub-G+ 후보 (UAT 결과 따라)

- **hardening pass**: bash→Python 보간 stdin/argv 전환 + active-project.json validation
- **Hybrid Supabase index**: 결정사항 200+ 시점에 SQL 검색 layer (git source-of-truth 유지)
- **mockup 자동 thumbnail**: HTML → PNG 캡처 → dashboard 미리보기
- **모바일 PWA + write**: GitHub API direct write
- **자동 reload**: hamstern-data 변경 감지 → dashboard 새로고침
- **diary 메타 미러링**: diary 글 메타가 hamstern-data 의 통합 dashboard 에 노출 (Sub-D verification.md 의 발견 사항 반영)
