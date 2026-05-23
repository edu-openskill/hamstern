# Hamstern Plugin Cleanup Verification — 2026-05-23

> Sub-project A (`docs/discussions/2026-05-23-hamstern-cleanup-design.md`) 의 Task 8 검증 결과.
> 실행 환경: Windows 11 / PowerShell 5.1 / Python 3.x / 검증 디렉토리는 `%TEMP%\hamstern-verify-{random}`

## 검증 결과

| # | 항목 | 결과 | 비고 |
|---|------|------|------|
| 1 | 임시 디렉토리 + baby 더미 파일 생성 | ✅ | `.hamstern/{baby,mom,boss}-hamster/` + `session_TEST.md` 생성됨 |
| 2 | `server.py --port 7777` 기동 + listening | ✅ | `Start-Process -WindowStyle Hidden` background, `TcpTestSucceeded: True` |
| 3 | GET 5개 엔드포인트 → 200 | ✅ | `/`, `/api/baby`, `/api/mom`, `/api/decisions`, `/api/analyze/status` 모두 200 |
| 4 | /api/baby 가 session_TEST.md 인식 | ✅ | files.count=1, content 에 한글 "검증용 더미 prompt" 정확 포함 |
| 5 | `aggregate.py` → mom.md 생성 | ✅ | 408 bytes, `# Mom MD` 헤더 + session_TEST 본문 (한글 포함) 정상 통합 |
| 6 | POST /api/pin/boss → decisions.md 기록 | ✅* | 200, decisions.md 생성, Architecture 카테고리에 항목 추가. UTF-8 byte 직접 전송 시 한글 완전 보존 |
| 7 | decisions.md 가독 (`/hams:remind` 환기 본문) | ✅ | 헤더 + 카테고리 + 결정 항목 형태 정상, 사람이 읽기에 자연스러움 |
| 8 | 서버 종료 + 디렉토리 정리 | ✅ | PID stop + Remove-Item, 포트 7777 closed |

(*) Step 6 첫 시도에서 PowerShell `Invoke-WebRequest -Body (ConvertTo-Json)` 가 한글을 mojibake (`?? ?? ??`) 로 전송. UTF-8 byte 명시 (`[System.Text.Encoding]::UTF8.GetBytes`) 재시도 시 완벽 보존. **서버 측 버그 아님** — 검증 클라이언트 (PowerShell) 의 기본 인코딩 동작.

## 핸드오프 무결성 결론

`baby (.hamstern/baby-hamster/*.md) → mom (.hamstern/mom-hamster/mom.md) → boss (.hamstern/boss-hamster/decisions.md) → /hams:remind 가 읽을 본문` 의 전체 경로가 끊김 없이 동작함을 확인. 한글 콘텐츠도 모든 단계에서 보존됨 (UTF-8 호환 클라이언트 사용 시).

## 발견된 후속 작업 (실패 아님 — 개선 후보)

1. **클라이언트 가이드 보강** — 한글 본문을 POST 할 때 `Invoke-WebRequest` 사용자가 자주 마주칠 mojibake 함정을 `/hams:dashboard` 사용 안내에 한 줄 추가하면 디버깅 시간 절약. 예: "외부 스크립트로 POST 시 `[System.Text.Encoding]::UTF8.GetBytes()` 로 명시 전송 권장". 우선순위 낮음 — 대시보드 자체 UI 는 브라우저(자동 UTF-8) 사용이라 영향 없음.

2. **(없음)** — 위 외에 핸드오프 경로 자체의 결함은 발견되지 않음.

## 정리 작업의 전반적 평가

- pytest: **18/18 PASS** (cleanup 전후 동일)
- repo-wide grep: 활성 코드·스킬·매니페스트에 `cmux` / `app-running` / `migrate_claude_md` 참조 **0건** (README changelog 의 과거 history 만 의도적으로 유지)
- 대시보드 핸드오프: 6단계 모두 ✅ (1개 후속 개선 후보, 차단 이슈 없음)

**Sub-project A 완료 — 정리된 플러그인은 cmux-free + 단일 진실 출처(`_gate.py`) + 검증된 baby→mom→boss 핸드오프 흐름 상태. Sub-project B (멀티 플랫폼 도달성) 진행 가능한 입력.**
