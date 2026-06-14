# SSOT Dashboard Links (sub-project C) — Design

- 날짜: 2026-06-14
- 대상 repo: `edu-openskill/hamstern` (이 repo)
- 성격: 설계 스펙 (구현 전). 후속 = writing-plans → 구현
- 의존: sub-project A (`/hams:ssot`, hamstern v1.4.0) — meta.json에 `ssot_paths`·`repo_url` 저장됨
- 배경: `docs/discussions/2026-06-14-hamstern-spec-drift-gate.md` (대시보드는 복사 말고 GitHub blob 링크)

## 1. 목적과 범위

hamstern 대시보드(GitHub Pages)의 per-project view에 그 프로젝트의 **SSOT 문서로 가는 GitHub 링크 목록**을 추가한다. 문서 내용을 복사하지 않고 원본으로 보낸다 → 항상 최신, 스냅샷 드리프트 없음.

**비범위:** 프로젝트 목록(index) 페이지, freshness 게이트(A), build의 기존 decisions/sessions/mockups 로직.

## 2. 발견된 제약 (설계 전제)

`build.py`는 **hamstern-data(메타 repo) 위에서** 실행되어 **프로젝트 실제 파일이 없다** (파일 헤더: `hamstern-data/projects/*/... → docs/data/`). 따라서 빌드 시점에 글로브를 실제 파일로 확장할 수 없다.

→ 결론: 구체 경로는 blob 링크, 글로브는 tree(폴더) 링크로 렌더한다.

## 3. 데이터 — manifest 확장 (build.py)

`run_single_project(src_dir, out_dir)`가 `src_dir/meta.json`을 읽어 `ssot_paths`·`repo_url`을 추출하고, 각 경로를 링크 엔트리로 변환해 `manifest["ssot"]`에 넣는다. `run_multiproject`는 이를 `projects[uuid]["ssot"]`에 포함한다.

**링크 엔트리 규칙:**
```
각 path in ssot_paths:
  '*' 없음 (구체 파일) → {"label": path, "url": f"{repo_url}/blob/HEAD/{path}", "kind": "file"}
  '*' 있음 (글로브)    → prefix = path의 첫 '*' 이전 세그먼트들을 '/'로 결합
                         {"label": path, "url": f"{repo_url}/tree/HEAD/{prefix}", "kind": "glob"}
                         (첫 세그먼트가 글로브면 prefix="" → url = f"{repo_url}/tree/HEAD")
repo_url 없음 → {"label": path, "url": None, "kind": ...}  (라벨만)
ssot_paths 없음 → manifest["ssot"] = []
```

**결정:**
1. **URL 구성은 build.py(Python)** — `test_build.py`로 검증. app.js는 받은 url만 렌더.
2. **branch = `HEAD`** — `{repo_url}/blob/HEAD/{path}`는 GitHub가 기본 브랜치로 리다이렉트(main/master 하드코딩 회피).
3. **repo_url은 이미 `https://github.com/{owner}/{repo}` 형태**(A의 set이 정규화) → 문자열 결합, 재파싱 불필요.
4. **복사 없음** — manifest엔 url만, 문서 내용 미포함.

글로브 prefix 예: `skills/**/SKILL.md`→`skills`, `docs/*.md`→`docs`, `docs/PRD.md`→(글로브 아님, blob).

## 4. 렌더 — per-project view (app.js + HTML)

per-project view 렌더 시 `manifest.projects[uuid].ssot`가 있으면 "SSOT 문서" 섹션을 그린다.
- 각 엔트리 → `<a href="{url}" target="_blank">`. `kind=file`→📄, `kind=glob`→📁. 라벨 = path/패턴.
- `url`이 null이면(repo_url 미설정) 링크 없이 **라벨 plain text**로만 표시.
- ssot 비었거나 없으면 → 섹션 숨김 (`renderMockupsList`가 컨테이너 없음/빈 목록을 다루는 패턴 그대로).
- `DOMPurify.sanitize`로 label·url sanitize (기존 일관).
- 배치: per-project 페이지의 mockups 섹션 인근("참조 자료" 성격).

**plan에서 핀할 디테일:** per-project HTML이 빌드 생성인지 공유 템플릿+라우팅인지 확인 후 `#ssot-list` 컨테이너 위치 결정 (렌더 방식 자체는 확정).

## 5. 테스트 (test_build.py)

- meta.json에 `ssot_paths`(구체+글로브) + `repo_url` → manifest의 ssot 엔트리가 올바른 blob/tree URL·kind를 가짐.
- `repo_url` 없음 → 엔트리 url=None, 라벨 보존.
- `ssot_paths` 없음 → `manifest["ssot"] == []`.
- 글로브 prefix 추출 단위 검증(`skills/**/SKILL.md`→tree/HEAD/skills 등).

## 6. 범위 경계 + 규율

- 링크만, 복사 없음.
- per-project view만. index 페이지 미변경.
- build의 기존 로직·A 게이트 불변 (manifest에 `ssot` 키만 additive).
- app.js는 기존 렌더 리팩토링 없이 SSOT 섹션만 추가.
- **버전 bump**: dashboard 동작 변경 → `plugin.json`·`marketplace.json` 1.4.0 → 1.5.0.

## 7. 합격 기준 (DoD)

- [ ] build.py가 meta.json의 ssot_paths·repo_url을 읽어 manifest.projects[uuid].ssot에 링크 엔트리 생성
- [ ] 구체경로→blob/HEAD, 글로브→tree/HEAD/prefix, repo_url 없음→url null
- [ ] app.js per-project view에 SSOT 섹션 렌더(📄/📁), 빈 경우 숨김, target=_blank, DOMPurify
- [ ] test_build.py 통과 (구체/글로브/no-repo_url/no-ssot)
- [ ] plugin.json·marketplace.json 1.5.0
- [ ] 문서 복사 0 (링크만)
