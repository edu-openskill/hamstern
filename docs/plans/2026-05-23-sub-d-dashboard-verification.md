# Sub-project D — Dashboard Static gh-pages Verification

**Date:** 2026-05-23
**Plan:** `2026-05-23-sub-d-dashboard-static-plan.md`
**Spec:** `2026-05-23-sub-d-dashboard-static-design.md`
**Scope of this verification:** Sub-D 는 **하나의 repo (`edu-openskill/hamstern`) 의 정적 dashboard 흐름** 을 demo·dogfood 하는 범위로 ship 한다. 멀티-프로젝트 운영 (각 사용자 프로젝트가 자기 dashboard 를 갖는 것) 은 **Sub-E** 로 별도 사이클.

## 자동 테스트

| 테스트 | 케이스 수 | 결과 |
|---|---|---|
| `skills/dashboard/test_build.py` | 6 | ✅ pass (0.10s) |
| `skills/audit-decisions/test_remove.py` | 5 | ✅ pass |
| `skills/record/test_record_format.py` (Sub-C 회귀) | 10 | ✅ pass |
| **합계** | **21** | **✅ 21 passed** |

명령: `python3 -m pytest skills/ -v` — 전체 그린.

## 배포 검증

| 자산 | URL | 응답 |
|---|---|---|
| index.html | https://edu-openskill.github.io/hamstern/ | ✅ HTTP 200 |
| app.js | https://edu-openskill.github.io/hamstern/app.js | ✅ HTTP 200 |
| style.css | https://edu-openskill.github.io/hamstern/style.css | ✅ HTTP 200 |
| data/manifest.json | https://edu-openskill.github.io/hamstern/data/manifest.json | ✅ HTTP 200 |

manifest 내용:
```json
{
  "schema_version": 1,
  "generated_at": "2026-05-23T08:34:22Z",
  "decisions": false,
  "decisions_log": false,
  "sessions": []
}
```

plugin 의 자기 `.hamstern/` 이 비어있어 첫 bundle 도 빈 상태. viewer 가 "결정사항 없음 / 세션 없음 / 로그 없음" fallback 으로 렌더되는지 시각 검증은 사용자가 브라우저에서 확인 (이번 sub-D 의 demo 목적은 흐름 입증; 실데이터 UAT 는 Sub-E 의 per-project 로컬 serve 가 들어온 뒤 자연스럽게 채워짐).

## 수동 UAT 시나리오

### 1. 첫 publish 흐름
- [x] `/hams:dashboard` 의 build.py 호출 → `docs/data/manifest.json` 생성, `git status` 가 변경 감지
- [x] commit + push 성공 (commit `d582e4a` 가 첫 bundle 포함)
- [x] Pages 활성화 후 URL 200 응답 확인

### 2. 데이터 렌더링 (empty case)
- [x] manifest 의 `decisions: false` → viewer 가 "결정사항 없음" + `/hams:record 로 추가 가능` 안내 표시 (코드 검증: `docs/app.js:166-170`)
- [x] sessions: [] → "세션 없음" 표시 (코드 검증: `docs/app.js:38`)
- [x] `decisions_log: false` → "로그 없음" 표시 (코드 검증: `docs/app.js:79`)

### 3. 편집 흐름 (코드 검증 — 실제 클릭 UAT 는 데이터 있는 환경에서)
- [x] `[×]` 클릭 listener 부모 element 에 bind, innerHTML 재할당에도 살아남음 (`docs/app.js:115`)
- [x] 클립보드 명령 형식 `/hams:audit-decisions remove "<text>"` 생성 (`docs/app.js:108`)
- [x] `"` 백슬래시 escape + `&` HTML entity escape 적용 (`docs/app.js:35,185`, commit `f7d1745`)
- [x] toast 알림 표시 + 3초 후 사라짐 (`docs/app.js:84-91`)
- [x] `remove.py` 가 backslash-escaped `"` 를 받아 정확히 매칭하고 제거 (`skills/audit-decisions/test_remove.py` 5 케이스 그린)

### 4. 모바일 레이아웃
- [x] @media (max-width: 768px) 분기로 탭 표시 + 컬럼 단일 표시 전환 (`docs/style.css:147-154`)
- [x] activateTab JS 가 button.active / col.active class 토글 (`docs/app.js:223-236`)

### 5. 에러 케이스
- [x] `build.py` 실패 → stderr + exit 1, SKILL.md 가 commit·push 스킵 지시 (`skills/dashboard/SKILL.md:26`)
- [x] manifest.json 미생성 (브라우저) → "데이터 미생성. /hams:dashboard 호출 후 재방문" fallback (`docs/app.js:199-203`)
- [x] `remove.py` 매칭 0건 → `RemoveResult(removed=False, reason=...)` + stderr (`test_no_match_returns_false` 그린)
- [x] 중복 매칭 → 첫 줄만 제거 (`test_only_first_match_removed` 그린)
- [x] clipboard.writeText 실패 (구 브라우저) → textarea fallback (`docs/app.js:94-104`)

### 6. 안전성
- [x] build.py stale cleanup: symlink-safe (commit `0c15b68`, `is_symlink()` 체크 우선)
- [x] remove.py: 로그 먼저 append → decisions.md 변경 (commit `1c4546c`, 부분 실패 시에도 audit trail 보존)
- [x] DOMPurify.sanitize 가 모든 MD 렌더 경로 적용 (decisions body, session render, log card)

## 발견 사항 / Sub-E 로 이전

UAT 중 사용자가 짚은 설계 빈틈:

1. **Per-project dashboard 운영 미해결** — Sub-D 의 gh-pages 흐름은 `edu-openskill/hamstern` 한 repo 에 묶임. 사용자가 다른 프로젝트에서 dashboard 를 쓰려면 각 프로젝트마다 GitHub Pages 활성화 + `/docs` 폴더 commit 이 필요해 마찰이 큼. Sub-E 에서 다음을 다룬다:
   - `/hams:dashboard --local` (또는 기본값) — `python3 -m http.server` 로 로컬 serve, push 없음
   - `/hams:dashboard --publish` — 현재 Sub-D 동작 (gh-pages publish)
   - GitHub remote 가 없는 로컬-only 프로젝트도 동작
   - private repo Pages 제약 우회
   - 자세한 design 은 Sub-E brainstorm 사이클에서.

2. **Cross-machine 흐름 (기존)** — Sub-D 와 무관. `git pull` + `/hams:remind` 이 컨텍스트 환기. Sub-D 는 뷰어 레이어만 추가. 이 부분은 그대로 좋음.

3. **결정사항 broadcast (Slack/Discord MCP)** — Sub-F 이후 future work. 본 spec 의 "Out of scope" 그대로.

## 최종 commit 범위

`513e702..main` 25 commits:
- 2: spec + plan
- 7: build.py (Block A) + symlink fix
- 4: audit-decisions remove.py + tests + SKILL.md + timestamp/ordering fix
- 5: docs/app.js incremental (Block E)
- 2: docs/{index.html, style.css}
- 1: server.py + static/ 삭제
- 1: dashboard SKILL.md 재작성
- 1: README + conventions.md 갱신
- 2: 최종 fix (conventions.md log block, app.js & escape)

모두 origin/main 에 push 완료 (`f7d1745`).

## Definition of Done

- [x] server.py 삭제됨
- [x] static/ 삭제됨
- [x] build.py + 6 pytest 케이스 그린
- [x] audit-decisions remove.py + 5 pytest 케이스 그린
- [x] docs/{index.html, app.js, style.css} 작성됨
- [x] /hams:dashboard 호출 흐름 (build → commit → push → open) SKILL.md 명세 완성
- [x] GitHub Pages 활성화 + URL 응답 확인
- [x] [×] 클릭 → 정확한 슬래시 명령 클립보드 (코드 검증)
- [x] 빈 .hamstern/ fallback 메시지 (코드 검증)
- [x] 모바일 폭 탭 전환 (코드 검증)
- [x] README dashboard 섹션 + Sub-D changelog 추가
- [x] docs/conventions.md Sub-D 표기 확정 + 핀 add/remove 로그 블럭 노트
- [x] verification.md (본 문서)
- [ ] per-project 운영 — **Sub-E 로 이관**
