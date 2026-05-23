# Sub-project D — Dashboard Static gh-pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/hams:dashboard` 호출 시 `.hamstern/*.md` 를 `docs/data/` 로 번들·commit·push·브라우저 오픈하여 정적 GitHub Pages 가 viewer 역할을 하게 한다. 편집은 브라우저에서 클립보드 슬래시 명령 → Claude 세션 → audit-decisions 의 신규 `remove "<text>"` args 형식이 처리.

**Architecture:** main 브랜치 단일. `.hamstern/` (소스) + `docs/` (gh-pages source: main `/docs`). `/hams:dashboard` 가 `skills/dashboard/build.py` 로 번들 후 변경 있으면 commit·push. 브라우저는 `docs/data/manifest.json` 을 시작점으로 fetch + marked.js 로 MD 렌더. read-only — 모든 write 는 클립보드 → 사용자 세션 → `/hams:audit-decisions remove "<text>"` 경유.

**Tech Stack:** Python 3 (stdlib only — pathlib, json, shutil, argparse). 정적 HTML + vanilla JS. CDN: marked@14.1.3, dompurify@3.1.7 (integrity hash 는 Task 10 에서 확정). pytest.

**Reference Spec:** `docs/discussions/2026-05-23-sub-d-dashboard-static-design.md`

---

## 파일 구조 결정

| 경로 | 작성/수정 | 책임 |
|---|---|---|
| `skills/dashboard/build.py` | **신규** | `.hamstern/*.md` → `docs/data/` 번들 + manifest.json 생성 + stale 정리 |
| `skills/dashboard/test_build.py` | **신규** | build.py pytest (6 케이스) |
| `skills/dashboard/SKILL.md` | **재작성** | 로컬 서버 절차 → publish + 오픈 절차 |
| `skills/dashboard/server.py` | **삭제** | 로컬 서버 폐기 |
| `skills/dashboard/static/` | **삭제 (전체)** | 정적 자산은 `docs/` 로 |
| `skills/audit-decisions/remove.py` | **신규** | `remove "<text>"` 의 Python 참조 구현 (test 가능한 격리 함수) |
| `skills/audit-decisions/test_remove.py` | **신규** | remove.py pytest (5 케이스) |
| `skills/audit-decisions/SKILL.md` | **수정** | Direct args 형식 문서화 (`remove "<text>"`) |
| `docs/index.html` | **신규** | 정적 viewer 마크업 |
| `docs/style.css` | **신규** | 3-column desktop + 탭 mobile 레이아웃 |
| `docs/app.js` | **신규** | fetch → render → clipboard → toast |
| `docs/data/` | **신규 (build.py 산출)** | 첫 빌드 시 자동 생성 + commit |
| `docs/conventions.md` | **수정** | dashboard 항목 Sub-D 확정 표기 |
| `README.md` | **수정** | dashboard 사용법 갱신 + Pages 활성화 안내 + changelog |
| `docs/plans/2026-05-23-sub-d-dashboard-verification.md` | **신규 (마지막 단계)** | 수동 UAT 결과 기록 |

---

## Task 1: 사전 점검 + git 상태 확인

**Files:** (읽기 전용 확인)

- [ ] **Step 1: 현재 디렉터리·브랜치 확인**

Run:
```
cd hamstern-plugin
git status --short
git log -1 --format='%h %s'
git remote -v
```

Expected:
- working tree: 본 plan 작업 외 unstaged 변경 가능 (record/skills/why/SKILL.md 등은 무시)
- 마지막 commit 가 spec (`513e702 docs(spec): Sub-project D ...`) 또는 그 이후
- remote = `origin https://github.com/edu-openskill/hamstern.git`

- [ ] **Step 2: spec 다시 한번 읽기**

`docs/discussions/2026-05-23-sub-d-dashboard-static-design.md` 전체. 특히 manifest.json 스키마와 클립보드 형식.

- [ ] **Step 3: 작업 시작 commit 마커 (선택)**

스킵. 첫 실제 변경부터 commit 한다.

---

## Task 2: `build.py` — 빈 케이스 테스트부터

**Files:**
- Create: `skills/dashboard/test_build.py`
- Create: `skills/dashboard/build.py`

- [ ] **Step 1: test_build.py 작성 (실패하는 테스트 1)**

```python
# skills/dashboard/test_build.py
"""Layer 2 regression for /hams:dashboard build step.

build.py 는 .hamstern/*.md 를 docs/data/ 로 번들 + manifest.json 생성.
"""
import json
from pathlib import Path

from skills.dashboard import build


def _setup_project(tmp_path: Path, *, decisions: str | None = None,
                   decisions_log: str | None = None,
                   sessions: dict[str, str] | None = None) -> Path:
    """tmp_path 에 .hamstern/ 가짜 프로젝트 생성."""
    hamstern = tmp_path / ".hamstern"
    hamstern.mkdir()
    if decisions is not None:
        (hamstern / "decisions.md").write_text(decisions, encoding="utf-8")
    if decisions_log is not None:
        (hamstern / "decisions-log.md").write_text(decisions_log, encoding="utf-8")
    if sessions:
        (hamstern / "sessions").mkdir()
        for name, body in sessions.items():
            (hamstern / "sessions" / name).write_text(body, encoding="utf-8")
    return tmp_path


def test_empty_hamstern_produces_empty_manifest(tmp_path):
    project = _setup_project(tmp_path)
    out = tmp_path / "docs" / "data"

    build.run(project_root=project, out_dir=out)

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["decisions"] is False
    assert manifest["decisions_log"] is False
    assert manifest["sessions"] == []
    assert not (out / "decisions.md").exists()
    assert not (out / "decisions-log.md").exists()
```

- [ ] **Step 2: 테스트 실패 확인**

Run:
```
cd hamstern-plugin
python3 -m pytest skills/dashboard/test_build.py::test_empty_hamstern_produces_empty_manifest -v
```

Expected: `ModuleNotFoundError: No module named 'skills.dashboard.build'` 또는 ImportError

- [ ] **Step 3: build.py 최소 구현 (이 테스트만 통과)**

```python
# skills/dashboard/build.py
"""Bundle .hamstern/*.md into docs/data/ for the static gh-pages viewer.

Stdlib only — pathlib, json, shutil, argparse, datetime.
"""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1


def run(project_root: Path, out_dir: Path) -> dict:
    """Bundle .hamstern -> out_dir. Returns the manifest dict."""
    project_root = Path(project_root)
    out_dir = Path(out_dir)
    src = project_root / ".hamstern"

    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decisions": False,
        "decisions_log": False,
        "sessions": [],
    }

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
```

또한 빈 `skills/dashboard/__init__.py` 가 필요 (pytest import 용).

- [ ] **Step 4: `skills/dashboard/__init__.py` 와 `skills/__init__.py` 확인·생성**

Run:
```
test -f hamstern-plugin/skills/__init__.py || touch hamstern-plugin/skills/__init__.py
test -f hamstern-plugin/skills/dashboard/__init__.py || touch hamstern-plugin/skills/dashboard/__init__.py
```

만약 `skills/record/test_record_format.py` 가 다른 방식 (sys.path) 으로 import 하면 그 패턴 따른다. (record 의 test 는 `from <module>` 형태가 아닌 in-file reference 라 __init__.py 불필요할 수도 — 만약 그렇다면 build.py 도 in-file 참조 + relative import 패턴 따를 것; 그 경우 본 task 의 import 라인을 그에 맞춰 조정.)

- [ ] **Step 5: 테스트 통과 확인**

Run:
```
python3 -m pytest skills/dashboard/test_build.py::test_empty_hamstern_produces_empty_manifest -v
```

Expected: 1 passed

- [ ] **Step 6: commit**

```
git add skills/dashboard/build.py skills/dashboard/test_build.py skills/__init__.py skills/dashboard/__init__.py
git commit -m "feat(dashboard): build.py skeleton + empty case test (Sub-D)"
```

(`__init__.py` 가 이미 있던 경우 그 라인 빼고)

---

## Task 3: `build.py` — decisions.md 복사

**Files:**
- Modify: `skills/dashboard/test_build.py`
- Modify: `skills/dashboard/build.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`test_build.py` 끝에 append:

```python
def test_decisions_only_copies_file_and_sets_flag(tmp_path):
    project = _setup_project(
        tmp_path,
        decisions="# 프로젝트 결정사항\n\n## Architecture\n- foo\n",
    )
    out = tmp_path / "docs" / "data"

    build.run(project_root=project, out_dir=out)

    assert (out / "decisions.md").read_text(encoding="utf-8") == \
        "# 프로젝트 결정사항\n\n## Architecture\n- foo\n"
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["decisions"] is True
    assert manifest["decisions_log"] is False
    assert manifest["sessions"] == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run:
```
python3 -m pytest skills/dashboard/test_build.py::test_decisions_only_copies_file_and_sets_flag -v
```

Expected: AssertionError on `out / "decisions.md"` (파일이 없음)

- [ ] **Step 3: build.py 에 decisions.md 복사 로직 추가**

`build.py` 의 `run()` 안에서 manifest 초기화 직후, manifest.json write 직전에 추가:

```python
    decisions_src = src / "decisions.md"
    if decisions_src.is_file():
        shutil.copy2(decisions_src, out_dir / "decisions.md")
        manifest["decisions"] = True
```

- [ ] **Step 4: 두 테스트 모두 통과 확인**

Run:
```
python3 -m pytest skills/dashboard/test_build.py -v
```

Expected: 2 passed

- [ ] **Step 5: commit**

```
git add skills/dashboard/build.py skills/dashboard/test_build.py
git commit -m "feat(dashboard): build.py copies decisions.md (Sub-D)"
```

---

## Task 4: `build.py` — decisions-log.md 복사

**Files:**
- Modify: `skills/dashboard/test_build.py`
- Modify: `skills/dashboard/build.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`test_build.py` 끝:

```python
def test_decisions_log_copies_and_sets_flag(tmp_path):
    project = _setup_project(
        tmp_path,
        decisions_log="# Decisions Log\n<!-- append-only -->\n",
    )
    out = tmp_path / "docs" / "data"

    build.run(project_root=project, out_dir=out)

    assert (out / "decisions-log.md").read_text(encoding="utf-8").startswith("# Decisions Log")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["decisions_log"] is True
    assert manifest["decisions"] is False
```

- [ ] **Step 2: 실패 확인**

```
python3 -m pytest skills/dashboard/test_build.py::test_decisions_log_copies_and_sets_flag -v
```

Expected: FAIL

- [ ] **Step 3: build.py 에 decisions-log.md 복사 추가**

`decisions_src` 블럭 다음에:

```python
    log_src = src / "decisions-log.md"
    if log_src.is_file():
        shutil.copy2(log_src, out_dir / "decisions-log.md")
        manifest["decisions_log"] = True
```

- [ ] **Step 4: 전체 테스트 통과**

```
python3 -m pytest skills/dashboard/test_build.py -v
```

Expected: 3 passed

- [ ] **Step 5: commit**

```
git add skills/dashboard/build.py skills/dashboard/test_build.py
git commit -m "feat(dashboard): build.py copies decisions-log.md (Sub-D)"
```

---

## Task 5: `build.py` — sessions/ 복사 + manifest 채움

**Files:**
- Modify: `skills/dashboard/test_build.py`
- Modify: `skills/dashboard/build.py`

- [ ] **Step 1: 실패하는 테스트 추가**

```python
def test_sessions_copied_and_listed_in_manifest(tmp_path):
    project = _setup_project(
        tmp_path,
        sessions={
            "session_2026-05-22.md": "# session A\n",
            "session_2026-05-23.md": "# session B\n",
        },
    )
    out = tmp_path / "docs" / "data"

    build.run(project_root=project, out_dir=out)

    assert (out / "sessions" / "session_2026-05-22.md").exists()
    assert (out / "sessions" / "session_2026-05-23.md").exists()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(manifest["sessions"]) == [
        "session_2026-05-22.md",
        "session_2026-05-23.md",
    ]
```

- [ ] **Step 2: 실패 확인**

```
python3 -m pytest skills/dashboard/test_build.py::test_sessions_copied_and_listed_in_manifest -v
```

Expected: FAIL

- [ ] **Step 3: build.py 에 sessions 복사 추가**

`log_src` 블럭 다음:

```python
    sessions_src = src / "sessions"
    if sessions_src.is_dir():
        sessions_out = out_dir / "sessions"
        sessions_out.mkdir(exist_ok=True)
        names = []
        for f in sorted(sessions_src.glob("*.md"),
                        key=lambda p: p.stat().st_mtime, reverse=True):
            shutil.copy2(f, sessions_out / f.name)
            names.append(f.name)
        manifest["sessions"] = names
```

- [ ] **Step 4: 전체 테스트**

```
python3 -m pytest skills/dashboard/test_build.py -v
```

Expected: 4 passed

- [ ] **Step 5: commit**

```
git add skills/dashboard/build.py skills/dashboard/test_build.py
git commit -m "feat(dashboard): build.py copies sessions/ (Sub-D)"
```

---

## Task 6: `build.py` — stale 정리

**Files:**
- Modify: `skills/dashboard/test_build.py`
- Modify: `skills/dashboard/build.py`

- [ ] **Step 1: 실패하는 테스트 추가**

```python
def test_stale_files_removed_on_rebuild(tmp_path):
    project = _setup_project(
        tmp_path,
        decisions="# decisions\n- A\n",
        sessions={"session_old.md": "old\n"},
    )
    out = tmp_path / "docs" / "data"

    # 1차 빌드
    build.run(project_root=project, out_dir=out)
    assert (out / "sessions" / "session_old.md").exists()

    # 소스에서 session_old.md 삭제 + decisions.md 도 제거
    (project / ".hamstern" / "sessions" / "session_old.md").unlink()
    (project / ".hamstern" / "decisions.md").unlink()

    # 2차 빌드
    build.run(project_root=project, out_dir=out)

    assert not (out / "sessions" / "session_old.md").exists(), "stale session 남음"
    assert not (out / "decisions.md").exists(), "stale decisions.md 남음"
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sessions"] == []
    assert manifest["decisions"] is False
```

- [ ] **Step 2: 실패 확인**

```
python3 -m pytest skills/dashboard/test_build.py::test_stale_files_removed_on_rebuild -v
```

Expected: FAIL (session_old.md 가 stale 로 남음)

- [ ] **Step 3: build.py 에 stale 정리 로직 추가**

`run()` 함수 안, 데이터 복사 전에 prepass 로 out_dir 초기화:

```python
    # stale 정리 — 매번 깨끗이 다시 쓴다
    if out_dir.exists():
        for child in out_dir.iterdir():
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
    out_dir.mkdir(parents=True, exist_ok=True)
```

이 블럭이 `manifest = {...}` 초기화 보다 앞에 와야 한다. (manifest 초기화는 이미 있음 — 위치만 확인.)

- [ ] **Step 4: 전체 테스트**

```
python3 -m pytest skills/dashboard/test_build.py -v
```

Expected: 5 passed

- [ ] **Step 5: commit**

```
git add skills/dashboard/build.py skills/dashboard/test_build.py
git commit -m "feat(dashboard): build.py stale cleanup on rebuild (Sub-D)"
```

---

## Task 7: `build.py` — idempotency + CLI entry

**Files:**
- Modify: `skills/dashboard/test_build.py`
- Modify: `skills/dashboard/build.py`

- [ ] **Step 1: 실패하는 테스트 추가 (idempotency 6th 케이스)**

```python
def test_idempotent_two_calls_same_content(tmp_path):
    """동일 소스로 두 번 호출 → 데이터 파일 내용 동일 (mtime 만 다를 수 있음)."""
    project = _setup_project(
        tmp_path,
        decisions="# d\n- x\n",
        sessions={"s.md": "body\n"},
    )
    out = tmp_path / "docs" / "data"

    build.run(project_root=project, out_dir=out)
    first_decisions = (out / "decisions.md").read_text(encoding="utf-8")
    first_session = (out / "sessions" / "s.md").read_text(encoding="utf-8")

    build.run(project_root=project, out_dir=out)
    assert (out / "decisions.md").read_text(encoding="utf-8") == first_decisions
    assert (out / "sessions" / "s.md").read_text(encoding="utf-8") == first_session
    # manifest 의 sessions 도 동일
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["sessions"] == ["s.md"]
```

- [ ] **Step 2: 실패 확인**

```
python3 -m pytest skills/dashboard/test_build.py::test_idempotent_two_calls_same_content -v
```

Expected: 이미 통과할 가능성 큼 (stale 정리 + 결정적 sort 로). PASS 이면 OK — Step 3 스킵.

- [ ] **Step 3: 만약 FAIL 이면 원인 디버깅**

가장 유력: sort key 가 mtime 인데 mtime 이 같아 순서 비결정 → key 를 `(p.stat().st_mtime, p.name)` 으로 보강.

수정 시 build.py 의 sort 라인:
```python
        for f in sorted(sessions_src.glob("*.md"),
                        key=lambda p: (-p.stat().st_mtime, p.name)):
```

- [ ] **Step 4: CLI 진입점 추가**

`build.py` 맨 끝에 (run 함수 아래):

```python
def main():
    parser = argparse.ArgumentParser(description="Bundle .hamstern -> docs/data")
    parser.add_argument("--project", default=".", help="프로젝트 루트 (.hamstern/ 가 있는 곳)")
    parser.add_argument("--out", default="docs/data", help="출력 디렉터리 (project 기준 상대 또는 절대)")
    args = parser.parse_args()
    project = Path(args.project).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = project / out
    manifest = run(project_root=project, out_dir=out)
    print(f"built: decisions={manifest['decisions']} log={manifest['decisions_log']} sessions={len(manifest['sessions'])}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 수동 실행 확인 (smoke)**

Run:
```
cd hamstern-plugin
python3 skills/dashboard/build.py --project .
ls docs/data/
cat docs/data/manifest.json
```

Expected: `decisions=True log=True sessions=N` 출력. `docs/data/manifest.json` 존재 + 현재 .hamstern 데이터 반영.

- [ ] **Step 6: 전체 테스트 + commit**

```
python3 -m pytest skills/dashboard/test_build.py -v
```
Expected: 6 passed

```
git add skills/dashboard/build.py skills/dashboard/test_build.py docs/data/
git commit -m "feat(dashboard): build.py CLI entry + first data bundle (Sub-D)"
```

(첫 commit 에 docs/data/ 도 함께 — 이후 task 들이 이 데이터를 기준으로 작동)

---

## Task 8: `audit-decisions/remove.py` — 신규 helper

**Files:**
- Create: `skills/audit-decisions/remove.py`
- Create: `skills/audit-decisions/test_remove.py`
- Create: `skills/audit-decisions/__init__.py` (필요 시)

decisions.md 형식 (record SKILL.md 정의):
```
# 프로젝트 결정사항

_마지막 업데이트: 2026-05-23T...Z_

## Architecture
- decision body <!-- session: session_2026-05-22.md -->
- another decision body
```

매칭 규칙: `<text>` 와 같은 line 의 `- ` 다음 본문 (있다면 `<!-- session: ... -->` 마커는 제거 후) 가 일치하는 첫 줄을 삭제.

- [ ] **Step 1: 실패하는 첫 테스트**

```python
# skills/audit-decisions/test_remove.py
"""Direct args form: /hams:audit-decisions remove "<text>"
실패 시 stderr 메시지 + non-zero exit. 성공 시 decisions.md 갱신 + log append.
"""
from pathlib import Path

from skills.audit_decisions import remove as removemod


def _setup(tmp_path: Path, decisions_md: str, log_md: str | None = None):
    h = tmp_path / ".hamstern"
    h.mkdir()
    (h / "decisions.md").write_text(decisions_md, encoding="utf-8")
    if log_md is not None:
        (h / "decisions-log.md").write_text(log_md, encoding="utf-8")
    return h


def test_removes_matching_line(tmp_path):
    h = _setup(tmp_path, "# decisions\n\n## A\n- foo bar\n- baz\n")

    result = removemod.run(project_root=tmp_path, text="foo bar")

    assert result.removed is True
    assert result.line == "- foo bar"
    new = (h / "decisions.md").read_text(encoding="utf-8")
    assert "- foo bar" not in new
    assert "- baz" in new  # 다른 line 영향 없음
```

`skills/audit_decisions/__init__.py` 도 빈 파일로 (import 용). 디렉터리명이 하이픈인 `audit-decisions` 라 Python module name 으로 직접 사용 불가 → **디렉터리명을 `audit_decisions` 로 변경하거나, 그대로 두고 import path 를 sys.path manipulation 으로 우회**.

**결정**: 디렉터리명을 바꾸는 건 marketplace.json 의 skill path (`./skills/audit-decisions`) 와 어긋남 → 디렉터리명 유지. test_remove.py 에서 `importlib.util.spec_from_file_location` 로 우회.

테스트 import 부분을 다음으로 교체:

```python
import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("audit_remove", _HERE / "remove.py")
removemod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(removemod)
```

(같은 패턴을 build test 에도 retroactively 적용 — Task 2 의 `from skills.dashboard import build` 가 동작하지 않으면 본 패턴으로 교체. 일관성 위해서.)

- [ ] **Step 2: import 우회 패턴 재확인 + build test 정합성**

`skills/dashboard/test_build.py` 의 import 가 실제 동작하는지 확인:

```
cd hamstern-plugin
python3 -m pytest skills/dashboard/test_build.py -v
```

만약 `ModuleNotFoundError` 면 같은 importlib 패턴으로 교체:

```python
import importlib.util
from pathlib import Path
_spec = importlib.util.spec_from_file_location("dashboard_build", Path(__file__).parent / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)
```

(이미 통과했다면 그대로 둔다.)

- [ ] **Step 3: 실패 확인**

```
python3 -m pytest skills/audit-decisions/test_remove.py::test_removes_matching_line -v
```

Expected: FAIL (remove.py 없음)

- [ ] **Step 4: `remove.py` 작성**

```python
# skills/audit-decisions/remove.py
"""Direct args form for /hams:audit-decisions:

    /hams:audit-decisions remove "<text>"

decisions.md 의 `- <text>` 또는 `- <text> <!-- session: ... -->` 첫 매칭 줄 삭제 +
decisions-log.md 에 제거 이벤트 append.

Stdlib only. import 측은 importlib.util 로 로드 (디렉터리명 하이픈).
"""
import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SESSION_MARKER_RE = re.compile(r"\s*<!--\s*session:\s*\S+?\s*-->\s*$")


@dataclass
class RemoveResult:
    removed: bool
    line: str = ""
    reason: str = ""


def _strip_marker(body: str) -> str:
    return SESSION_MARKER_RE.sub("", body).rstrip()


def run(project_root: Path, text: str) -> RemoveResult:
    project_root = Path(project_root)
    decisions_file = project_root / ".hamstern" / "decisions.md"
    log_file = project_root / ".hamstern" / "decisions-log.md"

    if not decisions_file.is_file():
        return RemoveResult(removed=False, reason=f"decisions.md not found at {decisions_file}")

    target = text.strip()
    lines = decisions_file.read_text(encoding="utf-8").splitlines()
    out_lines = []
    removed_line = None
    for ln in lines:
        if removed_line is None and ln.startswith("- "):
            body = _strip_marker(ln[2:])
            if body == target:
                removed_line = ln
                continue  # skip this line
        out_lines.append(ln)

    if removed_line is None:
        return RemoveResult(removed=False, reason=f"no matching decision for: {target!r}")

    decisions_file.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    # log append
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    entry = (
        f"\n---\n\n## {ts} | 핀 제거\n"
        f"- **결정:** {target}\n"
        f"- **제거 이유:** dashboard 에서 × 클릭 (사용자 세션 명령)\n"
    )
    if not log_file.exists():
        log_file.write_text("# Decisions Log\n<!-- append-only. 수동 편집 금지. -->\n", encoding="utf-8")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(entry)

    return RemoveResult(removed=True, line=removed_line)


def main():
    parser = argparse.ArgumentParser(description="Remove a decision by exact body match")
    parser.add_argument("text", help="결정 본문 (앞의 '- ' 와 trailing session 마커 제외)")
    parser.add_argument("--project", default=".", help="프로젝트 루트")
    args = parser.parse_args()
    result = run(project_root=Path(args.project).resolve(), text=args.text)
    if not result.removed:
        print(f"error: {result.reason}", file=sys.stderr)
        sys.exit(1)
    print(f"removed: {result.line}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 테스트 통과 확인**

```
python3 -m pytest skills/audit-decisions/test_remove.py -v
```

Expected: 1 passed

- [ ] **Step 6: commit**

```
git add skills/audit-decisions/remove.py skills/audit-decisions/test_remove.py
git commit -m "feat(audit-decisions): remove.py direct args form (Sub-D)"
```

---

## Task 9: `remove.py` — session marker 매칭 + 미매칭 케이스

**Files:**
- Modify: `skills/audit-decisions/test_remove.py`

- [ ] **Step 1: 4 개 추가 테스트 작성**

`test_remove.py` 끝:

```python
def test_removes_line_with_session_marker(tmp_path):
    _setup(
        tmp_path,
        "# d\n\n## A\n- foo bar <!-- session: session_2026-05-22.md -->\n- baz\n",
    )

    result = removemod.run(project_root=tmp_path, text="foo bar")

    assert result.removed is True
    new = (tmp_path / ".hamstern" / "decisions.md").read_text(encoding="utf-8")
    assert "foo bar" not in new
    assert "- baz" in new


def test_no_match_returns_false(tmp_path):
    _setup(tmp_path, "# d\n\n## A\n- foo\n")

    result = removemod.run(project_root=tmp_path, text="does not exist")

    assert result.removed is False
    assert "no matching decision" in result.reason
    # 파일 변경 없음
    assert (tmp_path / ".hamstern" / "decisions.md").read_text(encoding="utf-8") == \
        "# d\n\n## A\n- foo\n"


def test_only_first_match_removed(tmp_path):
    _setup(tmp_path, "# d\n\n## A\n- dup\n- dup\n")

    result = removemod.run(project_root=tmp_path, text="dup")

    assert result.removed is True
    new = (tmp_path / ".hamstern" / "decisions.md").read_text(encoding="utf-8")
    assert new.count("- dup") == 1


def test_log_appended_on_successful_remove(tmp_path):
    _setup(
        tmp_path,
        "# d\n\n## A\n- foo\n",
        log_md="# Decisions Log\n",
    )

    removemod.run(project_root=tmp_path, text="foo")

    log = (tmp_path / ".hamstern" / "decisions-log.md").read_text(encoding="utf-8")
    assert "핀 제거" in log
    assert "**결정:** foo" in log
```

- [ ] **Step 2: 모두 통과 확인 (Step 1 의 4개 + 첫 Task 의 1개 = 5개)**

```
python3 -m pytest skills/audit-decisions/test_remove.py -v
```

Expected: 5 passed

(만약 FAIL 면 remove.py 의 marker strip 또는 first-match 로직 점검)

- [ ] **Step 3: commit**

```
git add skills/audit-decisions/test_remove.py
git commit -m "test(audit-decisions): remove edge cases (marker, no-match, first-only, log) (Sub-D)"
```

---

## Task 10: `audit-decisions/SKILL.md` 갱신

**Files:**
- Modify: `skills/audit-decisions/SKILL.md`

- [ ] **Step 1: SKILL.md 의 "사용 방법" 섹션 교체**

기존:
```
## 사용 방법

\`\`\`bash
/hams:audit-decisions
\`\`\`

옵션 없음 — 현재 프로젝트의 모든 결정사항 검토
```

다음으로 교체:
```
## 사용 방법

### 인터랙티브 audit (기존)

\`\`\`bash
/hams:audit-decisions
\`\`\`

현재 프로젝트의 모든 결정사항을 Opus 분석으로 검토. 옵션 없음.

### 직접 제거 (Sub-D dashboard 가 발행하는 형식)

\`\`\`bash
/hams:audit-decisions remove "<decision text>"
\`\`\`

`.hamstern/decisions.md` 에서 본문이 `<text>` 와 정확히 일치하는 첫 `- ` 줄을 삭제 + `decisions-log.md` 에 제거 이벤트 append. `<text>` 는 leading `- ` 와 trailing `<!-- session: ... -->` 마커를 제외한 본문. `"` 가 본문에 있으면 백슬래시 escape (`\"`).

내부 구현: `skills/audit-decisions/remove.py`. Claude 가 다음을 실행:

\`\`\`
python3 skills/audit-decisions/remove.py "<text>" --project .
\`\`\`

매칭 0건이면 stderr 메시지 + non-zero exit. dashboard 의 `[×]` 가 발행하는 클립보드 명령에서 호출되는 게 주 사용 사례.
```

- [ ] **Step 2: SKILL.md 의 다른 부분 — "옵션 없음" 같은 위에서 모순되는 줄 검색·정리**

```
grep -n "옵션 없음" skills/audit-decisions/SKILL.md
```

남아 있으면 위 새 섹션이 그것을 대체하도록 정리.

- [ ] **Step 3: commit**

```
git add skills/audit-decisions/SKILL.md
git commit -m "docs(audit-decisions): document remove \"<text>\" direct form (Sub-D)"
```

---

## Task 11: `docs/index.html` 스켈레톤

**Files:**
- Create: `docs/index.html`

CDN 핀: marked@14.1.3, dompurify@3.1.7. integrity 해시는 jsdelivr SRI 페이지에서 확정.

- [ ] **Step 1: 통합 해시 확인**

Run:
```
curl -s "https://www.jsdelivr.com/package/npm/marked?tab=files&version=14.1.3" >/dev/null
# 실제 SRI 는 jsdelivr 의 +esm 또는 SRI generator 사용
# 대안: cdn 파일 받아서 직접 계산
curl -sL "https://cdn.jsdelivr.net/npm/marked@14.1.3/marked.min.js" | openssl dgst -sha384 -binary | openssl base64 -A
echo
curl -sL "https://cdn.jsdelivr.net/npm/dompurify@3.1.7/dist/purify.min.js" | openssl dgst -sha384 -binary | openssl base64 -A
echo
```

출력 2개를 메모. Windows 환경이면 PowerShell:
```
$h=(Invoke-WebRequest "https://cdn.jsdelivr.net/npm/marked@14.1.3/marked.min.js" -UseBasicParsing).Content
[Convert]::ToBase64String((New-Object System.Security.Cryptography.SHA384Managed).ComputeHash([Text.Encoding]::UTF8.GetBytes($h)))
```
(주의: 위 라인은 raw bytes vs UTF8 차이로 다른 해시 산출 위험 — Linux/macOS shell 우선 사용. 가능하면 git bash.)

이 두 해시를 `<MARKED_SRI>`, `<DOMPURIFY_SRI>` 자리에 채워넣음 (아래 Step 2).

- [ ] **Step 2: docs/index.html 작성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>🐹 hams-dashboard</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <span class="logo">🐹</span>
  <h1>hams-dashboard</h1>
  <span class="spacer"></span>
  <span class="generated" id="generated">…</span>
</header>

<nav class="tabs" id="tabs">
  <button data-tab="decisions" class="active">Decisions</button>
  <button data-tab="sessions">Sessions</button>
  <button data-tab="log">Log</button>
</nav>

<main class="main">
  <section class="col col-sessions" data-tab="sessions">
    <h2>Sessions</h2>
    <div id="sessions-list"><div class="empty">…</div></div>
    <div id="session-render" class="session-render"></div>
  </section>

  <section class="col col-decisions" data-tab="decisions">
    <h2>Decisions</h2>
    <div id="decisions-list"><div class="empty">…</div></div>
  </section>

  <section class="col col-log" data-tab="log">
    <h2>Log</h2>
    <div id="log-list"><div class="empty">…</div></div>
  </section>
</main>

<div id="toast" class="toast hidden"></div>

<script src="https://cdn.jsdelivr.net/npm/marked@14.1.3/marked.min.js"
        integrity="sha384-<MARKED_SRI>" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.1.7/dist/purify.min.js"
        integrity="sha384-<DOMPURIFY_SRI>" crossorigin="anonymous"></script>
<script src="app.js"></script>
</body>
</html>
```

`<MARKED_SRI>` 와 `<DOMPURIFY_SRI>` 를 Step 1 의 실제 base64 해시로 치환.

만약 해시 확정이 어려우면 임시로 `integrity` 와 `crossorigin` 속성을 **제거** (script 태그는 유지). README 의 known-issues 에 "TODO: SRI 추가" 명시. v1 의 우선순위는 동작.

- [ ] **Step 3: commit**

```
git add docs/index.html
git commit -m "feat(dashboard): docs/index.html static skeleton (Sub-D)"
```

---

## Task 12: `docs/style.css`

**Files:**
- Create: `docs/style.css`

- [ ] **Step 1: docs/style.css 작성**

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f5f5f5;
  color: #222;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

header {
  background: #1a1a2e;
  color: white;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}
header .logo { font-size: 20px; }
header h1 { font-size: 18px; font-weight: 600; }
header .spacer { flex: 1; }
header .generated { font-size: 12px; color: #aaa; font-family: ui-monospace, monospace; }

nav.tabs { display: none; }   /* desktop 기본 숨김 */
nav.tabs button {
  background: white;
  border: 1px solid #ddd;
  padding: 10px 18px;
  cursor: pointer;
  font-size: 14px;
}
nav.tabs button.active { background: #1a1a2e; color: white; border-color: #1a1a2e; }

.main {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 1px;
  background: #ddd;
}
.col {
  background: white;
  overflow-y: auto;
  padding: 16px;
}
.col-sessions  { width: 220px; flex-shrink: 0; }
.col-decisions { flex: 1; min-width: 360px; }
.col-log       { width: 320px; flex-shrink: 0; }
.col h2 {
  font-size: 13px;
  color: #666;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
}

.session-item {
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 12px;
  color: #333;
  margin-bottom: 4px;
  border: 1px solid #eee;
  cursor: pointer;
  font-family: ui-monospace, monospace;
}
.session-item:hover { background: #f9f9f9; }
.session-item.active { background: #eef; border-color: #99c; }

.session-render {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #eee;
  font-size: 13px;
  line-height: 1.6;
}
.session-render h1, .session-render h2, .session-render h3 { margin: 12px 0 6px; }
.session-render pre, .session-render code {
  background: #f3f3f3;
  padding: 1px 4px;
  border-radius: 3px;
  font-family: ui-monospace, monospace;
  font-size: 12px;
}
.session-render pre { padding: 8px; overflow-x: auto; }

.decision-category {
  font-size: 12px;
  text-transform: uppercase;
  color: #888;
  margin: 14px 0 6px;
  font-weight: 600;
}
.decision-item {
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 13px;
  border: 1px solid #e0e0e0;
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.decision-item .text { flex: 1; }
.decision-item .del {
  color: #ccc;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  flex-shrink: 0;
  user-select: none;
}
.decision-item .del:hover { color: #F44336; }

.log-card {
  padding: 10px 12px;
  border-radius: 4px;
  font-size: 12px;
  border: 1px solid #eee;
  margin-bottom: 8px;
  background: #fafafa;
}
.log-card .time { color: #888; font-family: ui-monospace, monospace; font-size: 11px; margin-bottom: 4px; }
.log-card .event-pin { color: #2e7d32; }
.log-card .event-unpin { color: #c62828; }

.empty { color: #bbb; font-size: 13px; text-align: center; padding: 24px 12px; line-height: 1.5; }

.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #1a1a2e;
  color: white;
  padding: 10px 16px;
  border-radius: 6px;
  font-size: 13px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.18);
  transition: opacity 0.3s ease;
}
.toast.hidden { opacity: 0; pointer-events: none; }

@media (max-width: 768px) {
  nav.tabs { display: flex; padding: 8px; background: white; border-bottom: 1px solid #ddd; gap: 4px; }
  nav.tabs button { flex: 1; }
  .main { flex-direction: column; }
  .col { width: 100% !important; display: none; }
  .col.active { display: block; }
  .col-sessions, .col-log { border-top: 1px solid #ddd; }
}
```

- [ ] **Step 2: commit**

```
git add docs/style.css
git commit -m "feat(dashboard): docs/style.css 3-column + mobile tabs (Sub-D)"
```

---

## Task 13: `docs/app.js` — fetch manifest + render decisions

**Files:**
- Create: `docs/app.js`

- [ ] **Step 1: app.js 초안 작성 (decisions 만, 다음 task 들에서 sessions/log/clipboard/tabs 추가)**

```js
// docs/app.js
// 정적 viewer — fetch manifest → render decisions + sessions + log
// read-only. write 는 클립보드 슬래시 명령 + 사용자 세션 경유.

const DATA_PATH = 'data';

async function fetchText(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${url} ${r.status}`);
  return r.text();
}
async function fetchJSON(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${url} ${r.status}`);
  return r.json();
}

function setGenerated(ts) {
  document.getElementById('generated').textContent = ts ? `generated: ${ts}` : '';
}

function renderEmpty(el, msg) {
  el.innerHTML = `<div class="empty">${msg}</div>`;
}

function parseDecisions(md) {
  // returns [{category, body, raw}] in document order
  const out = [];
  let currentCat = 'Other';
  for (const ln of md.split('\n')) {
    if (ln.startsWith('## ')) {
      currentCat = ln.slice(3).trim();
      continue;
    }
    if (ln.startsWith('- ')) {
      const raw = ln;
      let body = ln.slice(2);
      body = body.replace(/\s*<!--\s*session:\s*\S+?\s*-->\s*$/, '').trim();
      out.push({ category: currentCat, body, raw });
    }
  }
  return out;
}

function renderDecisions(md) {
  const el = document.getElementById('decisions-list');
  if (!md || !md.trim()) {
    renderEmpty(el, '결정사항 없음<br><small>/hams:record 로 추가 가능</small>');
    return;
  }
  const items = parseDecisions(md);
  if (items.length === 0) {
    renderEmpty(el, '결정사항 없음');
    return;
  }
  const byCat = new Map();
  for (const it of items) {
    if (!byCat.has(it.category)) byCat.set(it.category, []);
    byCat.get(it.category).push(it);
  }
  let html = '';
  for (const [cat, list] of byCat) {
    html += `<div class="decision-category">${cat}</div>`;
    for (const it of list) {
      const escapedAttr = it.body.replace(/"/g, '&quot;');
      html += `<div class="decision-item">
        <span class="text">${DOMPurify.sanitize(it.body)}</span>
        <span class="del" data-text="${escapedAttr}" title="제거">×</span>
      </div>`;
    }
  }
  el.innerHTML = html;
}

async function load() {
  let manifest;
  try {
    manifest = await fetchJSON(`${DATA_PATH}/manifest.json`);
  } catch (e) {
    renderEmpty(document.getElementById('decisions-list'),
      'Dashboard 데이터 미생성.<br>Claude 세션에서 <code>/hams:dashboard</code> 호출 후 재방문.');
    return;
  }
  setGenerated(manifest.generated_at);

  if (manifest.decisions) {
    const md = await fetchText(`${DATA_PATH}/decisions.md`);
    renderDecisions(md);
  } else {
    renderEmpty(document.getElementById('decisions-list'), '결정사항 없음');
  }
}

load();
```

- [ ] **Step 2: 수동 검증 (Pages 활성 전, 로컬 file:// 또는 임시 python -m http.server)**

```
cd hamstern-plugin
python3 -m http.server 8000 --directory docs &
# 브라우저 http://localhost:8000/ 열어 확인
```

Expected: decisions.md 의 결정사항이 카테고리별로 표시. × 버튼은 아직 동작 안 함 (Task 17).

서버 종료: 해당 백그라운드 PID kill 또는 Ctrl+C.

- [ ] **Step 3: commit**

```
git add docs/app.js
git commit -m "feat(dashboard): docs/app.js fetch manifest + render decisions (Sub-D)"
```

---

## Task 14: `app.js` — sessions list + inline render

**Files:**
- Modify: `docs/app.js`

- [ ] **Step 1: app.js 에 sessions 관련 함수 추가**

`parseDecisions` 함수 위에:

```js
function renderSessionsList(sessions) {
  const el = document.getElementById('sessions-list');
  if (!sessions || sessions.length === 0) {
    renderEmpty(el, '세션 없음');
    return;
  }
  let html = '';
  for (const name of sessions) {
    const short = name.replace(/^session_/, '').replace(/\.md$/, '');
    const escapedAttr = name.replace(/"/g, '&quot;');
    html += `<div class="session-item" data-file="${escapedAttr}">${short}</div>`;
  }
  el.innerHTML = html;
  el.addEventListener('click', onSessionClick);
}

let currentSessionEl = null;
async function onSessionClick(e) {
  const item = e.target.closest('.session-item');
  if (!item) return;
  const file = item.dataset.file;
  if (currentSessionEl) currentSessionEl.classList.remove('active');
  item.classList.add('active');
  currentSessionEl = item;

  const render = document.getElementById('session-render');
  render.innerHTML = '<em>loading…</em>';
  try {
    const md = await fetchText(`${DATA_PATH}/sessions/${file}`);
    render.innerHTML = DOMPurify.sanitize(marked.parse(md));
  } catch (err) {
    render.innerHTML = `<div class="empty">파일 로드 실패: ${file}</div>`;
  }
}
```

`load()` 함수의 끝에 추가:
```js
  renderSessionsList(manifest.sessions || []);
```

- [ ] **Step 2: 로컬 서버로 다시 확인**

세션 아이템 클릭 → 같은 컬럼 하단에 MD 렌더링 표시.

- [ ] **Step 3: commit**

```
git add docs/app.js
git commit -m "feat(dashboard): app.js sessions list + inline MD render (Sub-D)"
```

---

## Task 15: `app.js` — log timeline

**Files:**
- Modify: `docs/app.js`

- [ ] **Step 1: app.js 에 log 관련 함수 추가**

`onSessionClick` 함수 아래:

```js
function parseLog(md) {
  // decisions-log.md 의 `## YYYY-MM-DDTHH:MM:SS | 핀 추가|제거` 블럭 파싱.
  // 반환: [{time, event, body}], 최신순.
  const blocks = [];
  const lines = md.split('\n');
  let current = null;
  for (const ln of lines) {
    const m = ln.match(/^##\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s*\|\s*(.+)$/);
    if (m) {
      if (current) blocks.push(current);
      current = { time: m[1], event: m[2].trim(), body: [] };
    } else if (current) {
      current.body.push(ln);
    }
  }
  if (current) blocks.push(current);
  blocks.reverse();
  return blocks;
}

function renderLog(md) {
  const el = document.getElementById('log-list');
  if (!md || !md.trim()) { renderEmpty(el, '로그 없음'); return; }
  const blocks = parseLog(md);
  if (blocks.length === 0) { renderEmpty(el, '로그 없음'); return; }
  let html = '';
  for (const b of blocks) {
    const cls = b.event.includes('추가') ? 'event-pin'
              : b.event.includes('제거') ? 'event-unpin' : '';
    const bodyHtml = DOMPurify.sanitize(marked.parse(b.body.join('\n').trim() || ''));
    html += `<div class="log-card">
      <div class="time">${b.time}</div>
      <div class="${cls}">${b.event}</div>
      <div>${bodyHtml}</div>
    </div>`;
  }
  el.innerHTML = html;
}
```

`load()` 함수 마지막에:
```js
  if (manifest.decisions_log) {
    const md = await fetchText(`${DATA_PATH}/decisions-log.md`);
    renderLog(md);
  } else {
    renderEmpty(document.getElementById('log-list'), '로그 없음');
  }
```

- [ ] **Step 2: 로컬 서버로 확인 — log 카드 시간 역순 표시**

- [ ] **Step 3: commit**

```
git add docs/app.js
git commit -m "feat(dashboard): app.js log timeline render (Sub-D)"
```

---

## Task 16: `app.js` — 클립보드 복사 + toast

**Files:**
- Modify: `docs/app.js`

- [ ] **Step 1: app.js 에 클립보드 + toast 추가**

`renderLog` 함수 아래:

```js
function showToast(msg, ms = 3000) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.remove('hidden');
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => el.classList.add('hidden'), ms);
}

function escapeForSlashCommand(text) {
  // `"` 를 backslash escape — audit-decisions remove.py 와 대응
  return text.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    // fallback — hidden textarea
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand('copy'); } catch {}
    document.body.removeChild(ta);
    return ok;
  }
}

document.getElementById('decisions-list').addEventListener('click', async (e) => {
  const del = e.target.closest('.del');
  if (!del) return;
  const text = del.dataset.text;
  if (!text) return;
  const cmd = `/hams:audit-decisions remove "${escapeForSlashCommand(text)}"`;
  const ok = await copyToClipboard(cmd);
  if (ok) {
    showToast('복사됨 — Claude 세션에 붙여넣어 실행');
  } else {
    showToast('복사 실패 — 콘솔에서 복사하세요');
    console.log('COPY THIS:', cmd);
  }
});
```

(주의: `renderDecisions` 가 호출될 때마다 `decisions-list` 의 innerHTML 이 재설정되어도 위 listener 는 부모 element 에 bind 되어 있으므로 유지됨.)

- [ ] **Step 2: 로컬 서버로 검증**

× 클릭 → toast 표시 + 클립보드에 정확히 `/hams:audit-decisions remove "<text>"` 들어감 (다른 앱에 paste 해서 확인).

- [ ] **Step 3: commit**

```
git add docs/app.js
git commit -m "feat(dashboard): app.js clipboard slash command + toast (Sub-D)"
```

---

## Task 17: `app.js` — 모바일 탭 전환

**Files:**
- Modify: `docs/app.js`

- [ ] **Step 1: 탭 전환 로직 추가**

app.js 끝에 (혹은 `load();` 호출 위):

```js
function activateTab(name) {
  document.querySelectorAll('nav.tabs button').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === name);
  });
  document.querySelectorAll('.col').forEach(c => {
    c.classList.toggle('active', c.dataset.tab === name);
  });
}

document.getElementById('tabs').addEventListener('click', (e) => {
  if (e.target.tagName === 'BUTTON' && e.target.dataset.tab) {
    activateTab(e.target.dataset.tab);
  }
});

// 초기 active: decisions
activateTab('decisions');
```

- [ ] **Step 2: 검증**

브라우저 폭 ≤ 768px (DevTools 모바일 모드) → 탭 표시 + 클릭 시 컬럼 전환.

- [ ] **Step 3: commit**

```
git add docs/app.js
git commit -m "feat(dashboard): app.js mobile tab switching (Sub-D)"
```

---

## Task 18: 레거시 server.py + static/ 삭제

**Files:**
- Delete: `skills/dashboard/server.py`
- Delete: `skills/dashboard/static/` (전체)

- [ ] **Step 1: 삭제 실행**

```
cd hamstern-plugin
git rm skills/dashboard/server.py
git rm -r skills/dashboard/static/
```

- [ ] **Step 2: 다른 곳에서 참조 없는지 확인**

```
grep -rn "skills/dashboard/server.py\|skills/dashboard/static" \
  skills/ docs/ README.md .claude-plugin/ 2>/dev/null
```

기대: 결과 0 또는 docs/discussions·plans 의 historical 문서만 (이전 sub-project 문서들 — OK).

- [ ] **Step 3: pytest 전체 재실행 (잔존 의존성 확인)**

```
python3 -m pytest skills/ -v
```

Expected: 모두 통과. (build, remove, record 기존 테스트)

- [ ] **Step 4: commit**

```
git commit -m "refactor(dashboard): drop server.py + static/ (replaced by static gh-pages) (Sub-D)"
```

---

## Task 19: `skills/dashboard/SKILL.md` 재작성

**Files:**
- Modify: `skills/dashboard/SKILL.md`

- [ ] **Step 1: SKILL.md 전면 재작성**

전체 내용을 다음으로 교체:

```markdown
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
   \`\`\`
   python3 skills/dashboard/build.py --project .
   \`\`\`
   stderr / non-zero exit 시 중단 (commit·push 스킵).

2. **변경 감지**
   \`\`\`
   git status --short docs/data/
   \`\`\`

3. **commit + push** (출력에 변경 있으면)
   \`\`\`
   git add docs/data/
   git commit -m "chore(dashboard): refresh data $(date -u +%Y-%m-%dT%H:%M:%SZ)"
   git push origin main
   \`\`\`

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
```

- [ ] **Step 2: commit**

```
git add skills/dashboard/SKILL.md
git commit -m "docs(dashboard): rewrite SKILL.md for static gh-pages flow (Sub-D)"
```

---

## Task 20: `docs/conventions.md` + README 갱신

**Files:**
- Modify: `docs/conventions.md`
- Modify: `README.md`

- [ ] **Step 1: conventions.md 의 dashboard 줄 갱신**

```
grep -n "dashboard\|Sub-D" docs/conventions.md
```

Sub-D 미정 표기 (예: "Sub-D 에서 ... 재설계 예정") 를 다음 같이 확정 표기로 변경:

> `/hams:dashboard` — `.hamstern/*.md` 를 `docs/data/` 로 번들 + commit·push 후 `https://edu-openskill.github.io/hamstern/` 정적 viewer 오픈. read-only viewer; `[×]` 클릭 → 클립보드 `/hams:audit-decisions remove "<text>"`.

(현 줄 내용에 따라 위 문장으로 적절히 바꿔 적기.)

- [ ] **Step 2: README.md 의 dashboard 줄 갱신**

```
grep -n "/hams:dashboard" README.md
```

찾은 줄 (예: `| `/hams:dashboard` | 결정사항 추출·핀·확정 웹 UI 열기 |`) 을:

`| `/hams:dashboard` | `.hamstern` 스냅샷을 정적 gh-pages 로 publish + viewer 오픈 |`

- [ ] **Step 3: README 에 changelog 항목 추가 (Sub-D)**

기존 Sub-C changelog 다음에:

```markdown
### Sub-project D — Dashboard static gh-pages + browser edit UI (2026-05-23)

- 로컬 Python HTTP 서버 (`skills/dashboard/server.py`) 와 `static/` 디렉터리 제거.
- `/hams:dashboard` 가 `skills/dashboard/build.py` 로 `.hamstern/*.md` → `docs/data/` 번들 + commit·push + `https://edu-openskill.github.io/hamstern/` 오픈.
- 정적 viewer: `docs/{index.html, app.js, style.css}`. CDN 의존성 = marked.js + DOMPurify 2개.
- 편집 흐름: 브라우저 read-only → `[×]` 클릭 → 클립보드 `/hams:audit-decisions remove "<text>"` → 사용자 세션 → 다음 dashboard 호출 시 publish.
- `skills/audit-decisions` 에 `remove "<text>"` 직접 args 형식 추가 (`remove.py` + 5 pytest 케이스).
- repo 이전: `getinthere-private-job/hamstern-plugin` → `edu-openskill/hamstern`.
- GitHub Pages 활성화는 1회성 manual step (Settings → Pages → Source: main /docs).
```

- [ ] **Step 4: commit**

```
git add docs/conventions.md README.md
git commit -m "docs: conventions.md + README.md Sub-D updates (Sub-D)"
```

---

## Task 21: 첫 `/hams:dashboard` 실제 호출 + Pages 활성화

**Files:** (작성 없음 — 사용자 환경 작업)

- [ ] **Step 1: GitHub Settings → Pages 활성화 (1회성 manual)**

브라우저에서 https://github.com/edu-openskill/hamstern/settings/pages
→ Source: `Deploy from a branch`
→ Branch: `main`, Folder: `/docs`
→ Save.

저장 후 페이지 상단에 "Your site is live at https://edu-openskill.github.io/hamstern/" 메시지 출현까지 ~1분.

- [ ] **Step 2: `/hams:dashboard` 실제 호출 시뮬레이션**

```
cd hamstern-plugin
python3 skills/dashboard/build.py --project .
git status --short docs/data/
```

만약 변경 있으면:
```
git add docs/data/
git commit -m "chore(dashboard): refresh data $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git push origin main
```

(이미 Task 7 에서 첫 commit 되었을 수 있음 — 변경 0 이면 skip)

- [ ] **Step 3: 브라우저 오픈 + 시각 검증**

```
start https://edu-openskill.github.io/hamstern/    # Windows
```

확인:
- 헤더의 generated timestamp 표시
- Decisions 컬럼에 카테고리별 결정사항 표시
- Sessions 컬럼에 파일 리스트
- 세션 클릭 시 하단에 MD 렌더
- Log 컬럼에 시간순 카드
- `[×]` 클릭 → toast + 클립보드에 `/hams:audit-decisions remove "..."` 정확히 복사
- 브라우저 폭 좁히면 (DevTools 모바일) 탭 전환

- [ ] **Step 4: 만약 404 면**

- Settings → Pages 의 Source 가 `main /docs` 인지 재확인
- 첫 빌드 후 1-2분 대기
- `docs/index.html` 이 main 에 commit·push 되었는지 확인 (`git ls-tree origin/main docs/index.html`)

문제 해결 후 다시 Step 3.

---

## Task 22: 수동 verification 기록

**Files:**
- Create: `docs/plans/2026-05-23-sub-d-dashboard-verification.md`

- [ ] **Step 1: verification.md 작성**

```markdown
# Sub-project D — Dashboard Static gh-pages Verification

**Date:** 2026-05-23 (구현 완료일 기준 갱신)
**Plan:** `2026-05-23-sub-d-dashboard-static-plan.md`

## 자동 테스트

| 테스트 | 케이스 수 | 결과 |
|---|---|---|
| `skills/dashboard/test_build.py` | 6 | ✅ pass |
| `skills/audit-decisions/test_remove.py` | 5 | ✅ pass |
| `skills/record/test_record_format.py` (기존 회귀) | 기존 | ✅ pass |

명령: `python3 -m pytest skills/ -v` — 전체 그린.

## 수동 UAT

### 1. 첫 publish 흐름
- [ ] `/hams:dashboard` 호출 → `docs/data/` 생성 + commit + push 성공
- [ ] 브라우저 `https://edu-openskill.github.io/hamstern/` 200 응답

### 2. 데이터 렌더링
- [ ] Decisions: 카테고리별 그룹 + 각 항목 `[×]` 버튼 표시
- [ ] Sessions: 파일 리스트, 클릭 시 MD 렌더
- [ ] Log: 시간 역순 카드, 핀 추가/제거 색 구분

### 3. 편집 흐름
- [ ] `[×]` 클릭 → toast 표시
- [ ] 클립보드에 `/hams:audit-decisions remove "<text>"` 정확히 복사 (다른 앱 paste 로 검증)
- [ ] 본문에 `"` 포함 시 `\"` 로 escape 되는지 확인
- [ ] 붙여넣어 실행 → `.hamstern/decisions.md` 에서 해당 줄 제거 + `decisions-log.md` 에 append
- [ ] 다음 `/hams:dashboard` 호출 시 viewer 에서 사라짐

### 4. 빈 상태
- [ ] 새 디렉터리에서 `.hamstern/` 없이 호출 → build.py 빈 manifest 생성 + viewer 가 "데이터 미생성" 메시지

### 5. 모바일 레이아웃
- [ ] 폭 ≤ 768px 에서 탭 표시 + 전환 동작

### 6. 에러 케이스
- [ ] 매칭 0건 `remove` → stderr 메시지 + exit 1 + decisions.md 불변
- [ ] 같은 본문 2회 등록된 경우 → 첫 줄만 제거

## 발견 사항 / Follow-up

(구현 중 발견한 이슈, deferred 한 것들 기록)
```

- [ ] **Step 2: 실제 수동 UAT 수행하면서 체크박스 채우기**

각 항목 직접 시도. 실패 시 해당 task 로 돌아가 fix.

- [ ] **Step 3: commit**

```
git add docs/plans/2026-05-23-sub-d-dashboard-verification.md
git commit -m "test(verify): Sub-D dashboard static gh-pages verification log (Sub-D)"
```

---

## Task 23: 마무리 push + 정리

**Files:** (push 만)

- [ ] **Step 1: 최종 git push**

```
cd hamstern-plugin
git log origin/main..main --oneline
```

origin/main 대비 차이 확인. 모든 Sub-D commit 이 보임.

```
git push origin main
```

- [ ] **Step 2: 옛 repo (`getinthere-private-job/hamstern-plugin`) 처리**

사용자 결정:
- (a) archive: GitHub Settings → "Archive this repository" — read-only 보존
- (b) delete: Settings → "Delete this repository" — 완전 제거
- (c) 그대로 두기

본 plan 은 (a) 추천. 명시적 사용자 액션이라 plan task 로는 보류만.

- [ ] **Step 3: 완료 보고**

사용자에게 보고:
- Sub-D 완료 commit 수, push 결과
- Pages URL 동작 확인
- verification.md 위치
- Sub-E (Slack/Discord broadcast) 가 다음 자연스러운 단계

---

## Self-Review (plan 작성자 본인 점검 — 실행 시 무시)

**Spec coverage:**
- ✅ 두 계층 + 다리 (.hamstern / docs/ / build.py) — Task 2-7
- ✅ /hams:dashboard 흐름 4단계 — Task 19 (SKILL.md 재작성)
- ✅ 3-column desktop + 모바일 탭 — Task 12, 17
- ✅ 편집 클립보드 + escape — Task 16
- ✅ audit-decisions remove 확장 — Task 8-10
- ✅ Stale 정리 — Task 6
- ✅ manifest.json schema — Task 5
- ✅ 에러 처리 (실패·미활성·구브라우저·rate) — Task 13 (empty fallback), 16 (clipboard fallback)
- ✅ 테스트: build 6 + remove 5 + manual 6 — Task 2-7, 8-9, 22
- ✅ 삭제: server.py + static/ — Task 18
- ✅ docs/conventions + README 업데이트 — Task 20
- ✅ Pages 활성화 manual step — Task 21
- ✅ repo 이전은 brainstorm 단계에서 이미 완료, plan 에서는 옛 repo 처리만 — Task 23 (사용자 액션)
- ✅ verification.md — Task 22

**Placeholders:**
- CDN integrity 해시 자리 `<MARKED_SRI>` — Task 11 Step 1 에서 실제로 계산. 만약 환경 제약이면 빼고 동작 우선 (명시).
- `<text>`, `<name>` 같은 메타 syntax 자리표시는 spec 어휘로 의도된 것 (OK).

**Type consistency:**
- `RemoveResult` 의 fields: `removed`, `line`, `reason` — 모든 테스트가 이 이름 사용 ✅
- build.run 의 keyword args: `project_root`, `out_dir` — 모든 테스트가 이 이름 사용 ✅
- manifest fields: `schema_version`, `generated_at`, `decisions`, `decisions_log`, `sessions` — spec + 모든 task ✅
