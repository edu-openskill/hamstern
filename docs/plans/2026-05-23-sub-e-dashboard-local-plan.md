# Sub-project E — Dashboard Per-Project Local Serve Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/hams:dashboard` 기본 동작을 로컬 serve 로 전환. `--publish` 시 Sub-D 의 gh-pages 흐름. 모든 프로젝트에서 외부 의존 0 으로 즉시 동작.

**Architecture:** plugin install 경로의 정적 자산 (`docs/{index,app,style}`, Sub-D 산출물) + 프로젝트 로컬 데이터 (`{project}/.hamstern/dashboard-data/`) 를 작은 커스텀 Python 핸들러 (`skills/dashboard/serve.py`) 가 path 분기로 동시 serve. Background server, 동적 포트, PID 추적으로 idempotent restart.

**Tech Stack:** Python 3 (stdlib only — http.server, socket, argparse, pathlib). Sub-D 의 build.py 재사용. 외부 의존 0.

**Reference Spec:** `docs/discussions/2026-05-23-sub-e-dashboard-local-design.md` (commit `f24a666`)

---

## 파일 구조 결정

| 경로 | 작성/수정 | 책임 |
|---|---|---|
| `skills/dashboard/serve.py` | **신규** | 커스텀 핸들러 + 동적 포트 + CLI. ≤ 100 줄 stdlib. |
| `skills/dashboard/test_serve.py` | **신규** | 9 pytest 케이스 (translate_path + traversal + pick_port + e2e) |
| `skills/dashboard/SKILL.md` | **재작성** | 두 모드 (local 기본 / --publish) |
| `skills/dashboard/build.py` | 변경 없음 | Sub-D 그대로. `--out` 인자로 출력 경로 가변. |
| `skills/dashboard/test_build.py` | 변경 없음 | Sub-D 의 6 케이스 그대로 |
| `docs/index.html`, `docs/app.js`, `docs/style.css` | 변경 없음 | Sub-D 자산 그대로 |
| `docs/data/manifest.json` | 변경 없음 | plugin 자체 demo bundle (publish 용) |
| `README.md` | 수정 | dashboard 섹션 갱신 + Sub-E changelog |
| `docs/conventions.md` | 수정 | dashboard 항목 두 모드 표기 |
| `docs/plans/2026-05-23-sub-e-dashboard-local-verification.md` | **신규 (마지막)** | UAT 결과 |

### 환경 사실 (plan 작성 시점 검증)

- `$CLAUDE_PLUGIN_ROOT` 는 **현재 환경에서 비어있음** — env var 기반 discovery 사용 불가.
- 실제 plugin 설치 경로: `~/.claude/plugins/cache/hamstern/hams/<hash>/`.
- SKILL.md 의 plugin path discovery 는 glob fallback 으로 결정. Task 1 의 helper snippet 으로 표준화.

---

## Task 1: Plugin path discovery helper 결정

**Files:** (코드 변경 없음 — discovery 표준 확정)

- [ ] **Step 1: 현재 환경의 plugin 설치 경로 확인**

Run:
```
ls -d ~/.claude/plugins/cache/hamstern/hams/*/ 2>/dev/null
```

Expected: 1줄 출력 (예: `/c/Users/ssarm/.claude/plugins/cache/hamstern/hams/b1146da6b548/`).

만약 0줄이면 STOP — plugin 미설치. Sub-E 가 동작할 environment 가 아니므로 BLOCKED 보고.
만약 2줄 이상이면 가장 최신 (mtime DESC) 1개 선택하는 정책으로.

- [ ] **Step 2: SKILL.md 가 사용할 discovery 한 줄 helper 결정**

다음 Python one-liner 를 표준으로 사용:

```bash
PLUGIN_DIR=$(python3 -c "from pathlib import Path; ps=sorted(Path.home().glob('.claude/plugins/cache/hamstern/hams/*/'), key=lambda p: p.stat().st_mtime, reverse=True); print(str(ps[0]) if ps else '', end='')")
if [ -z "$PLUGIN_DIR" ]; then echo "hamstern plugin not installed under ~/.claude/plugins/cache/hamstern/" >&2; exit 1; fi
```

- 가장 최근 mtime 의 hamstern hash 디렉터리를 선택 (다중 install 시)
- 0개면 stderr + exit 1
- `print(..., end='')` 로 trailing newline 제거

검증:
```
PLUGIN_DIR=$(python3 -c "from pathlib import Path; ps=sorted(Path.home().glob('.claude/plugins/cache/hamstern/hams/*/'), key=lambda p: p.stat().st_mtime, reverse=True); print(str(ps[0]) if ps else '', end='')")
echo "PLUGIN_DIR=$PLUGIN_DIR"
ls "$PLUGIN_DIR/skills/dashboard/" 2>&1 | head -5
```

Expected: 비어있지 않은 경로 + 그 안의 `skills/dashboard/` 디렉터리 내용 (현재 cache 는 stale — pre-Sub-C 상태일 수 있음; 그래도 디렉터리는 존재).

- [ ] **Step 3: 코드 변경 없으니 commit 없음** — 본 task 는 SKILL.md 의 Step 9-10 에서 사용될 정확한 명령 문자열을 결정하는 용도. plan 문서 자체에 이미 포함.

---

## Task 2: `serve.py` 스켈레톤 + 첫 실패 테스트 (`/`)

**Files:**
- Create: `skills/dashboard/test_serve.py`
- Create: `skills/dashboard/serve.py`

- [ ] **Step 1: test_serve.py 작성 (첫 실패 테스트)**

```python
# skills/dashboard/test_serve.py
"""Layer 2 regression for /hams:dashboard local serve.

serve.py 는 plugin 정적 자산 + project 데이터 디렉터리를 path 분기로 동시 serve.
"""
import importlib.util
from pathlib import Path

_HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("dashboard_serve", _HERE / "serve.py")
serve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serve)


def _make_handler(plugin_dir: Path, data_dir: Path):
    """HamsHandler 의 class-level 속성을 주입한 서브클래스 반환 (인스턴스화 없이 translate_path 단위 호출용)."""
    class _H(serve.HamsHandler):
        pass
    _H.plugin_dir = plugin_dir
    _H.data_dir = data_dir
    return _H


def test_translate_root_returns_plugin_index(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir()
    data_dir.mkdir()
    (plugin_dir / "index.html").write_text("<html>plugin index</html>", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    # translate_path 는 instance method 지만 self 의 plugin_dir/data_dir 만 참조하므로
    # 더미 인스턴스 없이 unbound method 로 호출 가능하게 staticmethod-스타일 검증:
    # SimpleHTTPRequestHandler.translate_path 는 self.directory 를 사용하지 않으면 staticmethod 처럼 동작
    # 우리 구현은 self 의 클래스 속성만 보므로 None self 로 호출 가능
    result = H.translate_path(None, "/")  # type: ignore[arg-type]
    assert Path(result) == plugin_dir / "index.html"
```

- [ ] **Step 2: 실패 확인**

Run:
```
cd hamstern-plugin
python3 -m pytest skills/dashboard/test_serve.py::test_translate_root_returns_plugin_index -v
```

Expected: ModuleNotFoundError / FileNotFoundError 또는 import 실패 (serve.py 없음).

- [ ] **Step 3: serve.py 최소 구현**

```python
# skills/dashboard/serve.py
"""hamstern /hams:dashboard 의 local serve 모드.

plugin 정적 자산 (docs/{index,app,style}) + project 데이터 (.hamstern/dashboard-data/) 를
path 분기로 동시 serve. 동적 포트 (OS 할당). Stdlib only.
"""
from __future__ import annotations

import argparse
import socket
import sys
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path


class HamsHandler(SimpleHTTPRequestHandler):
    plugin_dir: Path = None  # 클래스 속성으로 main() 에서 주입
    data_dir: Path = None

    def translate_path(self, path: str) -> str:
        # 쿼리·앵커 제거
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path in ("/", ""):
            path = "/index.html"
        rel = path.lstrip("/")
        return str(self.plugin_dir / rel)

    def log_message(self, fmt, *args):
        pass  # 콘솔 silent
```

- [ ] **Step 4: 통과 확인**

Run:
```
python3 -m pytest skills/dashboard/test_serve.py -v
```

Expected: 1 passed.

- [ ] **Step 5: commit**

```
git add skills/dashboard/serve.py skills/dashboard/test_serve.py
git commit -m "feat(dashboard): serve.py skeleton + root path test (Sub-E)"
```

---

## Task 3: `/app.js` + `/style.css` 분기

**Files:**
- Modify: `skills/dashboard/test_serve.py`

(이미 Task 2 의 구현이 이 분기를 자연스럽게 지원함 — `/app.js` → `plugin_dir/app.js`. 테스트만 추가해 회귀 방지.)

- [ ] **Step 1: 두 테스트 추가**

`test_serve.py` 끝에:

```python
def test_translate_app_js_returns_plugin_app_js(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (plugin_dir / "app.js").write_text("// app", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/app.js")
    assert Path(result) == plugin_dir / "app.js"


def test_translate_style_css_returns_plugin_style_css(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (plugin_dir / "style.css").write_text("body{}", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/style.css")
    assert Path(result) == plugin_dir / "style.css"
```

- [ ] **Step 2: 두 테스트 통과 확인**

```
python3 -m pytest skills/dashboard/test_serve.py -v
```

Expected: 3 passed.

- [ ] **Step 3: commit**

```
git add skills/dashboard/test_serve.py
git commit -m "test(dashboard): serve.py /app.js + /style.css regression (Sub-E)"
```

---

## Task 4: `/data/*` 분기 → data_dir 로

**Files:**
- Modify: `skills/dashboard/test_serve.py`
- Modify: `skills/dashboard/serve.py`

- [ ] **Step 1: 두 실패 테스트 추가**

```python
def test_translate_data_manifest_returns_data_dir(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (data_dir / "manifest.json").write_text("{}", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/data/manifest.json")
    assert Path(result) == data_dir / "manifest.json"


def test_translate_data_sessions_subpath(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (data_dir / "sessions").mkdir()
    (data_dir / "sessions" / "foo.md").write_text("# foo", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/data/sessions/foo.md")
    assert Path(result) == data_dir / "sessions" / "foo.md"
```

- [ ] **Step 2: 실패 확인**

```
python3 -m pytest skills/dashboard/test_serve.py::test_translate_data_manifest_returns_data_dir -v
```

Expected: FAIL — 현 구현은 모든 경로를 plugin_dir 에 매핑.

- [ ] **Step 3: serve.py 의 translate_path 에 /data/ 분기 추가**

`translate_path` 의 path 정규화 직후, `if path in ("/", "")` 이전에:

```python
        if path.startswith("/data/"):
            rel = path[len("/data/"):]
            return str(self.data_dir / rel)
```

전체 메서드 모양:
```python
    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path.startswith("/data/"):
            rel = path[len("/data/"):]
            return str(self.data_dir / rel)
        if path in ("/", ""):
            path = "/index.html"
        rel = path.lstrip("/")
        return str(self.plugin_dir / rel)
```

- [ ] **Step 4: 통과 확인**

```
python3 -m pytest skills/dashboard/test_serve.py -v
```

Expected: 5 passed.

- [ ] **Step 5: commit**

```
git add skills/dashboard/serve.py skills/dashboard/test_serve.py
git commit -m "feat(dashboard): serve.py /data/* routes to data_dir (Sub-E)"
```

---

## Task 5: Path traversal 차단

**Files:**
- Modify: `skills/dashboard/test_serve.py`
- Modify: `skills/dashboard/serve.py`

- [ ] **Step 1: 두 실패 테스트 추가 (traversal)**

```python
def test_translate_blocks_data_traversal(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("forbidden", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    # /data/../../secret.txt 가 secret.txt 로 resolve 되면 안 됨
    result = H.translate_path(None, "/data/../../secret.txt")
    resolved = Path(result).resolve()
    assert secret.resolve() != resolved, "traversal escaped data_dir to access secret"


def test_translate_blocks_root_traversal(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("forbidden", encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    result = H.translate_path(None, "/../secret.txt")
    resolved = Path(result).resolve()
    assert secret.resolve() != resolved, "traversal escaped plugin_dir to access secret"
```

- [ ] **Step 2: 실패 확인**

```
python3 -m pytest skills/dashboard/test_serve.py::test_translate_blocks_data_traversal -v
```

Expected: FAIL — 현 구현은 path string 을 그대로 join 해서 traversal 통과.

- [ ] **Step 3: serve.py 에 traversal guard 추가**

`translate_path` 를 다음으로 교체:

```python
    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path.startswith("/data/"):
            return self._safe_join(self.data_dir, path[len("/data/"):])
        if path in ("/", ""):
            path = "/index.html"
        return self._safe_join(self.plugin_dir, path.lstrip("/"))

    @classmethod
    def _safe_join(cls, base: Path, rel: str) -> str:
        """base 의 자손인지 검증 후 path 반환. 탈출 시 sentinel (존재하지 않는 path) 반환 → 404."""
        candidate = (base / rel).resolve()
        base_resolved = base.resolve()
        try:
            candidate.relative_to(base_resolved)
        except ValueError:
            return str(base_resolved / "__forbidden__")
        return str(candidate)
```

`Path.relative_to` 가 `ValueError` 를 던지면 candidate 가 base 밖이라는 뜻. sentinel `__forbidden__` 은 실제 파일이 없으니 SimpleHTTPRequestHandler 가 404 반환.

- [ ] **Step 4: 통과 확인**

```
python3 -m pytest skills/dashboard/test_serve.py -v
```

Expected: 7 passed.

- [ ] **Step 5: commit**

```
git add skills/dashboard/serve.py skills/dashboard/test_serve.py
git commit -m "feat(dashboard): serve.py path traversal guard (Sub-E)"
```

---

## Task 6: `pick_port()` 동적 포트 할당

**Files:**
- Modify: `skills/dashboard/test_serve.py`
- Modify: `skills/dashboard/serve.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
def test_pick_port_returns_valid_bindable_port():
    p1 = serve.pick_port()
    p2 = serve.pick_port()
    assert 1024 <= p1 <= 65535
    assert 1024 <= p2 <= 65535
    assert isinstance(p1, int) and isinstance(p2, int)

    # 실제 bind 가능한지
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", p1))
    finally:
        s.close()
```

`test_serve.py` 상단 import 에 추가:
```python
import socket
```

- [ ] **Step 2: 실패 확인**

```
python3 -m pytest skills/dashboard/test_serve.py::test_pick_port_returns_valid_bindable_port -v
```

Expected: `AttributeError: module ... has no attribute 'pick_port'`.

- [ ] **Step 3: serve.py 에 pick_port 추가**

`HamsHandler` 클래스 아래 모듈 레벨:

```python
def pick_port() -> int:
    """OS 가 할당한 자유 포트 (ephemeral range)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
```

- [ ] **Step 4: 통과 확인**

```
python3 -m pytest skills/dashboard/test_serve.py -v
```

Expected: 8 passed.

- [ ] **Step 5: commit**

```
git add skills/dashboard/serve.py skills/dashboard/test_serve.py
git commit -m "feat(dashboard): serve.py pick_port helper (Sub-E)"
```

---

## Task 7: CLI entry (`main`)

**Files:**
- Modify: `skills/dashboard/serve.py`

- [ ] **Step 1: serve.py 끝에 main 추가**

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="hamstern dashboard local server")
    parser.add_argument("--plugin-dir", required=True, help="docs/ 자산이 있는 plugin 디렉터리")
    parser.add_argument("--data-dir", required=True, help="build.py 가 만든 .hamstern/dashboard-data/")
    parser.add_argument("--port", type=int, default=0, help="0 = OS 동적 할당")
    args = parser.parse_args()

    HamsHandler.plugin_dir = Path(args.plugin_dir).resolve()
    HamsHandler.data_dir = Path(args.data_dir).resolve()

    if not HamsHandler.plugin_dir.is_dir():
        print(f"plugin-dir not found: {HamsHandler.plugin_dir}", file=sys.stderr)
        sys.exit(1)

    HamsHandler.data_dir.mkdir(parents=True, exist_ok=True)

    port = args.port if args.port else pick_port()
    try:
        server = HTTPServer(("127.0.0.1", port), HamsHandler)
    except OSError as e:
        print(f"failed to bind port {port}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"http://localhost:{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: smoke test (background)**

Run from `hamstern-plugin`:
```
mkdir -p /tmp/serve-smoke-data && echo "{}" > /tmp/serve-smoke-data/manifest.json
python3 skills/dashboard/serve.py --plugin-dir docs --data-dir /tmp/serve-smoke-data &
SMOKE_PID=$!
sleep 1
# URL 출력 캡쳐 어렵지만 PID 살아있는지 확인
kill -0 $SMOKE_PID && echo "server running pid=$SMOKE_PID"
kill $SMOKE_PID
```

Expected: `server running pid=...` 출력.

- [ ] **Step 3: pytest 회귀 확인**

```
python3 -m pytest skills/dashboard/test_serve.py -v
```

Expected: 8 passed (이미 통과한 것들 + main 은 unit test 없음).

- [ ] **Step 4: commit**

```
git add skills/dashboard/serve.py
git commit -m "feat(dashboard): serve.py CLI entry main() (Sub-E)"
```

---

## Task 8: End-to-end HTTPServer 테스트

**Files:**
- Modify: `skills/dashboard/test_serve.py`

- [ ] **Step 1: 9 번째 테스트 추가 (e2e)**

`test_serve.py` 상단 import 에 추가:
```python
import threading
import urllib.request
import time
from http.server import HTTPServer
```

테스트:
```python
def test_e2e_http_server_serves_plugin_and_data(tmp_path):
    plugin_dir = tmp_path / "plugin_docs"
    data_dir = tmp_path / "data"
    plugin_dir.mkdir(); data_dir.mkdir()
    (plugin_dir / "index.html").write_text("<html>idx</html>", encoding="utf-8")
    (plugin_dir / "app.js").write_text("// app", encoding="utf-8")
    (data_dir / "manifest.json").write_text('{"schema_version":1}', encoding="utf-8")

    H = _make_handler(plugin_dir, data_dir)
    port = serve.pick_port()
    server = HTTPServer(("127.0.0.1", port), H)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # /
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2) as r:
            assert r.status == 200
            assert b"idx" in r.read()
        # /app.js
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/app.js", timeout=2) as r:
            assert r.status == 200
            assert b"app" in r.read()
        # /data/manifest.json
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/data/manifest.json", timeout=2) as r:
            assert r.status == 200
            assert b"schema_version" in r.read()
        # traversal → 404
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/data/../../secret", timeout=2)
            assert False, "traversal request should 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
```

`urllib.error` 도 import 필요:
```python
import urllib.error
```

- [ ] **Step 2: 통과 확인**

```
python3 -m pytest skills/dashboard/test_serve.py -v
```

Expected: 9 passed. (실패 시 thread/server lifecycle 디버깅 — `daemon=True` 와 `server.shutdown()` 가 깔끔히 정리하는지.)

- [ ] **Step 3: commit**

```
git add skills/dashboard/test_serve.py
git commit -m "test(dashboard): serve.py end-to-end HTTPServer integration (Sub-E)"
```

---

## Task 9: `skills/dashboard/SKILL.md` 재작성 (두 모드)

**Files:**
- Modify: `skills/dashboard/SKILL.md`

- [ ] **Step 1: SKILL.md 전체 교체**

다음 내용으로 (모든 코드 펜스는 literal triple backticks):

```markdown
---
name: dashboard
description: hamstern dashboard 실행. 기본 = 로컬 serve (모든 프로젝트 즉시 동작). --publish 시 gh-pages 흐름 (Sub-D demo).
---

# /hams:dashboard

`.hamstern/*.md` 를 정적 viewer 로 본다. 두 모드:

| 모드 | 명령 | 데이터 | 자산 출처 | 외부 의존 |
|---|---|---|---|---|
| **local** (기본) | `/hams:dashboard` | `{project}/.hamstern/dashboard-data/` | plugin install 의 `docs/` | 0 |
| **publish** | `/hams:dashboard --publish` | `{project}/docs/data/` | 같음 (commit 됨) | git remote + GitHub Pages |

## 동작 (Claude 가 실행)

### 공통 — plugin 경로 탐지

\`\`\`
PLUGIN_DIR=$(python3 -c "from pathlib import Path; ps=sorted(Path.home().glob('.claude/plugins/cache/hamstern/hams/*/'), key=lambda p: p.stat().st_mtime, reverse=True); print(str(ps[0]) if ps else '', end='')")
if [ -z "$PLUGIN_DIR" ]; then echo "hamstern plugin not installed under ~/.claude/plugins/cache/hamstern/" >&2; exit 1; fi
\`\`\`

가장 최근 mtime 의 hamstern 설치 디렉터리 선택. 없으면 stderr + exit.

### Local 모드 (기본)

1. **이전 인스턴스 정리**
   \`\`\`
   if [ -f .hamstern/dashboard.pid ]; then
     OLD_PID=$(cat .hamstern/dashboard.pid)
     kill -0 "$OLD_PID" 2>/dev/null && kill "$OLD_PID"
     rm -f .hamstern/dashboard.pid .hamstern/dashboard.url
   fi
   \`\`\`

2. **데이터 번들**
   \`\`\`
   python3 "$PLUGIN_DIR/skills/dashboard/build.py" --project . --out .hamstern/dashboard-data
   \`\`\`
   exit 1 시 중단.

3. **서버 background 기동**
   \`\`\`
   python3 "$PLUGIN_DIR/skills/dashboard/serve.py" \
     --plugin-dir "$PLUGIN_DIR/docs" \
     --data-dir .hamstern/dashboard-data \
     > .hamstern/dashboard.url 2>&1 &
   echo $! > .hamstern/dashboard.pid
   \`\`\`

4. **URL 대기 (최대 5초 폴링)**
   \`\`\`
   for i in 1 2 3 4 5; do
     if [ -s .hamstern/dashboard.url ]; then break; fi
     sleep 1
   done
   URL=$(head -1 .hamstern/dashboard.url)
   if [ -z "$URL" ]; then
     echo "server did not emit URL within 5s; output:" >&2
     cat .hamstern/dashboard.url >&2
     exit 1
   fi
   \`\`\`

5. **브라우저 오픈 (플랫폼별)**
   - Windows: `start "$URL"`
   - macOS: `open "$URL"`
   - Linux: `xdg-open "$URL"`

6. **사용자에게 보고**
   \`\`\`
   echo "dashboard live at $URL (pid=$(cat .hamstern/dashboard.pid))"
   \`\`\`

### Publish 모드 (--publish, Sub-D 흐름)

1. **데이터 번들**
   \`\`\`
   python3 "$PLUGIN_DIR/skills/dashboard/build.py" --project . --out docs/data
   \`\`\`

2. **변경 감지 + commit + push**
   \`\`\`
   if [ -n "$(git status --short docs/data/)" ]; then
     git add docs/data/
     git commit -m "chore(dashboard): refresh data $(date -u +%Y-%m-%dT%H:%M:%SZ)"
     git push origin main
   fi
   \`\`\`

3. **gh-pages URL 오픈**
   git remote 에서 owner/repo 추출 → `https://<owner>.github.io/<repo>/`. Windows: `start ...`.

### 1회성 GitHub Pages 활성화 (publish 모드 전제)

repo 의 Settings → Pages → Source: `Deploy from a branch` → Branch: `main` → Folder: `/docs` → Save. ~1-2분 대기.

## 종료 (local 모드)

명시적 stop 명령 없음. 세 경로:
1. 다음 `/hams:dashboard` 호출 시 자동 kill·재시작
2. `kill $(cat .hamstern/dashboard.pid)`
3. 머신 종료

좀비 누적 우려 시 미래에 `/hams:dashboard-stop` 추가 검토.

## 사용자 프로젝트 `.gitignore` 추천

publish 모드 안 쓰는 프로젝트:
\`\`\`
.hamstern/dashboard-data/
.hamstern/dashboard.pid
.hamstern/dashboard.url
\`\`\`

## 편집 흐름

dashboard 는 read-only. `[×]` 클릭 → 클립보드 `/hams:audit-decisions remove "<text>"` → Claude 세션에 붙여넣어 실행 → 다음 `/hams:dashboard` 호출 시 viewer 반영.

## 데이터 매핑

| 모드 | 소스 | 출력 |
|---|---|---|
| local | `.hamstern/decisions.md` | `.hamstern/dashboard-data/decisions.md` |
| local | `.hamstern/decisions-log.md` | `.hamstern/dashboard-data/decisions-log.md` |
| local | `.hamstern/sessions/*.md` | `.hamstern/dashboard-data/sessions/<name>.md` |
| publish | `.hamstern/decisions.md` | `docs/data/decisions.md` |
| publish | `.hamstern/sessions/*.md` | `docs/data/sessions/<name>.md` |
```

- [ ] **Step 2: 사후 sanity grep**

```
grep -n "PLUGIN_DIR" skills/dashboard/SKILL.md   # expect 5+
grep -n "dashboard-data" skills/dashboard/SKILL.md   # expect 6+
grep -n "edu-openskill.github.io" skills/dashboard/SKILL.md   # expect 0 (URL 은 git remote 에서 동적으로 — hardcode 안 함)
grep -n "localhost:7777" skills/dashboard/SKILL.md   # expect 0
grep -n "server.py" skills/dashboard/SKILL.md   # expect 0
```

만약 grep 결과가 예상과 다르면 SKILL.md 내용 점검.

- [ ] **Step 3: commit**

```
git add skills/dashboard/SKILL.md
git commit -m "docs(dashboard): rewrite SKILL.md for two modes (local default + --publish) (Sub-E)"
```

---

## Task 10: README + docs/conventions.md 갱신

**Files:**
- Modify: `README.md`
- Modify: `docs/conventions.md`

- [ ] **Step 1: README.md 의 dashboard 슬래시 표 행 갱신**

```
grep -n "/hams:dashboard" README.md
```

찾은 줄 (현재: `| `/hams:dashboard` | `.hamstern` 스냅샷을 정적 gh-pages 로 publish + viewer 오픈 |`) 을:

`| `/hams:dashboard` | 로컬 dashboard serve (모든 프로젝트 동작). `--publish` 시 gh-pages |`

- [ ] **Step 2: README.md 에 Sub-E changelog 추가**

기존 Sub-D changelog 섹션 ("Sub-project D — Dashboard static gh-pages + browser edit UI (2026-05-23)") 직후에 삽입:

```markdown
### Sub-project E — Dashboard per-project local serve (2026-05-23)

- `/hams:dashboard` 기본 동작을 **로컬 serve** 로 전환 — 모든 프로젝트에서 외부 의존 0 으로 즉시 동작.
- `skills/dashboard/serve.py` 신규 (≤ 80 줄 stdlib) — plugin 정적 자산 (`$PLUGIN/docs/`) + project 데이터 (`{project}/.hamstern/dashboard-data/`) 를 path 분기로 동시 serve.
- 동적 포트 (OS 할당) + background server + PID 추적 → 멀티-프로젝트 dashboard 동시 동작, 포트 충돌 0.
- Path traversal 차단 (`_safe_join` + sentinel path → 404).
- `/hams:dashboard --publish` = Sub-D 의 gh-pages 흐름 보존.
- SKILL.md 의 plugin 경로 탐지: `~/.claude/plugins/cache/hamstern/hams/*/` glob 으로 가장 최근 mtime 선택 (env var `$CLAUDE_PLUGIN_ROOT` 미신뢰).
- 9 pytest 케이스 (translate_path 5 + traversal 2 + pick_port 1 + e2e HTTPServer 1).
```

- [ ] **Step 3: docs/conventions.md 의 dashboard 줄 갱신**

```
grep -n "/hams:dashboard\|dashboard.*publish\|edu-openskill.github.io" docs/conventions.md
```

찾은 줄 (Sub-D 갱신 결과 — `/hams:dashboard — .hamstern/*.md 를 docs/data/ 로 번들 + commit·push 후 https://edu-openskill.github.io/hamstern/ 정적 viewer 오픈 ...`) 을 다음 두 줄로 분할:

```
- `/hams:dashboard` (local 기본) — `.hamstern/*.md` 를 `.hamstern/dashboard-data/` 로 번들 + background 서버 기동 + http://localhost:<dynamic_port>/ 브라우저 오픈. 모든 프로젝트에서 외부 의존 0.
- `/hams:dashboard --publish` — Sub-D 흐름 보존. `docs/data/` 로 번들 + commit·push → `https://<owner>.github.io/<repo>/` 정적 viewer.
```

(원 형식이 markdown 표 행이면 표 행 2개로, list 항목이면 list 항목 2개로 — 주변 형식 따라 조정.)

- [ ] **Step 4: sanity grep**

```
grep -c "Sub-project E" README.md     # expect 1+
grep -c "dashboard-data" docs/conventions.md   # expect 1+
grep -c "Sub-project E" docs/conventions.md   # expect 0 또는 1 — 히스토리 mention 없으면 0 (OK)
```

- [ ] **Step 5: commit**

```
git add README.md docs/conventions.md
git commit -m "docs: README + conventions.md Sub-E updates (Sub-E)"
```

---

## Task 11: 사용자 환경 plugin 캐시 갱신 + Manual UAT + verification.md

**Files:**
- Create: `docs/plans/2026-05-23-sub-e-dashboard-local-verification.md`

### Step 1: push + plugin 캐시 갱신 안내

- [ ] **Step 1a: 모든 Sub-E commit push**

```
cd hamstern-plugin
git log --oneline origin/main..main
git push origin main
```

- [ ] **Step 1b: plugin 캐시 갱신 (사용자 액션)**

Sub-D 직후 시점의 plugin 캐시는 stale (pre-Sub-C 상태 가능성 있음). 사용자에게 다음 중 하나 안내:

옵션 1 — Claude Code 의 plugin update 명령 (정확한 명령은 환경별):
```
# 예: /plugin update hamstern  (Claude Code 가 지원하는 경우)
```

옵션 2 — 캐시 디렉터리 강제 갱신:
```
cd ~/.claude/plugins/cache/hamstern/hams/<HASH>/
git pull origin main
# 또는 캐시 전체 삭제 + Claude 재시작 → 자동 재다운로드
```

옵션 3 — symlink 로 dev tree 를 직접 사용:
```
mv ~/.claude/plugins/cache/hamstern/hams/<HASH> ~/.claude/plugins/cache/hamstern/hams/<HASH>.bak
ln -s ~/workspace/hamstern/hamstern-plugin ~/.claude/plugins/cache/hamstern/hams/<HASH>
```

UAT 진행 전 사용자가 어느 옵션을 선택했는지 명시.

### Step 2: Manual UAT 6 시나리오

- [ ] **시나리오 1 — 빈 프로젝트 (`.hamstern/` 없음) 에서 local 모드**

새 디렉터리:
```
mkdir -p /tmp/test-empty && cd /tmp/test-empty
# /hams:dashboard 호출 (Claude 세션에서)
```

기대:
- `.hamstern/dashboard-data/manifest.json` 생성 (decisions:false, sessions:[])
- 서버 background 기동, URL 출력
- 브라우저에 "결정사항 없음 / 세션 없음 / 로그 없음" fallback 표시

- [ ] **시나리오 2 — 실데이터 프로젝트**

`hamstern-plugin` 자체 디렉터리에서 (만약 plugin 의 `.hamstern/` 비어있다면 record 한두 번 호출 후):
```
# /hams:record 로 임시 결정사항 한두 개 저장 (테스트용)
# /hams:dashboard
```

기대:
- decisions/sessions/log 모두 렌더
- × 클릭 → 클립보드에 정확한 `/hams:audit-decisions remove "..."` 복사

- [ ] **시나리오 3 — Idempotent restart**

같은 프로젝트에서:
```
# /hams:dashboard  (첫 호출)
# /hams:dashboard  (두 번째 호출)
```

기대:
- 두 번째 호출 시 첫 인스턴스의 PID kill → 새 PID + 새 포트
- 이전 URL 은 dead, 새 URL 만 살아있음
- `.hamstern/dashboard.pid` 가 새 PID 로 덮어쓰기

- [ ] **시나리오 4 — 멀티-프로젝트 공존**

두 다른 프로젝트 (예: hamstern-plugin + /tmp/test-empty) 에서 각각 호출:
- 각자 다른 동적 포트
- 두 브라우저 탭 동시 동작
- 한쪽 종료가 다른 쪽에 영향 없음

- [ ] **시나리오 5 — Publish 모드 회귀 (Sub-D 보존)**

```
# /hams:dashboard --publish    (hamstern-plugin 자체에서)
```

기대:
- `docs/data/` 번들 + (변경 있으면) commit + push
- https://edu-openskill.github.io/hamstern/ 가 갱신된 데이터로 응답

- [ ] **시나리오 6 — Path traversal 차단 (자동 + 수동 한 번)**

```
curl -I "http://localhost:<port>/data/../../etc/passwd"
```

기대: HTTP 404. (자동 테스트 e2e 케이스가 이미 검증.)

### Step 3: verification.md 작성

- [ ] **verification.md 신규 작성**

```markdown
# Sub-project E — Dashboard Per-Project Local Serve Verification

**Date:** 2026-05-23 (구현 완료일 기준 갱신)
**Plan:** `2026-05-23-sub-e-dashboard-local-plan.md`
**Spec:** `2026-05-23-sub-e-dashboard-local-design.md`

## 자동 테스트

| 테스트 | 케이스 수 | 결과 |
|---|---|---|
| `skills/dashboard/test_build.py` (Sub-D 회귀) | 6 | ✅ |
| `skills/dashboard/test_serve.py` (신규) | 9 | ✅ |
| `skills/audit-decisions/test_remove.py` (Sub-D 회귀) | 5 | ✅ |
| `skills/record/test_record_format.py` (Sub-C 회귀) | 10 | ✅ |
| **합계** | **30** | ✅ |

명령: `python3 -m pytest skills/ -v`.

## 수동 UAT

### 시나리오 1 — 빈 프로젝트 local 모드
- [ ] `.hamstern/dashboard-data/manifest.json` 생성됨 (decisions:false, sessions:[])
- [ ] 서버 background 기동, URL 출력
- [ ] 브라우저: "결정사항 없음 / 세션 없음 / 로그 없음"

### 시나리오 2 — 실데이터 프로젝트
- [ ] decisions/sessions/log 모두 렌더
- [ ] [×] 클릭 → 클립보드 정확한 remove 명령

### 시나리오 3 — Idempotent restart
- [ ] 두 번째 호출 시 첫 PID kill + 새 PID 기록
- [ ] 새 URL 만 살아있음

### 시나리오 4 — 멀티-프로젝트 공존
- [ ] 두 프로젝트가 서로 다른 포트로 동시 dashboard

### 시나리오 5 — Publish 모드 회귀
- [ ] `--publish` → gh-pages 흐름 정상 (Sub-D 보존)

### 시나리오 6 — Path traversal
- [x] e2e 테스트 통과
- [ ] 수동 curl 검증 (HTTP 404)

## 발견 사항 / Follow-up

(구현 중 발견한 이슈 기록 — 예: plugin 캐시 갱신 마찰, 좀비 PID 누적, …)

## Sub-F 후보

- 멀티-프로젝트 aggregator (한 URL 에서 N개 프로젝트 합쳐 보기)
- Slack/Discord broadcast (MCP)
- 자동 reload (데이터 변경 감지 → 브라우저 새로고침)
```

각 시나리오 박스를 실제 UAT 후 채움.

- [ ] **commit + 최종 push**

```
git add docs/plans/2026-05-23-sub-e-dashboard-local-verification.md
git commit -m "test(verify): Sub-E dashboard local serve verification log (Sub-E)"
git push origin main
```

---

## Self-Review (plan 작성자 본인 점검 — 실행 시 무시)

**Spec coverage:**
- ✅ 두 모드 (local 기본 / --publish): Task 9 의 SKILL.md
- ✅ `serve.py` ≤ 80 줄 stdlib: Task 2-7 의 단계별 구현
- ✅ `translate_path` + `/data/*` 분기: Task 2-4
- ✅ Path traversal 차단: Task 5
- ✅ 동적 포트 + 멀티-프로젝트 공존: Task 6 + UAT 시나리오 4
- ✅ Background server + PID 추적 + idempotent restart: Task 9 의 SKILL.md Step 1
- ✅ 9 pytest 케이스: Task 2-8
- ✅ build.py 변경 없음: 명시
- ✅ 정적 자산 변경 없음: 명시
- ✅ README + conventions 갱신: Task 10
- ✅ verification.md: Task 11
- ✅ plugin 캐시 갱신 마찰: Task 11 Step 1b
- ✅ `$CLAUDE_PLUGIN_ROOT` 미신뢰 + glob fallback: Task 1 + SKILL.md

**Placeholders:**
- 사용자 액션 placeholder (옵션 1/2/3) — 의도된 사용자 선택 영역. 명확.
- 시나리오 6 의 수동 curl 검증은 자동 테스트로 백업됨. OK.

**Type consistency:**
- `HamsHandler.plugin_dir` / `data_dir` — Task 2-7 일관
- `pick_port()` 모듈 레벨 함수 — Task 6 + 8 일관
- `_safe_join` classmethod — Task 5 정의, e2e 에서 자동 호출

**Risk:** plugin 캐시 갱신은 사용자 환경 의존 — UAT 진행 전 명시적으로 갱신 완료 필요. Task 11 Step 1b 가 이를 명시.
