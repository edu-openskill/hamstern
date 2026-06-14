---
name: ssot
description: |
  프로젝트 SSOT 문서(PRD·tech·아키텍처·rules)의 드리프트를 사후 advisory로 탐지.
  포인터를 meta.json에 등록하고(set), 확인하고(list), 게이트를 돌린다(check).
  사용법:
    /hams:ssot set <글로브…>   # SSOT 경로 등록 (프로젝트 repo 안에서)
    /hams:ssot list            # 등록 경로 + repo_url + 실존 미리보기
    /hams:ssot check           # freshness 게이트 (검사0 + 추출기 → advisory)
allowed-tools:
  - Read
  - Bash
---

# /hams:ssot

SSOT 문서가 코드보다 뒤처졌는지(stale) 사후·non-blocking으로 알린다. 막지 않는다.
자세한 데이터 모델·계약은 `docs/discussions/2026-06-14-ssot-freshness-gate-design.md` 참조.

## 실행

모든 서브커맨드는 `python3 skills/ssot/ssot.py <cmd> ...` 를 호출한다 (Bash).

- `set <글로브…>` — 프로젝트 repo 안에서 실행. SSOT 글로브를 `meta.json.ssot_paths`에,
  `git remote`의 URL을 `meta.json.repo_url`에 저장. 로컬 경로는 저장하지 않음(런타임 해석).
- `list` — 등록된 경로·repo_url + 각 글로브 실존 여부.
- `check` — 프로젝트 repo 안에서 실행. 검사0(글로브 self-validate) → 추출기 →
  advisory 리포트. 항상 exit 0.

## 추출기 (pluggable)

- 내장: `extractors/skill_registry_check.py` — hamstern 스킬 레지스트리 정합성
  (① 문서의 `/hams:<name>` 참조 ↔ marketplace.json 등록집합, ② orphan 스킬 디렉터리).
- 프로젝트-로컬: 프로젝트 repo의 `.hamstern/ssot-extractors/*.sh` 를 자동 발견·실행.
- 계약: `argv[1]=project_root`, `argv[2:]=SSOT 파일들`. stdout에
  `severity\tlocation\tmessage` (severity ∈ ERROR/WARN). exit 무시.
