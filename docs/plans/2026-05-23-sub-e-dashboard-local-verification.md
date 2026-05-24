# Sub-project E — Dashboard Per-Project Local Serve Verification

**Date:** 2026-05-24 (auto test 결과 / 수동 UAT 는 사용자 다음 세션에서 갱신)
**Plan:** `2026-05-23-sub-e-dashboard-local-plan.md`
**Spec:** `2026-05-23-sub-e-dashboard-local-design.md`

## 자동 테스트

| 테스트 | 케이스 수 | 결과 |
|---|---|---|
| `skills/dashboard/test_build.py` (Sub-D 회귀) | 6 | ✅ |
| `skills/dashboard/test_serve.py` (Sub-E 신규) | 9 | ✅ |
| `skills/audit-decisions/test_remove.py` (Sub-D 회귀) | 5 | ✅ |
| `skills/record/test_record_format.py` (Sub-C 회귀) | 10 | ✅ |
| **합계** | **30** | ✅ 30 passed in 0.44s |

명령: `python3 -m pytest skills/ -v`

## 배포

| 항목 | 상태 |
|---|---|
| Sub-E 13 commits (refactor + Block A 9 + Block B 1 + Block C 1 + final fixes 1) | ✅ push 완료 (origin/main = f838616) |
| Plugin cache (`~/.claude/plugins/cache/hamstern/hams/b1146da6b548/`) | ✅ Sub-E dev tree 로 갱신 (이전 cache 는 `.bak-pre-sub-e` 로 백업) |

## 수동 UAT (다음 세션에서 사용자 진행)

⚠️ **현 세션에서는 검증 불가** — Claude 세션의 plugin cache 가 시작 시점에 로드돼 있어 cache 갱신이 자동 반영 안 됨. 사용자가 **Claude 세션 재시작 후** 진행.

### 시나리오 1 — 빈 프로젝트 (`.hamstern/` 없음) 에서 local 모드
- [ ] 새 디렉터리 (예: `/tmp/test-empty-e`) 에서 `/hams:dashboard` 호출
- [ ] `.hamstern/dashboard-data/manifest.json` 생성 (`decisions: false`, `sessions: []`)
- [ ] 서버 background 기동 + URL 출력 (`http://localhost:<dynamic_port>/`)
- [ ] 브라우저: "결정사항 없음 / 세션 없음 / 로그 없음" fallback

### 시나리오 2 — 실데이터 프로젝트
- [ ] `hamstern-plugin` 자체 또는 다른 프로젝트에서 `/hams:record` 한두 번 호출 → 결정사항 저장
- [ ] `/hams:dashboard`
- [ ] 브라우저: decisions/sessions/log 모두 렌더
- [ ] `[×]` 클릭 → 클립보드에 정확한 `/hams:audit-decisions remove "..."`

### 시나리오 3 — Idempotent restart
- [ ] 같은 프로젝트에서 `/hams:dashboard` 두 번 호출
- [ ] 두 번째 호출 시 이전 PID kill → 새 PID + 새 포트 + 새 URL
- [ ] `.hamstern/dashboard.pid` 가 새 PID 로 덮어쓰기

### 시나리오 4 — 멀티-프로젝트 공존
- [ ] 두 다른 프로젝트에서 각각 `/hams:dashboard`
- [ ] 각자 다른 동적 포트, 두 브라우저 탭 동시 동작
- [ ] 한쪽 종료가 다른 쪽에 영향 없음

### 시나리오 5 — Publish 모드 회귀 (Sub-D 보존)
- [ ] `hamstern-plugin` 디렉터리에서 `/hams:dashboard --publish`
- [ ] `docs/data/` 번들 + (변경 있으면) commit + push
- [ ] `https://edu-openskill.github.io/hamstern/` 갱신된 데이터로 응답

### 시나리오 6 — Path traversal 차단
- [x] 자동 테스트 e2e 케이스 통과 (`test_e2e_http_server_serves_plugin_and_data`)
- [ ] 수동 검증: `curl -I "http://localhost:<port>/data/../../etc/passwd"` → HTTP 404

## 발견 사항

(UAT 중 발견한 이슈 기록 — 예: SKILL.md 의 bash idiom 이 Windows raw PowerShell 에서 실행 안 됨, 좀비 PID 누적, …)

## 알려진 환경 제약

- **현 사용자 환경 (Windows 11)** — SKILL.md 의 모든 shell snippet 은 bash 문법. Claude 가 Bash tool 로 실행하므로 동작하나, 사용자가 직접 raw PowerShell 에서 실행하면 작동 안 함 (SKILL.md 의 Windows note 참조).
- **symlink** — 관리자 권한 또는 dev mode 필요. cache 갱신은 백업 + 복사 방식으로 진행됨.
- **$CLAUDE_PLUGIN_ROOT** — 현 환경에서 비어있어 glob fallback (`~/.claude/plugins/cache/hamstern/hams/*/`) 사용.

## 최종 commit 범위 (`f7328ea..f838616`)

```
f838616 docs: Sub-E final review fixes — line count + Windows note + browser fallback (Sub-E)
7179732 docs: README + conventions.md Sub-E updates (Sub-E)
64f0f8f docs(dashboard): rewrite SKILL.md for two modes (local default + --publish) (Sub-E)
5c6c7e7 refactor(dashboard): extract _route_path pure function (Sub-E)
06df063 test(dashboard): serve.py end-to-end HTTPServer integration (Sub-E)
0c72be5 feat(dashboard): serve.py CLI entry main() (Sub-E)
51ee8a4 feat(dashboard): serve.py pick_port helper (Sub-E)
bda9ca7 feat(dashboard): serve.py path traversal guard (Sub-E)
6e49bb4 feat(dashboard): serve.py /data/* routes to data_dir (Sub-E)
fcc9251 test(dashboard): serve.py /app.js + /style.css regression (Sub-E)
0651531 feat(dashboard): serve.py skeleton + root path test (Sub-E)
```

11 commits + 본 verification commit.

## Definition of Done

- [x] `serve.py` 작성 (≤ 100 줄 stdlib only — 실제 86 줄)
- [x] `test_serve.py` 9 케이스 그린
- [x] `SKILL.md` 두 모드 명세 재작성
- [x] Path traversal 차단 (자동 테스트 통과)
- [x] README + conventions 갱신
- [x] verification.md (본 문서)
- [ ] 수동 UAT 6 시나리오 — **다음 세션에서 사용자 진행**
- [ ] Plugin cache 정식 갱신 (Claude 자동 plugin update 메커니즘) — 현재는 manual 복사로 우회

## Sub-F 후보

- 멀티-프로젝트 aggregator (한 URL 에서 N개 프로젝트 합쳐 보기)
- Slack/Discord broadcast (MCP)
- 자동 reload (데이터 변경 감지 → 브라우저 새로고침)
- private project 의 publish (인증 토큰 기반)
