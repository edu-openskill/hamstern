# diary-core 렌더링 단계 (공유)

> diary-server·diary-local 공용. 호출 측이 `$BLOG_DIR`(서버=git 워크트리, 로컬=프로파일의 `dir`)와
> `$TEMPLATE`, `$BLOG_TITLE`, `$FEATURES_SEARCH`, `$PREVIEW_PORT` 변수를 세팅한 뒤 이 단계들을 실행한다.
> git(clone/worktree/commit/push)·serve·승인 게이트는 각 SKILL.md 소관이며 여기 없다.
> 스크립트 경로: `${PLUGIN_ROOT}/skills/diary-core/{inject_html_adapter,extract_original_html,watch_and_rebuild}.py`,
> 템플릿: `${PLUGIN_ROOT}/skills/diary-core/templates/{minimal|tech|lecture|notebook|magazine}/`

## 1️⃣ 입력 분류 & Job 목록 생성

입력 인자를 분석해 **JOBS** 배열을 만든다. 각 job:

```python
{
  "src": "/abs/path/to/file.md",   # 원본 절대경로
  "engine": "md" | "html",          # 처리 엔진
  "slug": "kebab-case-id",
  "title": "추출된 제목",
  "categories": ["msa", "kafka"],  # 항상 배열 (1개여도 ["msa"])
  "tags": [...],
  "summary": "..."
}
```

> **`categories` 입력 규칙**
> - CLI: `/hams:diary publish ./post.md "msa,kafka"` — 쉼표 구분, 공백 trim, 빈 항목 제거.
> - AskUserQuestion: 비어있으면 기존 글로벌 카테고리 목록 + "신규 입력" 으로 `multiSelect: true`. 글로벌이 비면 텍스트 1개 입력.
> - 옛 단일 string `category` 인자도 호환 — 내부적으로 `[category]` 로 변환.

### 모드별 처리

- **`{file.md}`** → 1 job (engine=md)
- **`{file.html}`** → 1 job (engine=html)
- **`{dir/}`** → 디렉토리 안 모든 `.md` + `.html` (재귀 X). 비-ASCII 파일명 처리(아래) 거쳐 N jobs.
- **`"{glob}"`** → glob 매칭한 파일들

### 비-ASCII (한글) 파일명 처리

Windows + Python 조합에서 한글 파일명이 `os.listdir()` 으로 보이지 않는 케이스가 있다. PowerShell 로 우회:

```powershell
Get-ChildItem -LiteralPath $src -Filter *.html | ForEach-Object {
  # ASCII slug 로 임시 디렉토리에 복사
  $slug = ...  # title/길이/순번 기반
  Copy-Item -LiteralPath $_.FullName -Destination "$tmp/$slug.html" -Force
}
```

이후 Python 빌더는 ASCII 임시 디렉토리에서 파일을 읽는다.

### 메타데이터 추출

- **MD**: frontmatter(`---` 사이) 우선, 없으면 첫 H1 → title, 첫 문단 → summary, 헤딩들 → tags
- **HTML**: `<title>` 태그 → title, `<meta name="description">` → summary, 첫 H1 → fallback title, body 안 헤딩들 → tags
- **slug**: 파일명 → kebab-case (한글은 PowerShell 단계에서 ASCII slug 로 변환됨)
- **categories**: CLI 인자 우선 (쉼표 구분 — 위 규칙 참조), 없으면 AskUserQuestion `multiSelect: true` 로 (기존 글로벌 + "신규 입력")

---

## 3️⃣ 첫 배포면 템플릿 복사

워크트리에 `index.html` 이 없거나 `.diary-meta.json` 의 template 이 다르면:

```bash
TEMPLATE_DIR="${PLUGIN_ROOT}/skills/diary-core/templates/${TEMPLATE}"
cp -R "$TEMPLATE_DIR"/* .
# {{BLOG_TITLE}}, {{BLOG_TAGLINE}}, {{BLOG_HERO_TITLE}}, {{BLOG_ABOUT}}, {{BLOG_YEAR}} 치환
sed -i "s/{{BLOG_TITLE}}/${BLOG_TITLE}/g" index.html
# ... (모든 템플릿 변수 치환)
echo "{\"template\":\"${TEMPLATE}\"}" > .diary-meta.json
touch .nojekyll  # GitHub Pages 가 _underscore 폴더를 무시하지 않도록
```

`{{BLOG_TITLE}}`, `{{BLOG_TAGLINE}}`, `{{BLOG_HERO_TITLE}}`, `{{BLOG_ABOUT}}`, `{{BLOG_YEAR}}` 가 비어있으면 AskUserQuestion 으로 사용자에게 입력받음.

---

## 4️⃣ posts.json 갱신 (메모리상) — 안전한 매칭

```bash
# 기존 posts.json 로드 (없으면 빈 구조)
[ -f posts.json ] && cat posts.json || echo '{"categories":[],"posts":[]}'
```

각 job 에 대해 **3단계 매칭 우선순위** 로 기존 항목을 찾는다 (한글 파일명 → ASCII slug 변환 시 drift 가 있어도 같은 글로 식별 가능하게):

1. **`originalFilename` 일치** (1순위) — `os.path.basename(SRC)` 와 `posts[].originalFilename` 직접 비교. 한글 원본 파일명 그대로 비교하므로 slug 알고리즘이 바뀌어도 면역.
2. **`id == job.slug` 일치** (2순위) — 기존 동작. originalFilename 이 빈 옛 항목 (마이그레이션 전) 호환용.
3. **제목 유사도 ≥ 0.85 + 같은 `engine`** (3순위) — `difflib.SequenceMatcher` 로 비교. 후보가 정확히 1건이면 AskUserQuestion 으로 사용자 확인 ("기존 글 'X' 와 같은 글입니까? 덮어쓸까요 / 신규 추가할까요"). 후보가 2건 이상이면 AskUserQuestion 으로 선택 또는 신규 추가.

매칭 결과 처리:

- **매칭 발견 + `--overwrite` 미설정**: `[skip] {filename} → already exists as id=${existing_slug}` 출력, 이 job 제외
- **매칭 발견 + `--overwrite` 설정**: **기존 slug 재사용** (URL 보존). `posts/{existing_slug}.html` 덮어쓰기, `_src/{existing_slug}.{ext}` 갱신, posts.json 항목 in-place 업데이트. 새 slug 절대 생성 안 함.
- **매칭 없음**: 새 slug 로 신규 삽입.

스키마 (기존 호환 + 신규 필드):
```json
{
  "postId": 1,
  "id": "kebab-slug",
  "title": "...",
  "date": "YYYY-MM-DD",
  "categories": ["msa", "kafka"],
  "summary": "...",
  "filename": "posts/1/kebab-slug.html",
  "tags": ["..."],
  "engine": "md" | "html",
  "themeInjected": true | false,
  "sourcePath": "_src/kebab-slug.{ext}",
  "originalFilename": "원본_파일명.html"
}
```

**`categories` 호환성 규칙**
- 새 entry 는 항상 `categories: [...]` 배열로 저장. 단일이어도 `["msa"]`.
- 옛 entry 가 `category: "msa"` 만 가지고 있으면 다음 publish/edit/--rebuild 시 자동 마이그레이션:
  `entry['categories'] = [entry.pop('category')]`. 정규화 후 글로벌 `categories[]` 도 갱신.
- 사이트 JS (template 의 `script.js`) 는 항상 `entry.categories ?? (entry.category ? [entry.category] : [])` 로 정규화해서 읽음. 첫 카테고리가 라벨/아이콘의 기본값.

**`postId` 부여 규칙**
- 신규 글의 `postId` = `max(p['postId'] for p in posts) + 1` (없으면 1). **재사용 금지** — 삭제된 ID 도 다시 쓰지 않는다 (URL 안정성).
- `filename` 은 항상 `posts/{postId}/{id}.html` 로 통일.
- 옛 스키마 (postId 없음) 항목은 publish/edit/--rebuild 첫 호출 시 자동 마이그레이션 — 현재 배열 순서대로 1, 2, 3 부여 + 파일 이동.

> **`originalFilename` 마이그레이션** — 기존 항목에 이 필드가 없는 경우, 다음 배포·재빌드 시 자동으로 채워진다. 1순위 매칭은 그냥 건너뛰고 2순위(slug)로 폴백되므로 옛 데이터 손상 없음.

**글로벌 `categories[]` 관리** — entry 의 `categories` 의 모든 항목을 글로벌 `categories[]` 에 union (첫 등장 순서 유지). 삭제 시 다른 글에서 더 이상 사용 안 하는 카테고리만 글로벌 배열에서 제거.

---

## 5️⃣ 포스트 HTML 생성 (워크트리에 기록)

### MD 엔진

```bash
# 출력 경로는 항상 posts/{postId}/{slug}.html
mkdir -p "posts/${postId}"

# 마크다운 → HTML 변환 (기존 변환 규칙 그대로, 인라인 Python markdown 또는 정규식)
# 변환된 HTML 을 _post-frame.html 의 {{POST_HTML}} 자리에 치환.
# {{POST_CATEGORY}} 는 categories 의 첫 번째 항목만 표시 (글 본문 헤더는 간결하게).
PRIMARY_CAT="${CATEGORIES[0]:-}"
sed -e "s|{{POST_TITLE}}|${TITLE}|g" \
    -e "s|{{POST_CATEGORY}}|${PRIMARY_CAT}|g" \
    -e "s|{{POST_DATE}}|${DATE}|g" \
    -e "s|{{POST_HTML}}|${BODY_HTML}|g" \
    -e "s|{{BLOG_TITLE}}|${BLOG_TITLE}|g" \
    _post-frame.html > "posts/${postId}/${slug}.html"
```

`_post-frame.html` 자체에는 `../../assets/style.css` 와 `../../index.html` 링크가 들어 있으므로 글이 깊이 2 디렉토리 안에서도 정상 동작.

(실제로는 sed 보다 Python 한 줄로 read+replace+write 하는 게 안전함, 본문에 특수문자 있을 수 있어서)

### HTML 엔진

```bash
# 출력 경로는 항상 posts/{postId}/{slug}.html
mkdir -p "posts/${postId}"

# 폭 모드 — CLI 플래그 또는 (--rebuild 시) posts.json[].fit 에서 결정
#   publish 시: --fit-viewport / --scale-up 인자에서 추출
#   rebuild 시: 기존 entry 의 fit 필드 (없으면 native)
FIT_ARG=""
case "$FIT_MODE" in
  viewport) FIT_ARG="--fit-viewport" ;;
  scale)    FIT_ARG="--scale-up" ;;
  *)        FIT_ARG="" ;;
esac

python3 "${PLUGIN_ROOT}/skills/diary-core/inject_html_adapter.py" \
  --src "${SRC}" --dst "posts/${postId}/${slug}.html" --title "${TITLE}" \
  ${NO_THEME:+--no-theme} $FIT_ARG

# 결과 fit_mode 를 posts.json 의 해당 entry 에 저장 (재빌드 시 그대로 재현)
#   {"postId":..., "id":..., "fit":"native|viewport|scale", ...}
```

어댑터의 floating bar 안 back-link 는 `../../index.html` 로 emit 된다 (글이 2단 깊이에 있으므로). 배치 모드는 `--map` JSON 으로 한 번에 호출 가능.

> 어댑터는 원본 HTML 의 dominant background 를 자동 감지해 `data-osd-source-theme="light|dark"` 로 표시한다. 사용자가 선택한 블로그 테마와 톤이 다를 때만 invert 필터를 걸어 자동 변환하므로, 라이트 톤 원본(예: 베이지) 도 다크 블로그에서 자연스럽게 보인다. (감지 실패 시 기존 동작인 `dark` 가정.)

### 원본 소스 보존 (`_src/`) + originalFilename 기록

배포 시 원본 파일을 워크트리의 `_src/{slug}.{ext}` 로도 복사한다. 나중에 `edit {slug}` 또는 `publish --rebuild` 시 이 원본을 사용한다.

```bash
mkdir -p _src
cp "${SRC}" "_src/${slug}.${EXT}"   # ext = md or html (변환 전 파일)
```

posts.json 의 두 필드에 기록:
- `sourcePath`: `"_src/{slug}.{ext}"` — 백업 파일 위치
- `originalFilename`: `os.path.basename(SRC)` — **매칭 1순위 키**. 한글 파일명 그대로 (`"Saga 오케스트레이션 _kafka.html"` 같은 형태) 저장. 다음 `--overwrite` 때 slug 가 다르게 나와도 이 필드로 같은 글이라고 식별.

`_src/` 는 GitHub Pages 가 무시하지 않도록 `.nojekyll` 만 있으면 그대로 서빙되지만, 보통 사이트에는 노출되지 않게 `index.html` 의 라우팅 대상 외다 — 그냥 레포에만 보관되는 원본 백업이다.

---

## 5️⃣.5 기능 토글 적용 (검색)

`features` 가 활성화되어 있으면 변수 치환 시 다음 자리표시자도 함께 채운다.

### `{{SEARCH_BLOCK}}` (index.html 안)

`features.search === true`:
```html
<div id="osd-search" class="osd-search"></div>
<link rel="stylesheet" href="pagefind/pagefind-ui.css" />
<script src="pagefind/pagefind-ui.js"></script>
<script>
  window.addEventListener('DOMContentLoaded', function () {
    new PagefindUI({
      element: '#osd-search',
      showSubResults: true,
      translations: { placeholder: '본문 검색…', clear_search: '지우기', no_results: '결과 없음' }
    });
  });
</script>
```

`features.search === false`:
```html
<!-- search disabled -->
```

> 댓글 기능은 지원하지 않는다. 옛 버전의 `{{COMMENTS_BLOCK}}` 자리표시자나 `--comments-*` 어댑터 인자는 모두 폐기됐다.

---

## 8️⃣.5 Pagefind 인덱스 생성 (검색 활성 시)

`features.search === true` 인 경우, push 직전에 인덱스를 빌드해 같은 commit 에 포함시킨다.

```bash
if [ "$FEATURES_SEARCH" = "true" ]; then
  cd "$BLOG_DIR"
  npx -y pagefind --site . --output-path pagefind 2>&1 | tail -5
  # 결과: ./pagefind/ 디렉토리 (UI css/js + 인덱스 조각들)
fi
```

빌드 실패 시 ("Node.js 없음" 등) 사용자에게 안내하고 검색 없이 진행.

---

## 5가지 템플릿 한눈에

| name | 톤 | 적합한 콘텐츠 |
|------|-----|------|
| `minimal` | 흰 배경 · 세리프 본문 · 단일 컬럼 | 텍스트 중심 노트, 에세이 |
| `tech` (default) | 다크 히어로 · 그라데이션 카드 · 카테고리 필터 | 시뮬레이터 · 도식 · 도구 |
| `lecture` | 주차/회차 번호 · 사이드 목차 | 정규 강의 시리즈 |
| `notebook` | Jupyter풍 좌측 TOC · monospace 헤딩 | 튜토리얼 · 실습 |
| `magazine` | 큰 히어로 · 에디토리얼 그리드 · 세리프 | 포트폴리오 · 쇼케이스 |

각 템플릿은 `templates/{name}/` 안 4개 파일:
- `index.html` — 홈
- `assets/style.css`
- `assets/script.js`
- `_post-frame.html` — 마크다운 포스트 셸 (HTML 시뮬레이터는 이 셸을 사용하지 않고 어댑터만 주입)
