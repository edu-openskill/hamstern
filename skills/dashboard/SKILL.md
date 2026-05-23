---
name: dashboard
description: Hamstern 대시보드 웹 UI 실행 — sessions + decisions 뷰어 + 결정사항 × 제거.
---

# /hams:dashboard

Hamstern 프로젝트 관리 대시보드를 웹 브라우저에서 엽니다. **결정사항 viewer + × 제거**가 주 역할입니다.

## 책임 분리

- **결정사항 viewer + toggle/remove** → 이 대시보드의 역할
- **결정사항 쓰기** → `/hams:record` 가 담당 (Sub-C 에서 단일 진입점으로 통일)
- **Sub-D 에서 github.io static + 브라우저 편집 UI 로 재설계 예정**

## 기능

- **Sessions** — `.hamstern/sessions/*.md` (record 가 작성한 세션 distill) 목록
- **Decisions** — 현재 확정된 결정사항 (`.hamstern/decisions.md`)
- **× 제거** — 개별 결정사항 삭제 (편집 endpoint)

## 동작 (Claude가 직접 실행)

```bash
/hams:dashboard [--port 7777]
```

Claude 실행 절차:
1. 포트 충돌 정리: `python3 -c "import subprocess; subprocess.run(['bash','-c','lsof -ti:7777 | xargs kill -9 2>/dev/null'], capture_output=True)"`
2. 서버 시작: `python3 skills/dashboard/server.py --port 7777 --project {cwd}`
3. 브라우저 오픈 (Windows): `start http://localhost:7777`

## 데이터

- `.hamstern/sessions/*.md` — 세션 기록 (record 가 작성)
- `.hamstern/decisions.md` — 확정 결정사항 (record 가 쓴 결정사항)
