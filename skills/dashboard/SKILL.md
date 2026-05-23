---
name: dashboard
description: hamstern 정적 dashboard publish + 브라우저 viewer 오픈 — .hamstern → docs/data 번들 후 commit·push, gh-pages 가 serve.
---

# /hams:dashboard

`.hamstern/decisions.md`, `decisions-log.md`, `sessions/*.md` 의 현재 스냅샷을 `docs/data/` 로 번들하고 GitHub 으로 push 한 뒤 브라우저에서 정적 viewer 를 연다.

## 책임

- **publish** — `.hamstern/*.md` 를 `docs/data/` 로 복사 + `manifest.json` 생성
- **commit + push** — `docs/data/` 변경 시 chore commit + main push
- **viewer 오픈** — `https://edu-openskill.github.io/hamstern/`

쓰지 않는 것:
- `.hamstern/*.md` (record/audit-decisions 가 관리)
- 인증·서버 (정적 사이트)

## 동작 (Claude 가 실행)

1. **번들**
   ```
   python3 skills/dashboard/build.py --project .
   ```
   stderr / non-zero exit 시 중단 (commit·push 스킵).

2. **변경 감지**
   ```
   git status --short docs/data/
   ```

3. **commit + push** (출력에 변경 있으면)
   ```
   git add docs/data/
   git commit -m "chore(dashboard): refresh data $(date -u +%Y-%m-%dT%H:%M:%SZ)"
   git push origin main
   ```

4. **브라우저 오픈** (플랫폼별)
   - Windows: `start https://edu-openskill.github.io/hamstern/`
   - macOS: `open https://edu-openskill.github.io/hamstern/`
   - Linux: `xdg-open https://edu-openskill.github.io/hamstern/`

## 1회성 GitHub Pages 활성화

repo 의 Settings → Pages → Source: `Deploy from a branch` → Branch: `main` → Folder: `/docs` → Save. 활성화 후 1~2분 대기.

## 편집 흐름

브라우저는 read-only. 결정사항 `[×]` 클릭 → 클립보드에 `/hams:audit-decisions remove "<text>"` 복사 → Claude 세션에 붙여넣어 실행. 다음 `/hams:dashboard` 호출 시 변경 반영.

## 데이터

| 소스 | 출력 |
|---|---|
| `.hamstern/decisions.md` | `docs/data/decisions.md` |
| `.hamstern/decisions-log.md` | `docs/data/decisions-log.md` |
| `.hamstern/sessions/*.md` | `docs/data/sessions/<name>.md` |
| — | `docs/data/manifest.json` (build.py 가 생성) |
