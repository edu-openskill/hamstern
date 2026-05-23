# Hamstern Plugin Cleanup — Sub-project A

**Date:** 2026-05-23
**Status:** Approved design, ready for plan
**Sub-project:** A (of A+B). B = 멀티 플랫폼 도달성 — 별도 디자인 세션으로 진행.

## 목표

현재 플러그인에서 (a) cmux 의존·언급을 전부 제거하고, (b) 중복·orphan 코드를 정리하며, (c) 대시보드의 `baby → mom → boss → /hams:remind` 핸드오프 흐름이 실제로 끊김 없이 동작함을 검증한다.

## 원칙 (Scope rules)

- **프로젝트 스코프 고정** — 모든 hook 동작과 `.hamstern/` 디렉토리는 프로젝트 내부에만 존재. 글로벌 영역 (`~/.hamstern/`, `~/.claude/hams-diary.json`) 은 이번 정리에서 손대지 않는다 — 별도 검토.
- **외부 도구 양보 메커니즘 제거** — cmux 가 macOS 전용이고 사용 안 하므로 `.app-running` 기반 양보 로직 자체를 삭제. 마커 이름 일반화도 안 한다 (필요해지면 재도입).
- **삭제 우선** — 와이어업 약속이 이행 안 된 orphan 코드는 삭제 (`migrate_claude_md.py`, `dashboard.sh`).
- **세션 핸드오프 무결성** — 정리 후에도 `baby → mom → boss → /hams:remind` 핸드오프 경로가 그대로 동작해야 함. 이것이 Sub-project B 의 전제 조건.

## 비범위 (Out of scope)

- 룰 시스템 (`why` / `rule`) 의 통합·리팩토링
- diary 스킬의 accumulated complexity
- 멀티 플랫폼 도달성 (→ Sub-project B)
- 글로벌 영역 (`~/.hamstern/`)
- 새로운 기능 추가

## 아키텍처 변화

### Before

```
hooks/user_prompt.py    ─┐
                          ├─ is_app_running() [cmux 양보]   ← 중복
hooks/stop.py           ─┘  is_deeptalk_running()           ← 중복

skills/dashboard/
  ├ dashboard.sh        ← cmux 바이너리 호출 (죽은 코드, SKILL.md 가 안내 안 함)
  ├ server.py           ← 실제 사용되는 진입점
  └ SKILL.md            ← server.py 안내

hooks/migrate_claude_md.py  ← orphan (호출처 없음)
```

### After

```
hooks/_gate.py
  ├ is_hamstern_project()     ← 기존
  ├ is_noise_command()        ← 기존
  └ is_deeptalk_running()     ← 신규 (양쪽에서 import)

hooks/user_prompt.py     ─ from _gate import is_deeptalk_running  (slim)
hooks/stop.py            ─ from _gate import is_deeptalk_running  (slim)

skills/dashboard/
  ├ server.py
  └ SKILL.md             (cmux/dashboard.sh 언급 제거)

(삭제됨)
  ├ skills/dashboard/dashboard.sh
  ├ hooks/migrate_claude_md.py
  └ hooks/test_migrate_claude_md.py
```

## 변경 목록 (6 tasks)

### Task 1 — cmux 잔재 제거

| 파일 | 변경 |
|------|------|
| `hooks/user_prompt.py` | `is_app_running()` 함수 + `.app-running` 마커 체크 분기 제거. `is_deeptalk_running()` 만 남김 |
| `hooks/stop.py` | 동일 — `is_app_running()` 제거, `is_deeptalk_running()` 만 남김 |
| `hooks/test_baby_record.py` | `test_user_prompt_skipped_when_app_running` 케이스 삭제 |
| `README.md` | 50–57 줄 "cmux 툴 (macOS) 과의 공존" 섹션 통째로 삭제, 473 줄 changelog 의 cmux 언급 정정 |
| `skills/audit-decisions/SKILL.md` | 72–75 줄 "HTTPDashboardServer는 구현되었으나... cmux dashboard 미등록" 항목 제거 (현재 server.py 가 동작 중이므로 오정보) |
| `skills/dashboard/SKILL.md` | 41 줄 "Stop hook이 cmux/deeptalk 활성으로 bail했거나" → "Stop hook이 deeptalk 활성으로 bail했거나" |

### Task 2 — `dashboard.sh` 삭제

- `skills/dashboard/dashboard.sh` 단일 파일 삭제
- 어디서도 참조 안 함 — SKILL.md 도 `server.py` 직접 호출만 안내
- 마켓플레이스/manifest 영향 없음

### Task 3 — hooks 중복 로직 → `_gate.py` 통합

`hooks/_gate.py` 에 신규 추가:

```python
def is_deeptalk_running(cwd: str) -> bool:
    """`.deeptalk-running` 마커가 있고 24시간 이내면 True. stale이면 자동 삭제."""
    flag = Path(cwd) / ".hamstern" / ".deeptalk-running"
    if not flag.exists():
        return False
    if time.time() - flag.stat().st_mtime > 24 * 3600:
        flag.unlink(missing_ok=True)
        return False
    return True
```

- `user_prompt.py` / `stop.py` 양쪽이 `from _gate import is_deeptalk_running` 으로 단일 import
- 양쪽에서 stale-cleanup 동작이 달랐던 버그 (`user_prompt.py` 만 삭제했고 `stop.py` 는 안 했음) 자연 해소

### Task 4 — `migrate_claude_md.py` 삭제

삭제 대상:
- `hooks/migrate_claude_md.py`
- `hooks/test_migrate_claude_md.py`

사용자 안내 — README 의 "기존 사용자 마이그레이션" 항목 (464 줄 근방) 을 한 줄로 대체: "이미 마이그레이션 안 된 사용자는 CLAUDE.md 의 `<!-- hamstern:decisions:start --> ... <!-- hamstern:decisions:end -->` 블록을 수동 삭제".

### Task 5 — `audit-decisions/SKILL.md` 정합성 정정

72–75 줄의 옛 메모 ("HTTPDashboardServer는 구현되었으나 아직 작동하지 않음 - cmux dashboard 커맨드 미등록") 제거. 현재 `dashboard/server.py` 가 정식 진입점이고 SKILL.md 도 그렇게 안내하므로, 이 메모는 사용자에게 오정보. 제거하고 그 자리에 "결정사항 확정은 `/hams:dashboard` 사용" 한 줄로 대체.

### Task 6 — 대시보드 작동 검증 (Manual + Smoke)

실제 실행으로 확인할 6단계:

1. **포트 충돌 없는 상태에서 서버 기동** — `python3 skills/dashboard/server.py --port 7777 --project {cwd}` 실행, 5초 내 listening 확인
2. **브라우저 라우트 응답** — `GET /`, `GET /api/baby`, `GET /api/mom`, `GET /api/decisions` 4개 엔드포인트 200 응답 확인 (`curl` 또는 PowerShell `Invoke-WebRequest`)
3. **baby 파일 인식** — 테스트용 `.hamstern/baby-hamster/session_TEST.md` 1개 만들고 대시보드에 보이는지
4. **mom 집계 트리거** — `scripts/aggregate.py` 직접 실행해서 `mom-hamster/mom.md` 생성 확인
5. **decisions.md 확정 경로** — UI 에서 ✅ 한 항목이 `boss-hamster/decisions.md` 에 기록되는지
6. **`/hams:remind` 환기 경로** — `decisions.md` 가 출력으로 흘러나오는지

각 단계 결과를 `docs/plans/2026-05-23-cleanup-verification.md` 같은 노트에 체크리스트로 남김. 실패 항목은 후속 task 로 분리.

> 주의: 실제 API 엔드포인트 이름은 `server.py` 를 읽고 확인 — 위 라우트 경로는 추정. 첫 검증 단계에서 server.py 의 실제 라우트를 먼저 확인하고 위 시나리오를 보정.

## 테스트 & 검증 계획

### 자동 테스트

| 테스트 파일 | 조치 |
|------------|------|
| `hooks/test_gate.py` | `is_deeptalk_running()` 케이스 추가 (마커 없음 / 있음 / 24h 초과 stale 자동 삭제) |
| `hooks/test_baby_record.py` | `test_user_prompt_skipped_when_app_running` 삭제. `test_user_prompt_skipped_when_deeptalk_running` 케이스로 대체·강화 |
| `hooks/test_all_hooks_gated.py` | cmux 시나리오 ("`.app-running` 마커 있으면 silent exit") 케이스 삭제 |
| `hooks/test_migrate_claude_md.py` | 파일 통째로 삭제 |

전체 자동 테스트 실행 게이트 — 정리 완료 후 `python -m pytest hooks/` 그린 확인. 빨간 케이스 0개가 Task 5 → 6 진행 조건.

### Manual 검증

Task 6 의 6단계 — `docs/plans/2026-05-23-cleanup-verification.md` 에 체크리스트로 남기고, 실패 항목은 후속 task 분리.

## 위험 & 롤백

| 위험 | 가능성 | 영향 | 완화책 |
|------|--------|------|--------|
| cmux 사용자가 존재해 `.app-running` 양보가 깨짐 | 0% — cmux 는 macOS 전용, 사용자 환경은 Windows | — | 해당 없음 |
| `migrate_claude_md.py` 삭제 후 옛 사용자의 CLAUDE.md 잔존 마커 | 낮음 (1개월+ 경과) | 시각적 노이즈만, 기능 영향 없음 | README 에 수동 삭제 안내 한 줄 |
| `_gate.py` 통합 후 import 경로 오타로 hook 침묵 실패 | 낮음 | hook 무동작 | `test_gate.py` + `test_baby_record.py` 가 import 통째로 검증 |
| 대시보드 검증 중 server.py 의 Windows 미지원 발견 | 중간 | A 의 Task 6 실패 | 발견 즉시 후속 task 로 분리 (A 의 범위는 "검증" 까지 — 미발견 버그 수정은 별건) |
| 대시보드 검증 중 mom→decisions 흐름 끊김 발견 | 중간 | 동일 | 동일 — 발견 → 별건 task |

**롤백** — 작업이 모두 git commit 으로 진행되므로 문제 발견 시 commit 단위 revert. 한 작업 = 한 commit 권장 (Task 1 은 파일 수가 많으니 "1a. 코드/테스트" + "1b. 문서" 두 commit 로 분리 가능).

## 완료 조건 (Definition of Done)

- [ ] Task 1–5: 모든 파일 변경 commit, `pytest hooks/` 그린
- [ ] Task 6: 6단계 manual 검증 모두 통과 또는 실패 항목이 후속 task 로 등록
- [ ] `grep -ri "cmux\|app-running" hamstern-plugin/` 결과 0 건 (단, `docs/superpowers/specs/` 안의 이 디자인 문서와 README 의 changelog 과거 기록은 history 로 유지 — grep 시 제외)
- [ ] README 의 잘못된 안내 (cmux 공존 섹션, migrate 와이어업 약속) 모두 정정 완료

## 다음 단계

Sub-project A 완료 후 → Sub-project B (멀티 플랫폼 도달성) 를 별도 brainstorming 세션으로 시작. B 는 Anthropic 공식 docs 조사 (Claude Desktop App / Mobile App / Web 에서 hook·plugin 지원 여부) 가 선행되어야 디자인 가능.
