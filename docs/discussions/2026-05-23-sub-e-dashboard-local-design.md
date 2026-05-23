# Dashboard — Per-Project Local Serve Mode (Sub-project E)

**Date:** 2026-05-23
**Status:** Approved design, ready for plan
**Sub-project:** E (of A+B+C+D+E+...). A·B·C·D 완료. Sub-D 가 단일 repo 의 정적 gh-pages dashboard 흐름을 demo·dogfood 로 ship. Sub-E 가 매 프로젝트에서 즉시 동작하는 로컬 serve 모드를 추가한다.
**Repo:** `edu-openskill/hamstern`

## 배경

Sub-D 의 UAT 막바지에 사용자가 짚은 설계 빈틈: dashboard 가 단일 repo 의 정적 사이트로만 동작하면 매 프로젝트가 자기 `docs/` + GitHub Pages 활성화를 가져야 한다. 이는 무거운 진입 마찰이고 다음 케이스를 막는다:

- private repo (Pages 가 유료 plan 필요)
- GitHub remote 가 없는 로컬-only 프로젝트
- `docs/` 폴더를 갖는 게 부자연스러운 프로젝트 (CLI 도구, 라이브러리, 노트 저장소 등)
- 새 프로젝트마다 GitHub Settings 5번 클릭

해법: **`/hams:dashboard` 의 기본 동작을 로컬 serve 로 전환**한다. plugin install 경로의 정적 자산 (Sub-D 산출물) + 프로젝트 로컬 데이터를 작은 커스텀 Python 핸들러가 동시 serve. gh-pages publish 흐름은 `--publish` 플래그로 보존.

## 목표

`/hams:dashboard` 가 **모든 프로젝트에서 외부 의존 0 으로 즉시 동작**한다 — git remote 없어도, Pages 미활성이어도, 인증 없이도. Sub-D 의 build.py 와 정적 자산 (`docs/{index,app,style}`) 은 100% 재사용. 새로운 코드는 `skills/dashboard/serve.py` 하나 (≤ 80 줄 stdlib).

## 원칙

- **두 모드, 단일 명령** — `/hams:dashboard` (local 기본) / `/hams:dashboard --publish` (Sub-D 흐름).
- **자산 출처는 plugin install** — `docs/{index,app,style}` 는 plugin 경로에서 serve. 사용자 프로젝트에 정적 자산 복사 안 함.
- **데이터 출처는 프로젝트 로컬** — `{project}/.hamstern/dashboard-data/`. `.hamstern/` 이 이미 hamstern 소유 영역이라 의미 명확.
- **Stdlib only** — FastAPI/Flask 등 외부 의존 0. hamstern 의 일관 원칙.
- **Background + 동적 포트** — Claude 세션 안 막힘. 매 호출 OS 가 자유 포트 할당 → 포트 충돌 0, 멀티-프로젝트 동시 dashboard 가능.
- **Idempotent restart** — 같은 프로젝트에서 두 번째 호출 시 이전 PID kill 후 새 인스턴스 시작.
- **Read 와 write 분리 유지** — Sub-D 와 동일. dashboard 는 read-only 뷰어, 편집은 `/hams:audit-decisions remove "<text>"` 클립보드 흐름.

## 비범위 (Out of scope)

- **`/hams:dashboard-stop` 명령** — YAGNI. 좀비 서버 누적 시 추가 검토.
- **멀티-프로젝트 aggregator** — Sub-F 후보. 한 URL 에서 N개 프로젝트 합쳐 보기.
- **Slack/Discord broadcast** — 별도 후속 sub-project.
- **인증·다중 사용자** — 단일 사용자 도구 가정 유지.
- **양방향 실시간 sync** — 정적 viewer + 클립보드 흐름 유지.
- **자동 브라우저 자동 reload** — 데이터 변경 시 브라우저 자동 갱신. v2 이후 검토. v1 은 사용자가 `/hams:dashboard` 재호출.

## 아키텍처

### 두 모드 비교

| 모드 | 명령 | 데이터 출력 | 자산 출처 | 외부 의존 |
|---|---|---|---|---|
| **local** (기본) | `/hams:dashboard` | `{project}/.hamstern/dashboard-data/` | `$CLAUDE_PLUGIN_ROOT/docs/` | 0 |
| **publish** | `/hams:dashboard --publish` | `{project}/docs/data/` | 같음 (commit 됨) | git remote + Pages |

publish 모드는 Sub-D 명세 그대로 — 본 spec 은 추가 변경 없음.

### Local 모드 디렉터리

```
플러그인 설치 (사용자 머신, 모든 프로젝트가 공유)
$CLAUDE_PLUGIN_ROOT/
├── skills/dashboard/
│   ├── build.py            # Sub-D 그대로 (--out 인자로 출력 경로 가변)
│   ├── serve.py            # 신규 (본 spec)
│   ├── test_build.py       # Sub-D 6 케이스
│   ├── test_serve.py       # 신규 9 케이스
│   └── SKILL.md            # 재작성 (두 모드 분기)
└── docs/                   # 정적 자산 (Sub-D 결과)
    ├── index.html
    ├── app.js
    ├── style.css
    └── data/               # plugin 자체 demo bundle. Sub-E 의 local 모드는 사용 안 함.
        └── manifest.json

사용자 프로젝트 (예: ~/myproject)
~/myproject/
└── .hamstern/
    ├── decisions.md         # /hams:record 가 씀 (소스)
    ├── decisions-log.md
    ├── sessions/*.md
    ├── dashboard-data/      # Sub-E 의 local 모드 출력 — build.py 가 매 호출 시 갱신
    │   ├── decisions.md     # source 의 사본
    │   ├── decisions-log.md
    │   ├── sessions/*.md
    │   └── manifest.json
    ├── dashboard.pid        # background serve.py PID
    └── dashboard.url        # 첫 줄에 http://localhost:<port>/
```

### 호출 흐름 (local 기본 모드)

SKILL.md 가 Claude 에게 지시:

1. **plugin 경로 확인** — `$CLAUDE_PLUGIN_ROOT` 검증. 미정 시 안내 + exit.
2. **이전 인스턴스 정리** — `.hamstern/dashboard.pid` 가 있으면 그 PID `kill -0` → 살아있으면 kill. 파일 제거.
3. **데이터 번들** — `python3 $CLAUDE_PLUGIN_ROOT/skills/dashboard/build.py --project . --out .hamstern/dashboard-data`. 실패 시 exit, 서버 기동 스킵.
4. **서버 background 기동** — `python3 $CLAUDE_PLUGIN_ROOT/skills/dashboard/serve.py --plugin-dir $CLAUDE_PLUGIN_ROOT/docs --data-dir .hamstern/dashboard-data > .hamstern/dashboard.url 2>&1 &` ; PID 를 `.hamstern/dashboard.pid` 에 기록.
5. **URL 대기** — 최대 5초간 `.hamstern/dashboard.url` 의 첫 줄 폴링. 비어있으면 timeout 보고.
6. **브라우저 오픈** — 플랫폼별 `start` / `open` / `xdg-open`. 명령 부재 시 URL 만 콘솔에 표시.
7. **사용자에게 보고** — `dashboard live at http://localhost:<port>/ (pid=<pid>)`.

### `serve.py` 명세

stdlib only (`http.server`, `socket`, `argparse`, `pathlib`).

```python
class HamsHandler(SimpleHTTPRequestHandler):
    plugin_dir: Path = None     # 클래스 속성으로 주입
    data_dir: Path = None

    def translate_path(self, path):
        # 쿼리·앵커 제거
        path = path.split('?', 1)[0].split('#', 1)[0]
        # 경로 정규화 (selen-style)
        if path.startswith('/data/'):
            rel = path[len('/data/'):]
            resolved = (self.data_dir / rel).resolve()
            if self.data_dir.resolve() not in (resolved, *resolved.parents):
                return str(self.data_dir / '__forbidden__')   # → 404
            return str(resolved)
        if path in ('/', ''):
            path = '/index.html'
        rel = path.lstrip('/')
        resolved = (self.plugin_dir / rel).resolve()
        if self.plugin_dir.resolve() not in (resolved, *resolved.parents):
            return str(self.plugin_dir / '__forbidden__')   # → 404
        return str(resolved)

    def log_message(self, fmt, *args):
        pass  # 콘솔 silent

def pick_port():
    """OS 가 할당한 자유 포트."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def main():
    # argparse: --plugin-dir, --data-dir, --port (default 0)
    # port 0 면 pick_port()
    # 첫 줄에 URL 출력 후 serve_forever()
    ...
```

### 보안

- Path traversal 차단 — `translate_path` 가 resolved 경로의 부모 chain 에 plugin_dir 또는 data_dir 가 포함되는지 검증. 아니면 존재하지 않는 sentinel path 반환 → SimpleHTTPRequestHandler 가 404.
- 127.0.0.1 만 bind — 외부 네트워크 노출 안 함.
- 인증 없음 — 동일 머신의 다른 사용자는 dashboard 접근 가능. v1 위협모델은 단일 사용자 머신 가정.

## UI 명세

Sub-D 와 동일 — 자산 그대로. 변경 없음.

브라우저는 `/data/manifest.json` 을 fetch 하는데, 본 spec 의 핸들러가 그것을 `{project}/.hamstern/dashboard-data/manifest.json` 으로 매핑. Sub-D 의 app.js 는 `DATA_PATH = 'data'` 상수를 쓰니 변경 불필요.

## 사용자 프로젝트의 `.gitignore`

SKILL.md 가 안내 (강제 안 함):
```
.hamstern/dashboard-data/
.hamstern/dashboard.pid
.hamstern/dashboard.url
```

publish 모드 안 쓰면 dashboard-data 는 commit 할 이유 없음. publish 모드 쓰면 그쪽은 `docs/data/` 로 별도 저장이라 충돌 없음.

## 에러 처리

| 시나리오 | 동작 |
|---|---|
| `$CLAUDE_PLUGIN_ROOT` 미정 | stderr 안내 + exit 1. SKILL.md Step 1 에서 검증. |
| `build.py` 실패 | stderr + exit 1, 서버 기동 스킵 |
| 동적 포트 할당 실패 | `serve.py` 가 stderr + exit 1. `.hamstern/dashboard.url` 비어있음을 SKILL.md 가 감지. |
| 서버 stdout 5초 내 URL 미출력 | timeout, `dashboard.url` 내용 stderr 로 보고 |
| 이전 PID 가 죽은 프로세스 | `kill -0` fail → silently rm pid 파일 후 진행 |
| 브라우저 명령 부재 | URL 콘솔 표시 + "수동으로 여세요" 안내 |
| Path traversal 시도 | translate_path 가 sentinel path 반환 → 404 |
| 동일 프로젝트 두 dashboard 인스턴스 | 이전 PID kill 로 자동 단일화 |
| `--publish` 모드에서 git remote 없음 / Pages 미활성 | Sub-D 의 흐름 그대로 — git 명령 자체가 stderr |

## 테스트

### 단위 (pytest)

`skills/dashboard/test_serve.py`:

1. `translate_path('/')` → `plugin_dir/index.html`
2. `translate_path('/app.js')` → `plugin_dir/app.js`
3. `translate_path('/style.css')` → `plugin_dir/style.css`
4. `translate_path('/data/manifest.json')` → `data_dir/manifest.json`
5. `translate_path('/data/sessions/foo.md')` → `data_dir/sessions/foo.md`
6. Path traversal `/data/../../../etc/passwd` → 차단 (sentinel path)
7. Path traversal `/../../etc/passwd` → 차단
8. `pick_port()` 두 번 → 둘 다 유효 포트 (1024+, 정수)
9. End-to-end — 실제 HTTPServer 띄워서 `urllib.request.urlopen` 으로 `/`, `/app.js`, `/data/manifest.json` HTTP 200 + 컨텐츠 검증

build.py 의 6 케이스는 변경 없음 (Sub-D 결과 그대로 유지).

### 매뉴얼 UAT (verification.md, plan 마지막 task)

- 빈 프로젝트 (`.hamstern/` 없음) 에서 `/hams:dashboard` → "데이터 미생성" fallback 정상
- 실데이터 프로젝트 → decisions/sessions/log 렌더
- 같은 프로젝트에서 두 번 연속 호출 → 이전 서버 kill, 새 포트, 새 URL
- 두 다른 프로젝트에서 각각 호출 → 각자 다른 포트로 동시 동작
- `--publish` → Sub-D 흐름 그대로 (gh-pages refresh + edu-openskill.github.io 갱신)
- Path traversal 수동 시도 (`curl http://localhost:PORT/../../etc/passwd`) → 404

## 변경 영향 매트릭스

| 항목 | 변경 |
|---|---|
| `skills/dashboard/serve.py` | **신규** |
| `skills/dashboard/test_serve.py` | **신규** (9 케이스) |
| `skills/dashboard/SKILL.md` | **재작성** (두 모드) |
| `skills/dashboard/build.py` | 변경 없음 |
| `skills/dashboard/test_build.py` | 변경 없음 |
| `docs/*` | 변경 없음 (Sub-D 자산 그대로) |
| `docs/data/manifest.json` (plugin 자체) | 변경 없음 (Sub-D demo bundle 유지) |
| `README.md` | dashboard 섹션 갱신 + Sub-E changelog 추가 |
| `docs/conventions.md` | dashboard 항목 "두 모드" 표기 |
| `.gitignore` (plugin 자체) | 변경 없음 (`.hamstern/` 가 plugin 에 없음) |
| `.claude-plugin/marketplace.json` | 변경 없음 |

## 마이그레이션

Sub-D 사용자 (= 본 개발자 1명) 의 영향:
- `/hams:dashboard` 의 기본 동작이 **gh-pages publish** 에서 **로컬 serve** 로 변경
- 기존 publish 흐름은 `--publish` 로 호출하면 동일 동작
- `edu-openskill/hamstern` 의 이미 publish 된 demo 사이트는 그대로 유지 — 다음 `--publish` 호출 시 갱신

## 1회성 운영 작업

없음. local 모드는 외부 설정 0. publish 모드는 Sub-D 의 Pages 활성화가 이미 완료됨.

## 검증 체크리스트 (Definition of Done)

- [ ] `skills/dashboard/serve.py` 작성됨 (≤ 80 줄, stdlib only)
- [ ] `skills/dashboard/test_serve.py` 9 케이스 그린
- [ ] `skills/dashboard/SKILL.md` 두 모드 명세로 재작성
- [ ] local 모드: 빈 프로젝트에서 동작 + 실데이터 프로젝트에서 동작 (수동)
- [ ] local 모드: 두 번 호출 시 idempotent restart 동작 (수동)
- [ ] local 모드: 두 프로젝트 동시 dashboard 동작 (수동)
- [ ] publish 모드: Sub-D 흐름 회귀 — `--publish` 호출이 gh-pages 갱신 (수동)
- [ ] Path traversal 차단 (자동 테스트)
- [ ] README + conventions 갱신
- [ ] verification.md 작성

## 다음 단계

Sub-F (가칭) 후보:
- 멀티-프로젝트 aggregator (한 dashboard 에서 N개 프로젝트 합쳐 보기)
- Slack/Discord broadcast (MCP 연동)
- 자동 reload (데이터 변경 감지 → 브라우저 reload)
- private project 의 publish (인증 토큰 기반)

Sub-E 의 plan 은 본 spec 을 입력으로 `writing-plans` skill 이 작성.
