# Record Unification Verification — 2026-05-23

> Sub-project C (`docs/discussions/2026-05-23-record-unification-design.md`) 의 Task 11 검증 결과.
> 환경: Windows 11 / PowerShell / Python 3.x

## 검증 상태: 슬래시 명령 시나리오는 사용자 실행 보류

`/hams:record` 는 슬래시 명령이라 자동화 세션 안에서는 트리거 안 됨. 시나리오 1-7 은 사용자가 새 Claude Code CLI 세션에서 첫 사용 시 수행하고 결과를 아래 표에 갱신.

## 사전 준비 (마이그레이션 시나리오 fixture)

```powershell
$VERIFY_DIR = "$env:TEMP\record-unif-verify-$(Get-Random)"
New-Item -ItemType Directory -Path "$VERIFY_DIR\.hamstern\baby-hamster" -Force | Out-Null
New-Item -ItemType Directory -Path "$VERIFY_DIR\.hamstern\mom-hamster" -Force | Out-Null
New-Item -ItemType Directory -Path "$VERIFY_DIR\.hamstern\boss-hamster" -Force | Out-Null
"old session 1" | Out-File -Encoding utf8 "$VERIFY_DIR\.hamstern\baby-hamster\session_old.md"
"# 프로젝트 결정사항`n## Architecture`n- old <!-- session: old -->`n" | Out-File -Encoding utf8 "$VERIFY_DIR\.hamstern\boss-hamster\decisions.md"
"# Decisions Log`n" | Out-File -Encoding utf8 "$VERIFY_DIR\.hamstern\boss-hamster\decisions-log.md"
"mom aggregate" | Out-File -Encoding utf8 "$VERIFY_DIR\.hamstern\mom-hamster\mom.md"
cd $VERIFY_DIR
git init -q
git add -A; git commit -qm "init with old structure"
$VERIFY_DIR | Out-File -Encoding utf8 "$env:TEMP\verify_dir.txt"
"VERIFY_DIR=$VERIFY_DIR"
```

## 시나리오 결과

| # | 시나리오 | 결과 | 비고 |
|---|----------|------|------|
| 1 | 신규 프로젝트에서 record 첫 호출 → sessions/{id}.md + decisions.md 자동 생성 | 보류 | 빈 디렉토리에서 첫 호출 |
| 2 | 옛 구조 디렉토리에서 record 첫 호출 → 자동 마이그레이션 + `.hamstern.bak.{ts}/` 백업 | 보류 | $VERIFY_DIR 에서 시도 |
| 3 | 같은 세션 두 번째 record → sessions/{id}.md 갱신 (in-place), decisions.md append + dedup | 보류 | 추가 결정 후 재호출 |
| 4 | `/hams:remind` → 새 path 의 decisions.md 정상 환기 | 보류 | record 후 호출 |
| 5 | `/hams:audit-decisions` → 새 path 정상 동작 (sessions/*.md + decisions.md 읽기) | 보류 | audit.sh 의 SESSIONS_DIR 변수 사용 확인 |
| 6 | `/hams:dashboard` → 새 path 의 sessions/decisions 정상 표시, × 결정 제거 작동 | 보류 | server.py 실행 후 브라우저 |
| 7 | FS 쓰기 차단 시 텍스트 폴백 (Desktop sandbox 시뮬레이션) | 보류 | `Set-Acl` 로 차단 후 호출 |

## 사전 사실 (이미 인라인 검증된 항목)

- ✅ pytest 10/10 PASS (`skills/record/test_record_format.py` — 기존 6 + 신규 4: write_session + migrate_old_to_new) — Task 10
- ✅ `.claude-plugin/marketplace.json` 13 → 11 (start/stop 제거, record 유지) — Task 10
- ✅ 디렉토리 삭제 확인: `hooks/`, `skills/start/`, `skills/stop/`, `skills/dashboard/scripts/aggregate.py` 전부 GONE — Task 10
- ✅ 활성 코드·문서의 옛 구조 (baby/mom/boss-hamster, deeptalk-running, /hams:start, /hams:stop) 참조 0건 (README changelog + record migration 로직 의도된 residual만) — Task 10
- ✅ server.py 컴파일 OK — Task 8
- ✅ `.claude/worktrees/` 는 `.gitignore` 처리되어 stray 워크트리들이 repo 오염시키지 않음

## 작업 과정 노트 (재현·디버깅용)

- Sub-C 실행 중 일부 subagent 가 worktree branch 에 commit 하고 main 에 안 들어가는 leakage 발생. Task 7 (remind + audit-decisions path) 의 commit 214720b 가 그 케이스. 후속 정리 commit (b4c970e) 으로 main 에 적용 + 누락된 prose mention (deeptalk:112, README:24, audit-decisions:13/55) 까지 sweep.
- 후속 sub-project 진행 시 subagent dispatch 후 작업이 main 에 실제 반영됐는지 `git log main -n 1` 확인 권장.

## 발견된 후속 작업

- (사용자 검증 시 실패 항목 발견되면 여기 기록)
- 시나리오 2 의 자동 마이그레이션이 실제 사용자 환경에서 백업 위치를 잘 만드는지 첫 확인 시 주목
- audit-decisions/SKILL.md 의 example 블록 (line 53-58 근방) 의 "record 가 양쪽에 쓰는데 sync 미정" 텍스트가 실제 spec 의도에 맞는지 추후 audit 시 재검토 가능

## 결론

Sub-C 의 모든 정적·회귀·구조 검증은 통과. 슬래시 명령 + 마이그레이션 실행 검증 (시나리오 1-7) 은 사용자 첫 사용 시점에 수행해 본 표에 결과 기록.
