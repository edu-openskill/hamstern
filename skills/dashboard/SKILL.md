---
name: dashboard
description: Hamstern 대시보드 웹 UI 실행 — mom MD를 Opus로 분석해 결정사항 후보 추출 + 2단계 핀으로 decisions.md 확정. mom 집계는 Stop hook이 세션 종료 시 자동 수행.
---

# /hams:dashboard

Hamstern 프로젝트 관리 대시보드를 웹 브라우저에서 엽니다. **결정사항 후보 추출(Analyze) + ✅ 확정**이 주 역할입니다.

## 책임 분리

- **mom.md 집계** (baby → mom concat+dedup) → **Stop hook이 세션 종료 시 자동 실행**
- **Analyze (Opus 분석)** + **2단계 핀** + **decisions.md 확정** → 이 대시보드의 역할

## 기능

- **Baby MDs** — Claude 세션별 대화 기록 목록 (앱 기록 + 훅 기록 구분)
- **Mom MD + Audit** — Opus가 중복 제거 후 결정사항 카드로 표시, 재분석 버튼
- **Decisions** — 현재 확정된 결정사항 (decisions.md)

## 2단계 핀

1. **mom 핀 (📌)** — "중요하지만 아직 미결" 표시 → 재분석 시 Opus가 우선 처리
2. **확정 (✅)** — decisions.md 기록 + CLAUDE.md 마커 섹션 자동 업데이트

## 동작 (Claude가 직접 실행)

```bash
/hams:dashboard [--port 7777]
```

Claude 실행 절차:
1. 포트 충돌 정리: `python3 -c "import subprocess; subprocess.run(['bash','-c','lsof -ti:7777 | xargs kill -9 2>/dev/null'], capture_output=True)"`
2. 서버 시작: `python3 skills/dashboard/server.py --port 7777 --project {cwd}`
3. 브라우저 오픈 (Windows): `start http://localhost:7777`

> mom.md는 Stop hook이 세션 종료마다 자동 갱신합니다. 대시보드 시작 시 별도 집계 단계는 없습니다.

## Fallback (mom.md가 비어있거나 stale 의심 시)

Stop hook이 deeptalk 활성으로 bail했거나, 세션이 비정상 종료된 경우 수동 집계:

```bash
python3 skills/dashboard/scripts/aggregate.py {cwd}
```

## 데이터

- `.hamstern/baby-hamster/*.md` — 세션 기록 (UserPromptSubmit/Stop hook이 turn 단위 append)
- `.hamstern/mom-hamster/mom.md` — 집계본 (Stop hook이 세션 종료 시 자동 갱신)
- `.hamstern/boss-hamster/decisions.md` — 확정 결정사항 (대시보드 ✅ 확정 시 기록)
