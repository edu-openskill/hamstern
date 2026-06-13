#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_lecture.py — 강의 한 회차(슬라이드/시뮬레이터/대본)를 GitHub Pages 강의 사이트에 배치.

호출 예:
  python3 build_lecture.py --repo-dir <worktree> --plugin-root <plugin> \
      --id 1 --no "1강" --title "어텐션이란?" --slug attention \
      --summary "전학생 비유로 보는 self-attention" --section "1부 · 트랜스포머" \
      --slide /path/slide.html --sim /path/sim.html --script /path/script.md \
      --blog-title "AI 네이티브 엔지니어링" --tagline "비유로 익히는 ..." \
      --hero "AI 네이티브 엔지니어링" --year 2026

대본 암호화 시 환경변수 LEC_SCRIPT_PASSCODE 필요(빌더가 encrypt_script.mjs 로 위임).
"""
import argparse, json, os, re, shutil, subprocess, sys, html as _html

# ───────────────────────── 미니 마크다운 → HTML ─────────────────────────
def md_to_html(md: str) -> str:
    lines = md.replace('\r\n', '\n').split('\n')
    out, i, n = [], 0, len(lines)
    def inline(t):
        t = _html.escape(t, quote=False)
        t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
        t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
        t = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', t)
        t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
        return t
    while i < n:
        ln = lines[i]
        if not ln.strip():
            i += 1; continue
        if ln.startswith('```'):
            i += 1; buf = []
            while i < n and not lines[i].startswith('```'):
                buf.append(_html.escape(lines[i], quote=False)); i += 1
            i += 1
            out.append('<pre><code>' + '\n'.join(buf) + '</code></pre>'); continue
        m = re.match(r'(#{1,6})\s+(.*)', ln)
        if m:
            lv = len(m.group(1)); out.append(f'<h{lv}>{inline(m.group(2))}</h{lv}>'); i += 1; continue
        if re.match(r'\s*[-*+]\s+', ln):
            items = []
            while i < n and re.match(r'\s*[-*+]\s+', lines[i]):
                items.append('<li>' + inline(re.sub(r'\s*[-*+]\s+', '', lines[i], count=1)) + '</li>'); i += 1
            out.append('<ul>' + ''.join(items) + '</ul>'); continue
        if re.match(r'\s*\d+\.\s+', ln):
            items = []
            while i < n and re.match(r'\s*\d+\.\s+', lines[i]):
                items.append('<li>' + inline(re.sub(r'\s*\d+\.\s+', '', lines[i], count=1)) + '</li>'); i += 1
            out.append('<ol>' + ''.join(items) + '</ol>'); continue
        if ln.startswith('>'):
            buf = []
            while i < n and lines[i].startswith('>'):
                buf.append(inline(lines[i].lstrip('>').strip())); i += 1
            out.append('<blockquote>' + '<br/>'.join(buf) + '</blockquote>'); continue
        buf = []
        while i < n and lines[i].strip() and not re.match(r'(#{1,6}\s|```|\s*[-*+]\s|\s*\d+\.\s|>)', lines[i]):
            buf.append(inline(lines[i])); i += 1
        out.append('<p>' + '<br/>'.join(buf) + '</p>')
    return '\n'.join(out)

# ───────────────────────── 슬라이드/시뮬 back-bar 주입 ─────────────────────────
BAR_CSS_JS = """
<!-- ===== hams:lec nav bar (injected) ===== -->
<style id="lec-bar-style">
#lec-bar{position:fixed;left:12px;bottom:12px;z-index:2147483000;display:flex;gap:8px;
  font-family:-apple-system,"Segoe UI","Noto Sans KR",sans-serif}
#lec-bar a{background:rgba(15,20,28,.82);color:#e6edf3;border:1px solid rgba(255,255,255,.18);
  border-radius:999px;padding:8px 14px;font-size:13px;font-weight:700;text-decoration:none;backdrop-filter:blur(6px)}
#lec-bar a:hover{background:rgba(15,20,28,.95)}
#lec-bar.hide{display:none}
</style>
<div id="lec-bar"><a href="../../index.html">← 강의 목록</a><a href="#" id="lec-bar-x">숨기기</a></div>
<script>document.getElementById('lec-bar-x').addEventListener('click',function(e){e.preventDefault();document.getElementById('lec-bar').classList.add('hide');});</script>
<!-- ===== /hams:lec nav bar ===== -->
"""

def inject_bar(src_html: str) -> str:
    if 'lec-bar-style' in src_html:
        return src_html  # 이미 주입됨
    if '</body>' in src_html:
        return src_html.replace('</body>', BAR_CSS_JS + '\n</body>', 1)
    return src_html + BAR_CSS_JS

# ───────────────────────── 첫 배포: 템플릿 복사 ─────────────────────────
def ensure_site(repo_dir, plugin_root, vars_):
    idx = os.path.join(repo_dir, 'index.html')
    tpl = os.path.join(plugin_root, 'skills', 'lec', 'templates')
    if not os.path.exists(idx):
        shutil.copy(os.path.join(tpl, 'index.html'), idx)
        os.makedirs(os.path.join(repo_dir, 'assets'), exist_ok=True)
        for f in ('style.css', 'app.js'):
            shutil.copy(os.path.join(tpl, 'assets', f), os.path.join(repo_dir, 'assets', f))
        # substitute blog vars
        with open(idx, encoding='utf-8') as fh: s = fh.read()
        for k, v in vars_.items():
            s = s.replace('{{' + k + '}}', v)
        with open(idx, 'w', encoding='utf-8') as fh: fh.write(s)
        open(os.path.join(repo_dir, '.nojekyll'), 'w').close()
        with open(os.path.join(repo_dir, 'robots.txt'), 'w', encoding='utf-8') as fh:
            fh.write("User-agent: *\nDisallow: /lectures/*/script.html\n")
        print('  [site] 템플릿 초기화 완료')

# ───────────────────────── 대본 암호화 → gate.html ─────────────────────────
def build_script(repo_dir, plugin_root, lec_id, no, title, blog_title, script_src):
    ext = os.path.splitext(script_src)[1].lower()
    raw = open(script_src, encoding='utf-8').read()
    body = raw if ext in ('.html', '.htm') else md_to_html(raw)
    passcode = os.environ.get('LEC_SCRIPT_PASSCODE')
    if not passcode:
        print('  [error] 대본 암호화에 LEC_SCRIPT_PASSCODE 환경변수가 필요합니다.', file=sys.stderr)
        sys.exit(3)
    enc = subprocess.run(
        ['node', os.path.join(plugin_root, 'skills', 'lec', 'encrypt_script.mjs')],
        input=body, capture_output=True, text=True)
    if enc.returncode != 0:
        print('  [error] 암호화 실패:', enc.stderr.strip(), file=sys.stderr); sys.exit(3)
    payload = json.loads(enc.stdout)
    gate = open(os.path.join(plugin_root, 'skills', 'lec', 'templates', 'script_gate.html'), encoding='utf-8').read()
    repl = {'LEC_TITLE': title, 'LEC_NO': no, 'BLOG_TITLE': blog_title,
            'CIPHER': payload['cipher'], 'SALT': payload['salt'],
            'IV': payload['iv'], 'ITERS': str(payload['iters'])}
    for k, v in repl.items():
        gate = gate.replace('{{' + k + '}}', v)
    dst = os.path.join(repo_dir, 'lectures', str(lec_id), 'script.html')
    with open(dst, 'w', encoding='utf-8') as fh: fh.write(gate)
    return f'lectures/{lec_id}/script.html'

# ───────────────────────── 슬라이드/시뮬 배치 ─────────────────────────
def place_asset(repo_dir, lec_id, src, name, no_bar):
    s = open(src, encoding='utf-8').read()
    if not no_bar:
        s = inject_bar(s)
    dst = os.path.join(repo_dir, 'lectures', str(lec_id), name)
    with open(dst, 'w', encoding='utf-8') as fh: fh.write(s)
    return f'lectures/{lec_id}/{name}'

# ───────────────────────── lectures.json upsert ─────────────────────────
def upsert(repo_dir, entry, section):
    p = os.path.join(repo_dir, 'lectures.json')
    data = {'blogTitle': '', 'sections': [], 'lectures': []}
    if os.path.exists(p):
        data = json.load(open(p, encoding='utf-8'))
    data.setdefault('sections', []); data.setdefault('lectures', [])
    if section and section not in data['sections']:
        data['sections'].append(section)
    found = False
    for i, l in enumerate(data['lectures']):
        if l.get('lecId') == entry['lecId']:
            data['lectures'][i] = {**l, **{k: v for k, v in entry.items() if v is not None}}
            found = True; break
    if not found:
        data['lectures'].append({k: v for k, v in entry.items() if v is not None})
    data['lectures'].sort(key=lambda x: x.get('lecId', 0))
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-dir', required=True)
    ap.add_argument('--plugin-root', required=True)
    ap.add_argument('--id', type=int, required=True)
    ap.add_argument('--no', required=True)
    ap.add_argument('--title', required=True)
    ap.add_argument('--slug', required=True)
    ap.add_argument('--summary', default='')
    ap.add_argument('--section', default='')
    ap.add_argument('--slide'); ap.add_argument('--sim'); ap.add_argument('--script')
    ap.add_argument('--date', default='')
    ap.add_argument('--no-bar', action='store_true')
    ap.add_argument('--blog-title', default='강의 노트')
    ap.add_argument('--tagline', default='')
    ap.add_argument('--hero', default='')
    ap.add_argument('--year', default='')
    a = ap.parse_args()

    ensure_site(a.repo_dir, a.plugin_root, {
        'BLOG_TITLE': a.blog_title, 'BLOG_TAGLINE': a.tagline,
        'BLOG_HERO_TITLE': a.hero or a.blog_title, 'BLOG_YEAR': a.year or '2026'})

    os.makedirs(os.path.join(a.repo_dir, 'lectures', str(a.id)), exist_ok=True)
    entry = {'lecId': a.id, 'no': a.no, 'title': a.title, 'slug': a.slug,
             'summary': a.summary, 'section': a.section, 'date': a.date,
             'slide': None, 'sim': None, 'script': None}
    if a.slide:  entry['slide']  = place_asset(a.repo_dir, a.id, a.slide, 'slide.html', a.no_bar); print('  [slide]', entry['slide'])
    if a.sim:    entry['sim']    = place_asset(a.repo_dir, a.id, a.sim, 'sim.html', a.no_bar);   print('  [sim]  ', entry['sim'])
    if a.script: entry['script'] = build_script(a.repo_dir, a.plugin_root, a.id, a.no, a.title, a.blog_title, a.script); print('  [script]', entry['script'], '(암호화됨)')

    upsert(a.repo_dir, entry, a.section)
    print(f'  [ok] #{a.id} {a.no} {a.title} → lectures.json 갱신')

if __name__ == '__main__':
    main()
