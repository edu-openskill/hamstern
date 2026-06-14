# SSOT Freshness Gate (sub-project A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** hamstern에 `/hams:ssot` 스킬을 추가해 프로젝트 SSOT 문서의 드리프트를 사후·advisory로 탐지하고, hamstern 자신의 record/remind 잔재로 dogfood한 뒤 정리한다.

**Architecture:** 단일 멀티커맨드 스킬(`set`/`list`/`check`). `check`는 검사0(포인터 self-validate) → 추출기(stdout 계약, 내장 1종 + 프로젝트-로컬 seam) → advisory non-blocking 리포트. SSOT 포인터는 `meta.json`(동기화)에, 프로젝트 로컬 경로는 런타임 해석.

**Tech Stack:** Python 3 (stdlib only), bash, pytest. 레퍼런스: `skills/audit-decisions/`(스킬+py+test), `skills/rule/`(멀티커맨드), `docs/conventions.md`(resolve_active_project/store_paths).

**Base:** repo `edu-openskill/hamstern`, branch `feat/ssot-freshness-gate`. 스펙: `docs/discussions/2026-06-14-ssot-freshness-gate-design.md`.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `skills/ssot/SKILL.md` | 멀티커맨드 절차 문서 (set/list/check) |
| `skills/ssot/ssot.py` | 오케스트레이터: 서브커맨드 dispatch, meta.json IO, 검사0, 추출기 runner, 리포트 |
| `skills/ssot/extractors/skill_registry_check.py` | 내장 추출기 (stdout 계약 따름): 스킬 레지스트리 정합성 ①참조 ②orphan |
| `skills/ssot/test_ssot.py` | ssot.py 순수함수 단위테스트 (검사0, 글로브, 계약 머지, meta IO) |
| `skills/ssot/extractors/test_skill_registry_check.py` | 내장 추출기 단위테스트 (가짜 참조, orphan) |
| `.claude-plugin/marketplace.json` | `./skills/ssot` 등록 + metadata.version bump |
| `.claude-plugin/plugin.json` | version 1.3.0 → 1.4.0 |

**공통 데이터형:** `Finding = (severity, location, message)` — severity ∈ {`"ERROR"`, `"WARN"`}, location = `"path:line"` 또는 `"path"`, message = 문자열. 리포트에서 `ERROR→🔴`, `WARN→⚠️`로 렌더.

**추출기 계약 (내장·로컬 동일):** `argv[1]=project_root`, `argv[2:]=SSOT 파일 경로들`. stdout에 `severity\tlocation\tmessage` 줄. exit code 무시.

---

### Task 1: 스킬 디렉터리 + meta.json IO 헬퍼

**Files:**
- Create: `skills/ssot/ssot.py`
- Test: `skills/ssot/test_ssot.py`

- [ ] **Step 1: Write the failing test**

```python
# skills/ssot/test_ssot.py
import json, os, importlib.util, pathlib

_spec = importlib.util.spec_from_file_location(
    "ssot", pathlib.Path(__file__).parent / "ssot.py")
ssot = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ssot)


def _make_hamstern_data(tmp_path, uuid="u1"):
    data = tmp_path / "hamstern-data"
    proj = data / "projects" / uuid
    proj.mkdir(parents=True)
    (proj / "meta.json").write_text(json.dumps(
        {"uuid": uuid, "name": "t", "repos": [],
         "created_at": "x", "last_active": "x"}), encoding="utf-8")
    cfg_dir = tmp_path / ".config" / "hamstern"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "active-project.json").write_text(json.dumps(
        {"uuid": uuid, "name": "t",
         "hamstern_data_path": str(data), "linked_at": "x"}), encoding="utf-8")
    return tmp_path


def test_load_and_save_meta_roundtrip(tmp_path, monkeypatch):
    home = _make_hamstern_data(tmp_path)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    active = ssot.resolve_active_project()
    meta = ssot.load_meta(active)
    meta["ssot_paths"] = [".claude/rules/*.md"]
    ssot.save_meta(active, meta)
    assert ssot.load_meta(active)["ssot_paths"] == [".claude/rules/*.md"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest skills/ssot/test_ssot.py::test_load_and_save_meta_roundtrip -v`
Expected: FAIL with `ModuleNotFoundError`/`No such file` (ssot.py 없음)

- [ ] **Step 3: Write minimal implementation**

```python
# skills/ssot/ssot.py
import json, os, sys, glob, subprocess
from collections import namedtuple

Finding = namedtuple("Finding", "severity location message")


def _home():
    return os.environ.get("HOME") or os.environ.get("USERPROFILE") or os.path.expanduser("~")


def resolve_active_project():
    cfg = os.path.join(_home(), ".config", "hamstern", "active-project.json")
    if not os.path.isfile(cfg):
        sys.exit('❌ active project 없음. /hams:link "name" 또는 /hams:init "name" 먼저.')
    c = json.load(open(cfg, encoding="utf-8"))
    proj_dir = os.path.join(c["hamstern_data_path"], "projects", c["uuid"])
    return {"uuid": c["uuid"], "name": c["name"],
            "hamstern_data": c["hamstern_data_path"], "proj_dir": proj_dir}


def _meta_path(active):
    return os.path.join(active["proj_dir"], "meta.json")


def load_meta(active):
    return json.load(open(_meta_path(active), encoding="utf-8"))


def save_meta(active, meta):
    json.dump(meta, open(_meta_path(active), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest skills/ssot/test_ssot.py::test_load_and_save_meta_roundtrip -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/ssot/ssot.py skills/ssot/test_ssot.py
git commit -m "feat(ssot): meta.json IO + active project resolve"
```

---

### Task 2: 글로브 해석 + 검사0 (포인터 self-validate)

**Files:**
- Modify: `skills/ssot/ssot.py`
- Test: `skills/ssot/test_ssot.py`

- [ ] **Step 1: Write the failing test**

```python
# append to skills/ssot/test_ssot.py
def test_resolve_globs_matches_existing(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PRD.md").write_text("x", encoding="utf-8")
    assert ssot.resolve_globs(str(tmp_path), ["docs/*.md"]) == ["docs/PRD.md"]


def test_check_pointers_flags_broken_glob(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PRD.md").write_text("x", encoding="utf-8")
    findings = ssot.check_pointers(str(tmp_path), ["docs/PRD.md", "missing/*.md"])
    locs = [(f.severity, f.location) for f in findings]
    assert ("ERROR", "missing/*.md") in locs
    assert all(f.location != "docs/PRD.md" for f in findings)  # 존재하는 건 finding 없음
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest skills/ssot/test_ssot.py -k "globs or pointers" -v`
Expected: FAIL with `AttributeError: module 'ssot' has no attribute 'resolve_globs'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to skills/ssot/ssot.py
def resolve_globs(project_root, ssot_paths):
    files = []
    for pat in ssot_paths:
        for m in glob.glob(os.path.join(project_root, pat), recursive=True):
            if os.path.isfile(m):
                files.append(os.path.relpath(m, project_root).replace(os.sep, "/"))
    return sorted(set(files))


def check_pointers(project_root, ssot_paths):
    findings = []
    for pat in ssot_paths:
        hits = glob.glob(os.path.join(project_root, pat), recursive=True)
        if not any(os.path.isfile(h) for h in hits):
            findings.append(Finding("ERROR", pat,
                                    "지정된 SSOT 경로가 더는 존재하지 않음 (메타-드리프트)"))
    return findings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest skills/ssot/test_ssot.py -k "globs or pointers" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add skills/ssot/ssot.py skills/ssot/test_ssot.py
git commit -m "feat(ssot): glob resolve + 검사0 pointer self-validate"
```

---

### Task 3: 내장 추출기 — 스킬 레지스트리 정합성

**Files:**
- Create: `skills/ssot/extractors/skill_registry_check.py`
- Test: `skills/ssot/extractors/test_skill_registry_check.py`

- [ ] **Step 1: Write the failing test**

```python
# skills/ssot/extractors/test_skill_registry_check.py
import json, subprocess, sys, pathlib

SCRIPT = pathlib.Path(__file__).parent / "skill_registry_check.py"


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True)


def _init_repo_with_skill(tmp_path):
    (tmp_path / ".claude-plugin").mkdir(parents=True)
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
        {"plugins": [{"skills": ["./skills/why"]}]}), encoding="utf-8")
    (tmp_path / "skills" / "why").mkdir(parents=True)
    (tmp_path / "skills" / "why" / "SKILL.md").write_text("# why", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
    return tmp_path


def _run(root, *files):
    out = subprocess.run([sys.executable, str(SCRIPT), str(root), *files],
                         capture_output=True, text=True)
    return out.stdout


def test_flags_unregistered_ref(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    doc = root / "docs.md"
    doc.write_text("see /hams:record for details", encoding="utf-8")
    out = _run(root, "docs.md")
    assert "WARN" in out and "record" in out and "docs.md:1" in out


def test_ignores_registered_ref(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    doc = root / "docs.md"
    doc.write_text("use /hams:why", encoding="utf-8")
    out = _run(root, "docs.md")
    assert "why" not in out  # 등록된 스킬은 finding 없음


def test_flags_orphan_skill_dir(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    # record/: SKILL.md 없음 + 추적 파일 0 (gitignore된 pyc만)
    (root / "skills" / "record" / "__pycache__").mkdir(parents=True)
    (root / "skills" / "record" / "__pycache__" / "t.pyc").write_text("x", encoding="utf-8")
    out = _run(root)
    assert "WARN" in out and "skills/record" in out and "orphan" in out.lower()


def test_diary_core_lib_not_flagged_as_orphan(tmp_path):
    root = _init_repo_with_skill(tmp_path)
    # 공유 lib: SKILL.md 없지만 추적 파일 있음 → orphan 아님
    (root / "skills" / "diary-core").mkdir(parents=True)
    (root / "skills" / "diary-core" / "render.py").write_text("x", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "y")
    out = _run(root)
    assert "diary-core" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest skills/ssot/extractors/test_skill_registry_check.py -v`
Expected: FAIL (script 없음 → 빈 stdout, assert 실패)

- [ ] **Step 3: Write minimal implementation**

```python
# skills/ssot/extractors/skill_registry_check.py
"""내장 추출기: 스킬 레지스트리 정합성. 계약: argv[1]=project_root, argv[2:]=SSOT 파일들.
stdout에 'severity\\tlocation\\tmessage' (WARN) 출력."""
import json, os, re, subprocess, sys

REF = re.compile(r"/hams:([a-z][a-z0-9-]*)")


def registered_skills(project_root):
    mp = os.path.join(project_root, ".claude-plugin", "marketplace.json")
    data = json.load(open(mp, encoding="utf-8"))
    names = set()
    for p in data.get("plugins", []):
        for s in p.get("skills", []):
            names.add(os.path.basename(s.rstrip("/")))
    return names


def scan_refs(project_root, files, registered):
    for rel in files:
        path = os.path.join(project_root, rel)
        if not os.path.isfile(path):
            continue
        for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
            for name in REF.findall(line):
                if name not in registered:
                    print(f"WARN\t{rel}:{i}\t등록되지 않은 스킬 참조 '/hams:{name}' (stale)")


def find_orphans(project_root):
    skills_dir = os.path.join(project_root, "skills")
    if not os.path.isdir(skills_dir):
        return
    for name in sorted(os.listdir(skills_dir)):
        d = os.path.join(skills_dir, name)
        if not os.path.isdir(d):
            continue
        if os.path.isfile(os.path.join(d, "SKILL.md")):
            continue
        tracked = subprocess.run(
            ["git", "-C", project_root, "ls-files", f"skills/{name}/"],
            capture_output=True, text=True).stdout.strip()
        if not tracked:
            print(f"WARN\tskills/{name}\tSKILL.md 없고 추적 파일 0 — orphan 스킬 디렉터리")


def main():
    project_root = sys.argv[1]
    files = sys.argv[2:]
    registered = registered_skills(project_root)
    scan_refs(project_root, files, registered)
    find_orphans(project_root)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest skills/ssot/extractors/test_skill_registry_check.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add skills/ssot/extractors/skill_registry_check.py skills/ssot/extractors/test_skill_registry_check.py
git commit -m "feat(ssot): 내장 추출기 — 스킬 레지스트리 정합성(참조+orphan)"
```

---

### Task 4: 추출기 runner + 리포트 (계약 머지)

**Files:**
- Modify: `skills/ssot/ssot.py`
- Test: `skills/ssot/test_ssot.py`

- [ ] **Step 1: Write the failing test**

```python
# append to skills/ssot/test_ssot.py
import stat as _stat

def test_run_extractors_merges_stdout(tmp_path):
    seam = tmp_path / "ext.sh"
    seam.write_text('#!/usr/bin/env bash\nprintf "WARN\\tfoo.md:3\\thi\\n"\n', encoding="utf-8")
    os.chmod(seam, os.stat(seam).st_mode | _stat.S_IEXEC)
    findings = ssot.run_extractors(str(tmp_path), ["foo.md"], [str(seam)])
    assert ssot.Finding("WARN", "foo.md:3", "hi") in findings


def test_format_report_groups_by_severity():
    out = ssot.format_report([
        ssot.Finding("ERROR", "a:1", "broken"),
        ssot.Finding("WARN", "b:2", "drift"),
    ])
    assert "🔴" in out and "broken" in out and "⚠️" in out and "drift" in out


def test_format_report_clean():
    assert "✅" in ssot.format_report([])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest skills/ssot/test_ssot.py -k "extractors or report" -v`
Expected: FAIL with `AttributeError: ... 'run_extractors'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to skills/ssot/ssot.py
def parse_finding_line(line):
    parts = line.rstrip("\n").split("\t")
    if len(parts) != 3 or parts[0] not in ("ERROR", "WARN"):
        return None
    return Finding(parts[0], parts[1], parts[2])


def discover_extractors(project_root, builtin_dir):
    found = [os.path.join(builtin_dir, "skill_registry_check.py")]
    seam = os.path.join(project_root, ".hamstern", "ssot-extractors")
    if os.path.isdir(seam):
        for f in sorted(os.listdir(seam)):
            if f.endswith(".sh"):
                found.append(os.path.join(seam, f))
    return found


def run_extractors(project_root, ssot_files, extractor_paths):
    findings = []
    for ext in extractor_paths:
        cmd = ([sys.executable, ext] if ext.endswith(".py") else ["bash", ext])
        proc = subprocess.run(cmd + [project_root, *ssot_files],
                              capture_output=True, text=True)
        for line in proc.stdout.splitlines():
            f = parse_finding_line(line)
            if f:
                findings.append(f)
    return findings


def format_report(findings):
    if not findings:
        return "✅ SSOT freshness: 이상 없음"
    icon = {"ERROR": "🔴", "WARN": "⚠️"}
    lines = ["SSOT freshness 리포트 (advisory):"]
    for f in findings:
        lines.append(f"  {icon[f.severity]} {f.location} · {f.message}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest skills/ssot/test_ssot.py -k "extractors or report" -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add skills/ssot/ssot.py skills/ssot/test_ssot.py
git commit -m "feat(ssot): 추출기 runner + advisory 리포트 (계약 머지)"
```

---

### Task 5: 서브커맨드 dispatch (set/list/check) + main

**Files:**
- Modify: `skills/ssot/ssot.py`
- Test: `skills/ssot/test_ssot.py`

- [ ] **Step 1: Write the failing test**

```python
# append to skills/ssot/test_ssot.py
def test_cmd_set_writes_paths_and_repo_url(tmp_path, monkeypatch):
    home = _make_hamstern_data(tmp_path)
    monkeypatch.setenv("HOME", str(home)); monkeypatch.setenv("USERPROFILE", str(home))
    proj = tmp_path / "proj"; proj.mkdir()
    monkeypatch.setattr(ssot, "project_root", lambda: str(proj))
    monkeypatch.setattr(ssot, "repo_url", lambda: "https://github.com/o/r")
    ssot.cmd_set([".claude/rules/*.md", "docs/PRD.md"])
    meta = ssot.load_meta(ssot.resolve_active_project())
    assert meta["ssot_paths"] == [".claude/rules/*.md", "docs/PRD.md"]
    assert meta["repo_url"] == "https://github.com/o/r"


def test_cmd_check_returns_findings(tmp_path, monkeypatch, capsys):
    home = _make_hamstern_data(tmp_path)
    monkeypatch.setenv("HOME", str(home)); monkeypatch.setenv("USERPROFILE", str(home))
    proj = tmp_path / "proj"; (proj / "docs").mkdir(parents=True)
    monkeypatch.setattr(ssot, "project_root", lambda: str(proj))
    active = ssot.resolve_active_project()
    meta = ssot.load_meta(active); meta["ssot_paths"] = ["missing/*.md"]
    ssot.save_meta(active, meta)
    monkeypatch.setattr(ssot, "discover_extractors", lambda r, b: [])
    ssot.cmd_check()
    assert "🔴" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest skills/ssot/test_ssot.py -k "cmd_set or cmd_check" -v`
Expected: FAIL with `AttributeError: ... 'cmd_set'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to skills/ssot/ssot.py
def project_root():
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("❌ git 저장소 안에서 실행하세요 (project_root 해석 실패).")
    return out.stdout.strip()


def repo_url():
    out = subprocess.run(["git", "remote", "get-url", "origin"],
                         capture_output=True, text=True)
    url = out.stdout.strip() if out.returncode == 0 else ""
    if url.startswith("git@"):  # git@github.com:o/r.git → https
        url = "https://" + url[4:].replace(":", "/", 1)
    return url[:-4] if url.endswith(".git") else url


def cmd_set(globs):
    active = resolve_active_project()
    meta = load_meta(active)
    meta["ssot_paths"] = list(globs)
    url = repo_url()
    if url:
        meta["repo_url"] = url
    save_meta(active, meta)
    print(f"✅ SSOT 경로 {len(globs)}개 저장" + (f" · repo_url={url}" if url else ""))


def cmd_list():
    active = resolve_active_project()
    meta = load_meta(active)
    paths = meta.get("ssot_paths", [])
    print(f"repo_url: {meta.get('repo_url', '(없음)')}")
    if not paths:
        print("SSOT 경로 미설정 — /hams:ssot set <글로브…>")
        return
    root = project_root()
    for pat in paths:
        ok = any(os.path.isfile(h) for h in glob.glob(os.path.join(root, pat), recursive=True))
        print(f"  {'✅' if ok else '🔴'} {pat}")


def cmd_check():
    active = resolve_active_project()
    meta = load_meta(active)
    paths = meta.get("ssot_paths", [])
    if not paths:
        print("SSOT 경로 미설정 — /hams:ssot set 먼저.")
        return
    root = project_root()
    findings = check_pointers(root, paths)
    files = resolve_globs(root, paths)
    builtin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extractors")
    findings += run_extractors(root, files, discover_extractors(root, builtin_dir))
    print(format_report(findings))


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "set":
        cmd_set(argv[2:])
    elif cmd == "list":
        cmd_list()
    elif cmd == "check":
        cmd_check()
    else:
        sys.exit("Usage: ssot.py {set <globs…>|list|check}")


if __name__ == "__main__":
    main(sys.argv)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest skills/ssot/test_ssot.py -v`
Expected: PASS (전체 통과)

- [ ] **Step 5: Commit**

```bash
git add skills/ssot/ssot.py skills/ssot/test_ssot.py
git commit -m "feat(ssot): set/list/check 서브커맨드 + main dispatch"
```

---

### Task 6: SKILL.md 작성 + 매니페스트 등록 + 버전 bump

**Files:**
- Create: `skills/ssot/SKILL.md`
- Modify: `.claude-plugin/marketplace.json` (skills 배열 + metadata.version), `.claude-plugin/plugin.json` (version)

- [ ] **Step 1: SKILL.md 작성**

```markdown
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
```

- [ ] **Step 2: marketplace.json — skills 배열에 등록 + 버전 bump**

`.claude-plugin/marketplace.json`의 `plugins[0].skills` 배열 끝에 `"./skills/ssot"` 추가, `metadata.version`을 `"1.3.0"` → `"1.4.0"`.

```json
        "./skills/lec",
        "./skills/ssot"
```
```json
  "metadata": {
    "description": "hamstern 프로젝트 관리 플러그인 (Tier 1-4 회의록, 결정사항, 스킬 추천)",
    "version": "1.4.0"
  },
```

- [ ] **Step 3: plugin.json — version bump**

`.claude-plugin/plugin.json`의 `"version": "1.3.0"` → `"1.4.0"`.

- [ ] **Step 4: 검증**

Run: `python -c "import json; json.load(open('.claude-plugin/marketplace.json')); json.load(open('.claude-plugin/plugin.json')); print('json ok')"`
Expected: `json ok`
Run: `grep -c '"./skills/ssot"' .claude-plugin/marketplace.json`
Expected: `1`

- [ ] **Step 5: Commit**

```bash
git add skills/ssot/SKILL.md .claude-plugin/marketplace.json .claude-plugin/plugin.json
git commit -m "feat(ssot): SKILL.md + 매니페스트 등록 + 1.3.0→1.4.0 bump"
```

---

### Task 7: Dogfood — hamstern 자신에 check 실행 (탐지 확인)

**Files:** (코드 변경 없음 — 실제 실행 검증)

- [ ] **Step 1: active 프로젝트가 hamstern repo로 바인딩됐는지 확인**

Run: `python3 -c "import json,os; c=json.load(open(os.path.expanduser('~/.config/hamstern/active-project.json'))); print(c['name'])"`
Expected: 프로젝트 이름 출력. hamstern repo용 프로젝트가 없으면 먼저 `/hams:init`로 생성하거나 기존 프로젝트에 `/hams:link`.

- [ ] **Step 2: SSOT 경로 등록 (hamstern repo 루트에서)**

Run: `python3 skills/ssot/ssot.py set "skills/**/SKILL.md" "skills/**/*.sh" "docs/conventions.md"`
Expected: `✅ SSOT 경로 3개 저장 · repo_url=https://github.com/edu-openskill/hamstern`

- [ ] **Step 3: check 실행 — record/remind 잔재 + orphan 탐지 확인**

Run: `python3 skills/ssot/ssot.py check`
Expected: ⚠️ findings — `/hams:record`·`/hams:remind` 참조 (audit-decisions/audit.sh, context-save, init, link, save-mockup의 SKILL.md, docs/conventions.md) + `skills/record` orphan. 최소 1건 이상 ⚠️ 가 record/remind/skills/record 를 가리켜야 함.

- [ ] **Step 4: 탐지 결과 기록**

탐지된 finding 목록을 다음 Task의 수정 대상으로 사용. (리포트 출력을 복사해 둔다.)

- [ ] **Step 5: 커밋 없음** (실행 검증 단계)

---

### Task 8: 정리 — record/remind 잔재 제거 (탐지→수정 루프 완결)

**Files:**
- Modify: Task 7이 탐지한 각 파일 (`skills/audit-decisions/audit.sh`, `skills/context-save/SKILL.md`, `skills/init/SKILL.md`, `skills/link/SKILL.md`, `skills/save-mockup/SKILL.md`, `docs/conventions.md`)
- Delete: `skills/record/`

- [ ] **Step 1: 각 파일의 `/hams:record`·`/hams:remind` 참조를 현행 스킬명으로 교체**

각 finding 위치를 열어, 문맥에 맞게 교체: `/hams:record` → `/hams:context-save`, `/hams:remind` → `/hams:context-resume`(세션 환기) 또는 `/hams:context-decisions`(결정만). 의미가 "결정 누적 기록"이면 context-save, "이전 세션 환기"면 context-resume.

확인용 Run: `grep -rn "hams:record\|hams:remind" skills/ docs/conventions.md`
교체 전 위치 파악 → 교체 후 재실행 시 0건이어야 함 (단, `docs/discussions/`·`docs/plans/`의 과거 문서는 SSOT 글로브에 없으므로 손대지 않음 — 이력 보존).

- [ ] **Step 2: orphan record 디렉터리 삭제**

Run: `git rm -r --cached skills/record 2>/dev/null; rm -rf skills/record`
Expected: `skills/record/` 제거 (추적 파일이 없으면 `git rm`은 무시되고 `rm -rf`로 로컬 정리)

- [ ] **Step 3: check 재실행 — ✅ 확인**

Run: `python3 skills/ssot/ssot.py check`
Expected: record/remind/orphan 관련 ⚠️ 가 사라짐. (다른 SSOT 파일에 잔여 드리프트가 없으면 `✅ SSOT freshness: 이상 없음`)

- [ ] **Step 4: 전체 테스트 재확인**

Run: `python -m pytest skills/ssot/ -v`
Expected: 전체 PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix(ssot): record/remind 잔재 정리 + orphan record/ 삭제 (dogfood)"
```

---

## 합격 기준 (Definition of Done)

- [ ] `/hams:ssot` set/list/check 동작, marketplace.json 등록 + plugin.json·marketplace metadata 1.4.0
- [ ] meta.json에 ssot_paths·repo_url 저장, 로컬 경로 런타임 해석
- [ ] 검사0이 깨진 글로브를 🔴로 검출
- [ ] 내장 추출기가 record/remind 참조 + orphan record/ 를 ⚠️로 검출 (dogfood)
- [ ] 로컬 seam(`.hamstern/ssot-extractors/*.sh`) 발견·실행·머지 (Task 4 테스트)
- [ ] record/remind 잔재 정리 완료 → 재실행 ✅
- [ ] `python -m pytest skills/ssot/ -v` 전체 통과
```
