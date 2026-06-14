# SSOT Freshness Gate (sub-project A) — Design

- 날짜: 2026-06-14
- 대상 repo: `edu-openskill/hamstern` (이 repo)
- 성격: 설계 스펙 (구현 전). 후속 = writing-plans → 구현
- 배경 논의: ncs-eval `docs/discussions/2026-06-14-hamstern-spec-drift-gate.md` (스펙 드리프트 두 겹 문서·이중 게이트 결론)

## 1. 목적과 범위

hamstern에 **스펙 드리프트 탐지**를 더한다. 전체 그림은 두 게이트(사후 freshness + 사전 guard)지만, 이 스펙은 **sub-project A = SSOT freshness 루프**만 다룬다.

**A의 산출물:**
1. `/hams:ssot` 단일 멀티커맨드 스킬 (포인터 관리 + freshness 체크)
2. 내장 추출기 1종(hamstern 자기점검) + 프로젝트-로컬 추출기 seam
3. hamstern 자신에 dogfood → record/remind 잔재 탐지 → **정리까지** (탐지→수정 루프 완결)

**명시적 비범위 (후속):**
- 사전 decision guard (diff↔decisions) = **sub-project B**
- 대시보드 SSOT blob 링크 렌더 = **sub-project C**
- `/hams:init`에 SSOT 설정 prompt 통합 = 후속 작은 확장
- 선언적 config 추출기 / 범용 추출기 엔진 = 필요해질 때 (YAGNI)

## 2. 발견된 공백 (설계 전제)

hamstern은 현재 **프로젝트 repo 위치를 추적하지 않는다**:
- `meta.json.repos`는 항상 `[]` (실제 데이터 확인됨, init이 채우지 않음)
- `active-project.json` = `{uuid, name, hamstern_data_path, linked_at}` — 프로젝트 경로 없음

freshness 게이트는 ① SSOT·코드 스캔용 **프로젝트 로컬 경로**, ② blob 링크용 **프로젝트 GitHub URL**이 필요하다. 둘 다 없으므로 A가 최소 추적을 추가한다.

## 3. 데이터 모델

```jsonc
// meta.json  (hamstern-data, 디바이스 간 동기화 → device-independent 값만)
{
  // ...기존 필드(uuid, name, description, repos, created_at, last_active)...
  "ssot_paths": [".claude/rules/*.md", "docs/PRD.md"],   // 프로젝트-상대 글로브 (신규)
  "repo_url":   "https://github.com/{owner}/{repo}"        // blob 링크용 (신규, set 시 자동 취득)
}
```

**결정:**
1. **SSOT 경로 = 프로젝트-상대 글로브 리스트.** 절대경로 금지(디바이스 의존). meta.json에 저장(동기화).
2. **repo_url만 저장, 로컬 경로는 런타임 해석.** meta.json은 여러 디바이스 공유 → device-independent URL만. 프로젝트 로컬 경로는 `check`/`set` 실행 시 `git rev-parse --show-toplevel`(cwd)로 그때그때 해석. (기존 "device-specific는 active 캐시, 공유값은 hamstern-data" 원칙 준수)
3. **`repos: []` 공백 채움.** `set`이 프로젝트 repo에서 `git remote get-url origin`으로 repo_url 자동 취득.

## 4. 스킬 구조 — `/hams:ssot`

`/hams:rule` 패턴 미러. 단일 스킬, 서브커맨드 3개.

| 서브커맨드 | 동작 | 실행 위치 |
|---|---|---|
| `/hams:ssot set <글로브…>` | SSOT 경로를 meta.json에 저장 + repo_url 자동 취득. 인자 없으면 현재 값 표시 후 대화형 입력 | 프로젝트 repo 안 |
| `/hams:ssot list` | 설정된 SSOT 경로 + repo_url + 각 경로 실존 여부(검사0 미리보기) | 어디서든 (읽기) |
| `/hams:ssot check` | freshness 게이트 실행 (검사0 + 추출기 → advisory 리포트) | 프로젝트 repo 안 |

**규율:** 신규 스킬이므로 커밋 `886dd61` 룰대로 `marketplace.json` 등록 + `plugin.json` 버전 bump(1.3.0 → 1.4.0).

## 5. 게이트 흐름 — `/hams:ssot check`

```
1. resolve  : active 프로젝트 + project_root = git rev-parse --show-toplevel (cwd)
              meta.json에서 ssot_paths 로드
2. 검사0    : 각 ssot 글로브가 project_root에서 ≥1 파일로 풀리나?
   (self-validate)  └ 안 풀리면 → 🔴 "지정된 SSOT 경로 X가 더는 존재하지 않음"
              ※ "포인터의 메타-드리프트도 탐지로 푼다" 구현 지점
3. 추출기   : pluggable. (살아남은 SSOT 파일 목록 + project_root) 입력
   ├ 내장 1종 (hamstern 자기점검) — §6
   └ 로컬 seam: .hamstern/ssot-extractors/*.sh 발견 시 함께 실행 — §6
4. 리포트   : advisory·non-blocking. chat에 그룹 출력. 항상 exit 0
              [🔴 깨진 포인터] / [⚠️ 드리프트] / [✅ 이상 없음]
```

**원칙:**
- **non-blocking advisory** — freshness는 알리되 막지 않는다. 커밋·작업을 멈추지 않음. (시끄럽게 막는 건 sub-project B 몫)
- **내장 추출기는 hamstern 전용** — 일반 프로젝트(ncs-eval 등)에서 `check`는 검사0 + 로컬 seam 스크립트만 동작. 일반 프로젝트용 추출기는 seam으로 추가.
- **리포트 finding 형식:** `심각도 · 파일:줄 · 메시지`. 검사0 깨짐=🔴, 추출기 드리프트=⚠️.

## 6. 추출기 — 계약 + seam (하이브리드)

추출기 = "코드에서 기계 검증 가능한 사실을 뽑아 SSOT 문서와 대조하는 한 단위". 선언적 config 아닌 **스크립트**. 내장·로컬 모두 동일 계약 → 실행 경로 하나.

```
계약 (모든 추출기 공통):
  입력 : project_root, 해석된 SSOT 파일 목록  (인자/env)
  출력 : stdout에 finding 1줄씩 — "심각도\t파일:줄\t메시지"
  exit : 무시 (advisory). 추출기는 "탐지"만, 게이트는 의미 해석 안 함

발견 위치:
  ① 내장 : 스킬 디렉터리 번들 스크립트 (hamstern 자기점검 1종)
  ② 로컬 : 프로젝트 repo의 .hamstern/ssot-extractors/*.sh  (게이트가 발견→동일 계약 실행→stdout 머지)
```

**내장 추출기 (hamstern 스킬 레지스트리 정합성) — 양방향:**
- ① 참조 → 레지스트리: **입력으로 받은 SSOT 파일 목록**을 스캔해 `/hams:<name>` 참조가 `marketplace.json` 등록 집합에 없음 → ⚠️ stale (`파일:줄` 보고)
- ② 디렉터리 → 현실: **project_root의 `skills/<Y>/`** 를 직접 열거해 SKILL.md 없음·미등록 (orphan) → ⚠️

> 명확화: ①은 계약대로 "입력 SSOT 파일 목록"만 스캔한다(그래서 dogfood는 ssot_paths에 스킬 파일·conventions를 포함시킨다 — §7). ②는 파일 내용이 아니라 디렉터리 구조 검사라 project_root를 직접 쓴다. 둘 다 계약 입력(project_root, SSOT 파일 목록) 안에서 동작한다.

**이점:** 추가 = 스크립트 한 개 드롭(스킬 코드 불변), 언어 무관·deterministic, `.hamstern/` 관례 재사용(`why`가 이미 사용), 내장도 같은 계약이라 실행 로직 단일.

## 7. Dogfood + 정리 (탐지→수정 루프 완결)

A 스펙에 **정리(c)까지 포함**한다.

1. **Dogfood:** hamstern repo에 `ssot_paths = ["skills/**/SKILL.md", "skills/**/*.sh", "docs/conventions.md"]` 설정 후 `/hams:ssot check`. (record/remind 참조가 이 글로브들에 다 잡힘 — SKILL.md 5곳 + audit-decisions/audit.sh + conventions.md)
2. **탐지 합격 기준:** `/hams:record`·`/hams:remind` 참조(살아있는 스킬 5개 + conventions.md) 전부 + orphan `skills/record/`(SKILL.md 없음)가 리포트됨.
3. **정리:** 게이트 출력으로 record/remind 참조 제거 + orphan `skills/record/` 삭제. 재실행 시 ✅.

## 8. 테스트

hamstern은 pytest 보유.
- **내장 추출기 단위테스트:** fixture(존재하지 않는 스킬 참조 문서)→finding 기대; orphan 디렉터리 fixture→finding 기대.
- **검사0 테스트:** 아무 파일도 안 풀리는 글로브 meta.json→🔴 finding 기대.
- **계약 테스트:** 로컬 seam 스크립트가 stdout finding을 내면 리포트에 머지되는지.

## 9. 합격 기준 (Definition of Done)

- [ ] `/hams:ssot` set/list/check 동작, marketplace.json 등록 + plugin.json 1.4.0 bump
- [ ] meta.json에 ssot_paths·repo_url 저장, 로컬 경로 런타임 해석
- [ ] 검사0이 깨진 글로브를 🔴로 검출
- [ ] 내장 추출기가 record/remind 참조 + orphan record/ 를 ⚠️로 검출 (dogfood)
- [ ] 로컬 seam(`.hamstern/ssot-extractors/*.sh`) 발견·실행·머지
- [ ] record/remind 잔재 정리 완료 → 재실행 ✅
- [ ] 단위·검사0·계약 테스트 통과
