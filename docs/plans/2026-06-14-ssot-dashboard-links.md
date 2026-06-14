# SSOT Dashboard Links (sub-project C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** hamstern 대시보드 per-project view에 그 프로젝트의 SSOT 문서로 가는 GitHub 링크(SSOT 탭)를 추가한다 — 문서 복사 없이 원본 링크만.

**Architecture:** `build.py`가 `meta.json`의 `ssot_paths`·`repo_url`을 읽어 per-project manifest에 `ssot` 링크 엔트리를 추가(구체경로→blob/HEAD, 글로브→tree/HEAD/prefix). `app.js`가 per-project view에 SSOT 탭을 렌더(📄/📁, 빈 경우 "없음"). 복사 없음.

**Tech Stack:** Python 3 (stdlib), 정적 JS(app.js)+HTML, pytest. 레퍼런스: `skills/dashboard/build.py`·`test_build.py`, `docs/app.js`(renderMockupsList), `docs/p/_project.html`(탭 구조).

**Base:** repo `edu-openskill/hamstern`, branch `feat/ssot-dashboard-links`. 스펙: `docs/discussions/2026-06-14-ssot-dashboard-links-design.md`.

---

## File Structure

| 파일 | 변경 | 책임 |
|---|---|---|
| `skills/dashboard/build.py` | 수정 | `_static_prefix`·`_ssot_entries` 헬퍼 + `run_single_project`에 `manifest["ssot"]` 추가 |
| `skills/dashboard/test_build.py` | 수정 | `_ssot_entries`·run_single_project ssot 테스트 |
| `docs/p/_project.html` | 수정 | SSOT 탭 버튼 + `#ssot-list` 섹션 |
| `docs/app.js` | 수정 | `renderSsotList()` + `loadProject`에서 호출 |
| `docs/style.css` | 수정 | `.ssot-item` 스타일 (mockup-item 미러) |
| `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json` | 수정 | 1.4.0 → 1.5.0 |

**ssot 엔트리 형식:** `{"label": str, "url": str|None, "kind": "file"|"glob"}`.

---

### Task 1: build.py — manifest에 ssot 링크 엔트리 (TDD)

**Files:**
- Modify: `skills/dashboard/build.py`
- Test: `skills/dashboard/test_build.py`

- [ ] **Step 1: Write the failing test** — append to `skills/dashboard/test_build.py`:

```python
def test_ssot_entries_concrete_and_glob():
    meta = {"ssot_paths": ["docs/PRD.md", "skills/**/SKILL.md"],
            "repo_url": "https://github.com/o/r"}
    entries = build._ssot_entries(meta)
    assert entries == [
        {"label": "docs/PRD.md",
         "url": "https://github.com/o/r/blob/HEAD/docs/PRD.md", "kind": "file"},
        {"label": "skills/**/SKILL.md",
         "url": "https://github.com/o/r/tree/HEAD/skills", "kind": "glob"},
    ]


def test_ssot_entries_no_repo_url_gives_none():
    meta = {"ssot_paths": ["docs/PRD.md"]}
    assert build._ssot_entries(meta) == [
        {"label": "docs/PRD.md", "url": None, "kind": "file"}]


def test_ssot_entries_empty_when_no_paths():
    assert build._ssot_entries({}) == []


def test_ssot_glob_at_root_prefix_empty():
    meta = {"ssot_paths": ["*.md"], "repo_url": "https://github.com/o/r"}
    assert build._ssot_entries(meta) == [
        {"label": "*.md", "url": "https://github.com/o/r/tree/HEAD", "kind": "glob"}]


def test_run_single_project_includes_ssot_from_meta(tmp_path):
    src = tmp_path / "proj"
    src.mkdir()
    (src / "meta.json").write_text(json.dumps(
        {"ssot_paths": ["docs/PRD.md"], "repo_url": "https://github.com/o/r"}),
        encoding="utf-8")
    out = tmp_path / "out"
    manifest = build.run_single_project(src, out)
    assert manifest["ssot"] == [
        {"label": "docs/PRD.md",
         "url": "https://github.com/o/r/blob/HEAD/docs/PRD.md", "kind": "file"}]


def test_run_single_project_ssot_empty_without_meta(tmp_path):
    src = tmp_path / "proj"; src.mkdir()
    out = tmp_path / "out"
    manifest = build.run_single_project(src, out)
    assert manifest["ssot"] == []
```

- [ ] **Step 2: Run, verify FAIL**

Run: `python -m pytest skills/dashboard/test_build.py -k ssot -v`
Expected: FAIL (`AttributeError: module ... has no attribute '_ssot_entries'`)

- [ ] **Step 3: Implement** — in `skills/dashboard/build.py`, add helpers after the imports/constants (before `run_single_project`):

```python
def _static_prefix(pattern: str) -> str:
    segs = []
    for seg in pattern.split("/"):
        if "*" in seg:
            break
        segs.append(seg)
    return "/".join(segs)


def _ssot_entries(meta: dict) -> list:
    paths = meta.get("ssot_paths") or []
    repo_url = meta.get("repo_url")
    entries = []
    for p in paths:
        if "*" in p:
            prefix = _static_prefix(p)
            url = (f"{repo_url}/tree/HEAD/{prefix}".rstrip("/")
                   if repo_url else None)
            entries.append({"label": p, "url": url, "kind": "glob"})
        else:
            url = f"{repo_url}/blob/HEAD/{p}" if repo_url else None
            entries.append({"label": p, "url": url, "kind": "file"})
    return entries
```

  Then in `run_single_project`, add `"ssot": []` to the initial `manifest` dict (after `"mockups": []`), and after the mockups block (just before writing `manifest.json`) insert:

```python
    # Sub-F: SSOT 링크 (meta.json — 복사 없이 GitHub 링크만)
    meta_src = src_dir / "meta.json"
    meta = {}
    if meta_src.is_file():
        try:
            meta = json.loads(meta_src.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            meta = {}
    manifest["ssot"] = _ssot_entries(meta)
```

- [ ] **Step 4: Run, verify PASS**

Run: `python -m pytest skills/dashboard/test_build.py -v`
Expected: PASS (기존 테스트 + 6 신규 모두 통과)

- [ ] **Step 5: Commit**

```bash
git add skills/dashboard/build.py skills/dashboard/test_build.py
git commit -m "feat(dashboard): manifest에 SSOT 링크 엔트리 (meta.json → blob/tree)"
```

---

### Task 2: _project.html — SSOT 탭 + 컨테이너

**Files:**
- Modify: `docs/p/_project.html`

- [ ] **Step 1: 탭 버튼 추가** — `docs/p/_project.html`의 `<nav class="tabs" id="tabs">` 안, `<button data-tab="mockups">Mockups</button>` 다음 줄에 추가:

```html
  <button data-tab="ssot">SSOT</button>
```

- [ ] **Step 2: 섹션 추가** — `<section class="col col-mockups" ...>...</section>` 블록 다음에 추가:

```html
  <section class="col col-ssot" data-tab="ssot">
    <h2>SSOT 문서</h2>
    <div id="ssot-list"><div class="empty">…</div></div>
  </section>
```

- [ ] **Step 3: 탭 전환 동작 확인** — 기존 탭 핸들러가 `data-tab`로 일반 동작하는지 확인.

Run: `grep -nE "data-tab|\\.tabs|querySelectorAll" docs/app.js`
Expected: 탭 전환이 `[data-tab]`를 일반적으로 토글하는 핸들러임을 확인(하드코딩된 4탭 목록이 아니라면 그대로 동작). 만약 탭 목록이 하드코딩돼 있으면 `ssot`를 그 목록에 추가.

- [ ] **Step 4: Commit**

```bash
git add docs/p/_project.html
git commit -m "feat(dashboard): per-project view에 SSOT 탭 + #ssot-list 컨테이너"
```

---

### Task 3: app.js — renderSsotList + loadProject 호출

**Files:**
- Modify: `docs/app.js`

- [ ] **Step 1: renderSsotList 추가** — `docs/app.js`의 `renderMockupsList` 함수 바로 다음에 추가:

```javascript
function renderSsotList(ssot) {
  const el = document.getElementById('ssot-list');
  if (!el) return; // page doesn't have ssot column
  if (!ssot || ssot.length === 0) {
    renderEmpty(el, 'SSOT 문서 없음');
    return;
  }
  let html = '';
  for (const e of ssot) {
    const icon = e.kind === 'glob' ? '📁' : '📄';
    const label = DOMPurify.sanitize(e.label);
    if (e.url) {
      const url = DOMPurify.sanitize(e.url);
      html += `<a href="${url}" target="_blank" class="ssot-item">${icon} ${label}</a>`;
    } else {
      html += `<div class="ssot-item ssot-nolink">${icon} ${label}</div>`;
    }
  }
  el.innerHTML = html;
}
```

- [ ] **Step 2: loadProject에서 호출** — `docs/app.js`의 `loadProject(uuid)` 안, mockups 렌더 호출(`renderMockupsList(...)`) 다음 줄에 추가:

```javascript
  renderSsotList(manifest.ssot);
```

(`renderMockupsList(...)` 호출 위치를 `grep -n "renderMockupsList(" docs/app.js`로 찾아 그 바로 다음에 삽입.)

- [ ] **Step 3: 통합 검증** — 샘플 데이터로 manifest 생성 후 렌더 확인:

```bash
python - <<'PY'
import json, tempfile, pathlib
from skills.dashboard import build
src = pathlib.Path(tempfile.mkdtemp()) / "proj"; src.mkdir()
(src / "meta.json").write_text(json.dumps(
    {"ssot_paths": ["docs/PRD.md", "skills/**/SKILL.md"],
     "repo_url": "https://github.com/o/r"}), encoding="utf-8")
out = pathlib.Path(tempfile.mkdtemp())
m = build.run_single_project(src, out)
print(json.dumps(m["ssot"], ensure_ascii=False, indent=2))
PY
```
Expected: ssot 엔트리 2개 출력(file=blob, glob=tree). app.js의 `renderSsotList`가 이 구조(`label`/`url`/`kind`)를 그대로 소비하는지 코드 확인.

- [ ] **Step 4: Commit**

```bash
git add docs/app.js
git commit -m "feat(dashboard): renderSsotList — SSOT 탭에 GitHub 링크 렌더"
```

---

### Task 4: style.css + 버전 bump

**Files:**
- Modify: `docs/style.css`, `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`

- [ ] **Step 1: .ssot-item 스타일** — `docs/style.css`에서 `.mockup-item` 규칙을 찾아(`grep -n "mockup-item" docs/style.css`) 그 근처에 추가:

```css
.ssot-item {
  display: block;
  padding: 8px 12px;
  margin-bottom: 6px;
  border: 1px solid var(--border, #2a3550);
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
}
.ssot-item:hover { background: var(--hover, #1a2440); }
.ssot-nolink { opacity: 0.6; cursor: default; }
```

(`--border`/`--hover` 변수가 style.css에 없으면 `.mockup-item`이 쓰는 실제 색·변수에 맞춰 동일 톤으로 조정.)

- [ ] **Step 2: 버전 bump** — `.claude-plugin/marketplace.json`의 `metadata.version` `1.4.0`→`1.5.0`, `.claude-plugin/plugin.json`의 `version` `1.4.0`→`1.5.0`.

- [ ] **Step 3: 검증**

Run: `python -c "import json; assert json.load(open('.claude-plugin/marketplace.json'))['metadata']['version']=='1.5.0'; assert json.load(open('.claude-plugin/plugin.json'))['version']=='1.5.0'; print('OK 1.5.0')"`
Expected: `OK 1.5.0`
Run: `python -m pytest skills/dashboard/ -v`
Expected: 전체 PASS (회귀 없음)

- [ ] **Step 4: Commit**

```bash
git add docs/style.css .claude-plugin/marketplace.json .claude-plugin/plugin.json
git commit -m "feat(dashboard): .ssot-item 스타일 + 1.4.0→1.5.0 bump"
```

---

## 합격 기준 (Definition of Done)

- [ ] `build._ssot_entries`가 구체경로→blob/HEAD, 글로브→tree/HEAD/prefix, repo_url 없음→url None, 경로 없음→[] 생성
- [ ] `run_single_project`가 manifest["ssot"]를 meta.json에서 채움 (meta.json 없으면 [])
- [ ] `_project.html`에 SSOT 탭 + `#ssot-list`
- [ ] `app.js renderSsotList`가 📄/📁 링크 렌더, 빈 경우 "SSOT 문서 없음", url null→plain text, DOMPurify·target=_blank
- [ ] `test_build.py` ssot 테스트 통과 + dashboard 스위트 회귀 없음
- [ ] plugin.json·marketplace.json 1.5.0
- [ ] 문서 복사 0 (manifest엔 url만)
