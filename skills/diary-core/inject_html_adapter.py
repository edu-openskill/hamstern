#!/usr/bin/env python3
"""
inject_html_adapter.py — Open Skill Diary HTML simulator adapter

Reads an arbitrary HTML file (typically a dark-themed simulator) and writes
a transformed copy that:
  - Preserves the simulator's own max-width / centering — adapter does NOT
    override layout widths. If the simulator has .container { max-width: ...;
    margin: 0 auto } it remains centered; if not, it stays full-width.
  - Wraps body content in #osd-content-wrapper so a CSS filter can produce a
    light-mode variant on demand without touching simulator-internal styles
  - Injects a floating navigation bar (back to blog + theme toggle) that
    sits above the inverted region (z-index: 2147483647)
  - Persists theme via localStorage('blog-theme'), shared with the host blog

Output paths are posts/{id}/{slug}.html, so the floating bar back-links go
two levels up (../../index.html).

Usage:
    python inject_html_adapter.py --src <input.html> --dst <output.html> --title "..."
    python inject_html_adapter.py --src-dir <dir> --dst-dir <posts/> [--map JSON]
    python inject_html_adapter.py --src <in.html> --dst <out.html> --title "..." --no-theme

When --no-theme is set, only the floating bar (with body padding-top to make
room) is injected. The simulator keeps its original colors and width.
"""

import argparse
import json
import os
import re
import sys

ADAPTER_STYLE_FULL = r"""
<!-- ======= Open Skill Diary theme adapter (injected) ======= -->
<style id="osd-theme-adapter">
  /* Reserve space for the floating bar — adapter does NOT touch the simulator's
     own max-width / centering. If the simulator has .container { max-width: ...;
     margin: 0 auto } it stays centered; if it has none, it stays full-width. */
  body { padding-top: 56px !important; }

  /* Allow page to grow naturally — many simulators set
     html, body { height:100%; overflow:hidden } to lock viewport. The adapter
     overrides this so floating bar is reachable via scroll. */
  html, body {
    height: auto !important;
    min-height: 100% !important;
    overflow: visible !important;
    overflow-y: auto !important;
  }

  /* Bidirectional inversion: applied only when the source tone differs from
     the selected blog theme. If they match, the original colors are kept
     untouched. The wrapper isolates the filter from the floating bar. */
  html[data-osd-source-theme="dark"][data-osd-theme="light"] body { background: #f7f8fb !important; }
  html[data-osd-source-theme="light"][data-osd-theme="dark"] body { background: #0c1220 !important; }

  html[data-osd-source-theme="dark"][data-osd-theme="light"] #osd-content-wrapper,
  html[data-osd-source-theme="light"][data-osd-theme="dark"] #osd-content-wrapper {
    filter: invert(0.92) hue-rotate(180deg);
    min-height: 100vh;
  }
  html[data-osd-source-theme="dark"][data-osd-theme="light"] #osd-content-wrapper img,
  html[data-osd-source-theme="dark"][data-osd-theme="light"] #osd-content-wrapper svg,
  html[data-osd-source-theme="dark"][data-osd-theme="light"] #osd-content-wrapper video,
  html[data-osd-source-theme="dark"][data-osd-theme="light"] #osd-content-wrapper canvas,
  html[data-osd-source-theme="light"][data-osd-theme="dark"] #osd-content-wrapper img,
  html[data-osd-source-theme="light"][data-osd-theme="dark"] #osd-content-wrapper svg,
  html[data-osd-source-theme="light"][data-osd-theme="dark"] #osd-content-wrapper video,
  html[data-osd-source-theme="light"][data-osd-theme="dark"] #osd-content-wrapper canvas {
    filter: invert(1) hue-rotate(180deg);
  }

  /* Floating top bar — fixed, very high z-index, sits above wrapper */
  #osd-bar {
    position: fixed; top: 0; left: 0; right: 0; z-index: 2147483647;
    display: flex; align-items: center; justify-content: space-between;
    gap: 12px; padding: 10px 16px;
    background: rgba(15, 22, 36, 0.85);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(255,255,255,0.12);
    color: #e8eef9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Pretendard",
                 "Noto Sans KR", sans-serif;
    font-size: 13px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
  }
  html[data-osd-theme="light"] #osd-bar {
    background: rgba(255,255,255,0.92);
    border-bottom: 1px solid #e3e8ef;
    color: #1a2332;
    box-shadow: 0 1px 3px rgba(20,30,50,0.06), 0 4px 16px rgba(20,30,50,0.04);
  }
  #osd-bar a, #osd-bar button {
    color: inherit; background: transparent; border: 1px solid currentColor;
    border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 600;
    text-decoration: none; cursor: pointer;
    opacity: 0.85; transition: opacity .15s, transform .15s;
    font-family: inherit;
  }
  #osd-bar a:hover, #osd-bar button:hover { opacity: 1; transform: translateY(-1px); }
  #osd-bar .osd-bar__title { font-weight: 700; letter-spacing: -0.2px; opacity: 0.9;
    flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
  #osd-bar .osd-bar__actions { display: flex; gap: 8px; flex-shrink: 0; }
  #osd-bar .osd-bar__brand { font-weight: 700; font-size: 13px; opacity: 0.7; flex-shrink: 0; }
  @media (max-width: 640px) {
    #osd-bar { padding: 8px 10px; font-size: 12px; }
    #osd-bar .osd-bar__title { display: none; }
  }
</style>
<script>
  (function(){
    document.documentElement.setAttribute('data-osd-source-theme', '__SOURCE_THEME__');
    try {
      var t = localStorage.getItem('blog-theme') || 'dark';
      document.documentElement.setAttribute('data-osd-theme', t);
    } catch(e){}
  })();
</script>
<!-- ======= /theme adapter ======= -->
"""

# Lite version: only floating bar + bar spacing, no filter inversion, no width override
ADAPTER_STYLE_NOTHEME = r"""
<!-- ======= Open Skill Diary adapter (no-theme) ======= -->
<style id="osd-theme-adapter">
  /* Reserve space for the floating bar — simulator's own width is preserved */
  body { padding-top: 56px !important; }
  /* Override viewport-lock that some simulators set so page can scroll */
  html, body {
    height: auto !important;
    min-height: 100% !important;
    overflow: visible !important;
    overflow-y: auto !important;
  }
  #osd-bar {
    position: fixed; top: 0; left: 0; right: 0; z-index: 2147483647;
    display: flex; align-items: center; justify-content: space-between;
    gap: 12px; padding: 10px 16px;
    background: rgba(15, 22, 36, 0.85);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(255,255,255,0.12);
    color: #e8eef9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Pretendard",
                 "Noto Sans KR", sans-serif;
    font-size: 13px;
  }
  #osd-bar a { color: inherit; background: transparent; border: 1px solid currentColor;
    border-radius: 8px; padding: 6px 12px; font-size: 12px; font-weight: 600;
    text-decoration: none; opacity: 0.85; }
  #osd-bar a:hover { opacity: 1; }
  #osd-bar .osd-bar__title { font-weight: 700; flex: 1; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; min-width: 0; }
  #osd-bar .osd-bar__actions { display: flex; gap: 8px; }
  #osd-bar .osd-bar__brand { font-weight: 700; opacity: 0.7; }
</style>
<!-- ======= /adapter ======= -->
"""

WRAP_SCRIPT = r"""
<script>
  // Wrap body content so the light-mode filter applies only to wrapper, not to floating bar
  (function(){
    function wrap(){
      var bar = document.getElementById('osd-bar');
      var wrapper = document.createElement('div');
      wrapper.id = 'osd-content-wrapper';
      wrapper.style.cssText = 'transition: filter .25s;';
      var nodes = Array.prototype.slice.call(document.body.childNodes);
      nodes.forEach(function(n){ if (n === bar) return; wrapper.appendChild(n); });
      document.body.appendChild(wrapper);
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', wrap, { once: true });
    } else { wrap(); }
  })();
</script>
"""

THEME_TOGGLE_SCRIPT = r"""
<script>
  (function(){
    var btn = document.getElementById('osd-theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', function(){
      var cur = document.documentElement.getAttribute('data-osd-theme') || 'dark';
      var next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-osd-theme', next);
      try { localStorage.setItem('blog-theme', next); } catch(e){}
    });
  })();
</script>
"""


def make_bar(title: str, with_theme: bool) -> str:
    theme_btn = '<button type="button" id="osd-theme-toggle" aria-label="테마 전환">테마</button>' if with_theme else ''
    return f'''
<!-- ======= OSD floating bar (injected) ======= -->
<div id="osd-bar" role="navigation" aria-label="블로그 네비게이션">
  <a href="../../index.html" class="osd-bar__brand" title="블로그 홈">◆ Diary</a>
  <div class="osd-bar__title">{title}</div>
  <div class="osd-bar__actions">
    <a href="../../index.html">← 목록</a>
    {theme_btn}
  </div>
</div>
<!-- ======= /OSD floating bar ======= -->
'''


_NAMED_COLOR_LUM = {
    'white': 1.0, 'beige': 0.91, 'ivory': 0.99, 'snow': 0.99,
    'lightgray': 0.83, 'lightgrey': 0.83, 'silver': 0.75,
    'wheat': 0.85, 'linen': 0.95, 'cornsilk': 0.96, 'floralwhite': 0.98,
    'antiquewhite': 0.93, 'oldlace': 0.97, 'seashell': 0.97,
    'gainsboro': 0.86, 'whitesmoke': 0.96, 'papayawhip': 0.93,
    'black': 0.0, 'darkslategray': 0.18, 'darkslategrey': 0.18,
    'navy': 0.04, 'midnightblue': 0.06, 'darkblue': 0.05,
    'darkgray': 0.66, 'darkgrey': 0.66, 'gray': 0.50, 'grey': 0.50,
    'dimgray': 0.41, 'dimgrey': 0.41, 'slategray': 0.45, 'slategrey': 0.45,
    'maroon': 0.18, 'darkred': 0.18, 'darkgreen': 0.20,
    'transparent': None,
}


def _color_to_luminance(value: str):
    """Return relative luminance (0..1) for a CSS color string, or None."""
    v = value.strip().lower().rstrip(';').strip()
    if not v:
        return None
    if v.startswith('#'):
        h = v.lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        if len(h) != 6:
            return None
        try:
            r = int(h[0:2], 16) / 255.0
            g = int(h[2:4], 16) / 255.0
            b = int(h[4:6], 16) / 255.0
        except ValueError:
            return None
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    if v.startswith('rgb'):
        m = re.match(r'rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)', v)
        if m:
            r = int(m.group(1)) / 255.0
            g = int(m.group(2)) / 255.0
            b = int(m.group(3)) / 255.0
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
    if v in _NAMED_COLOR_LUM:
        return _NAMED_COLOR_LUM[v]
    return None


def detect_source_theme(html: str) -> str:
    """Heuristically classify the source HTML's dominant background as
    'light' or 'dark'. Falls back to 'dark' (legacy default) when no signal."""

    def _classify(value: str):
        first = value.strip().split()[0] if value.strip() else ''
        lum = _color_to_luminance(first)
        if lum is None:
            return None
        return 'light' if lum > 0.6 else 'dark'

    # 1) <body style="background[-color]: ...">
    m = re.search(r'<body\b[^>]*\bstyle\s*=\s*["\']([^"\']*)["\']',
                  html, flags=re.IGNORECASE)
    if m:
        bg = re.search(r'background(?:-color)?\s*:\s*([^;]+)',
                       m.group(1), flags=re.IGNORECASE)
        if bg:
            verdict = _classify(bg.group(1))
            if verdict:
                return verdict

    # 2) inline <style> blocks: body { background } / html { background } /
    #    :root { --bg: } / :root { --background: }
    for sm in re.finditer(r'<style\b[^>]*>(.*?)</style>',
                          html, flags=re.IGNORECASE | re.DOTALL):
        css = sm.group(1)
        for pat in (
            r'(?:^|[\}\s])body\s*\{[^}]*?background(?:-color)?\s*:\s*([^;}\n]+)',
            r'(?:^|[\}\s])html\s*\{[^}]*?background(?:-color)?\s*:\s*([^;}\n]+)',
            r':root\s*\{[^}]*?--(?:bg|background)[A-Za-z0-9_-]*\s*:\s*([^;}\n]+)',
        ):
            rm = re.search(pat, css, flags=re.IGNORECASE)
            if rm:
                verdict = _classify(rm.group(1))
                if verdict:
                    return verdict

    return 'dark'


FIT_VIEWPORT_STYLE = r"""
<!-- ======= OSD fit-viewport (max-width override) ======= -->
<style id="osd-fit-viewport">
  /* Reset simulator's own max-width so layout fills viewport.
     Best for responsive simulators whose children also flex. */
  html, body { max-width: 100% !important; }
  .layout, .simulator, .container, main, .wrap, .wrapper, .page, .app, .root,
  [class*="container"], [class*="wrapper"] {
    max-width: 100% !important;
    width: 100% !important;
  }
</style>
<!-- ======= /fit-viewport ======= -->
"""

SCALE_UP_SCRIPT = r"""
<!-- ======= OSD scale-up (CSS transform: scale) ======= -->
<style id="osd-scale-up-style">
  #osd-content-wrapper { transform-origin: top left; }
</style>
<script>
  (function(){
    function setup(){
      var wrap = document.getElementById('osd-content-wrapper');
      if (!wrap) return;
      var measured = false;
      var nat = 0;
      function fit(){
        wrap.style.transform = 'scale(1)';
        if (!measured) {
          // measure natural width once after first paint, with scale=1
          nat = wrap.scrollWidth;
          measured = true;
        }
        var vw = document.documentElement.clientWidth;
        if (nat > 0 && vw > nat) {
          var s = vw / nat;
          wrap.style.transform = 'scale(' + s + ')';
          // height compensation: scaled body needs proportional space
          wrap.style.minHeight = (window.innerHeight / s) + 'px';
        }
      }
      // initial fit on next frame so children laid out
      requestAnimationFrame(function(){ requestAnimationFrame(fit); });
      var t = null;
      window.addEventListener('resize', function(){
        clearTimeout(t);
        t = setTimeout(function(){ measured = false; fit(); }, 80);
      });
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', setup, { once: true });
    } else { setup(); }
  })();
</script>
<!-- ======= /scale-up ======= -->
"""


def inject(html: str, title: str, with_theme: bool = True,
           fit_mode: str = 'native') -> str:
    """fit_mode: 'native' (default — preserve simulator's own width),
       'viewport' (remove simulator max-width to fill viewport — best for responsive),
       'scale' (CSS transform: scale to enlarge — best for fixed-pixel simulators)."""
    source_theme = detect_source_theme(html) if with_theme else 'dark'
    style = ADAPTER_STYLE_FULL if with_theme else ADAPTER_STYLE_NOTHEME
    style = style.replace('__SOURCE_THEME__', source_theme)
    if fit_mode == 'viewport':
        style = style + FIT_VIEWPORT_STYLE
    bar = make_bar(title, with_theme)

    # Insert adapter style+script right after <head>
    new = re.sub(r'(<head\b[^>]*>)', r'\1' + style, html, count=1, flags=re.IGNORECASE)
    if new == html:
        new = '<head>' + style + '</head>' + html

    # Insert bar + scripts right after <body>
    body_payload = bar + (WRAP_SCRIPT if with_theme else '') + (THEME_TOGGLE_SCRIPT if with_theme else '')
    if fit_mode == 'scale' and with_theme:
        # scale only meaningful when wrapper exists (with_theme creates it)
        body_payload += SCALE_UP_SCRIPT
    new2 = re.sub(r'(<body\b[^>]*>)', r'\1' + body_payload, new, count=1, flags=re.IGNORECASE)
    if new2 == new:
        new2 = '<body>' + body_payload + new + '</body>'

    return new2


def slugify(name: str) -> str:
    base = os.path.splitext(os.path.basename(name))[0]
    s = re.sub(r'[^\w\s-]', '', base, flags=re.UNICODE).strip().lower()
    s = re.sub(r'[-\s_]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s or 'post'


def extract_title(html: str, fallback: str) -> str:
    m = re.search(r'<title>(.*?)</title>', html, flags=re.IGNORECASE | re.DOTALL)
    if m:
        t = re.sub(r'\s+', ' ', m.group(1)).strip()
        if t:
            return t
    m = re.search(r'<h1\b[^>]*>(.*?)</h1>', html, flags=re.IGNORECASE | re.DOTALL)
    if m:
        t = re.sub(r'<[^>]+>', '', m.group(1))
        t = re.sub(r'\s+', ' ', t).strip()
        if t:
            return t
    return fallback


def main(argv=None):
    ap = argparse.ArgumentParser(description='Inject OSD theme adapter into HTML simulator')
    ap.add_argument('--src', help='Single source HTML file')
    ap.add_argument('--dst', help='Destination HTML path (with --src)')
    ap.add_argument('--title', help='Title to display in floating bar (with --src)')
    ap.add_argument('--src-dir', help='Source directory (batch)')
    ap.add_argument('--dst-dir', help='Destination directory (batch)')
    ap.add_argument('--map', help='JSON file: [{"src":"a.html","dst":"slug.html","title":"..."}, ...]')
    ap.add_argument('--no-theme', action='store_true', help='Skip light/dark adapter, only full-width + bar')
    ap.add_argument('--fit-viewport', action='store_true',
                    help='Remove simulator max-width to fill viewport (best for responsive layouts)')
    ap.add_argument('--scale-up', action='store_true',
                    help='CSS transform: scale wrapper to viewport width (best for fixed-pixel simulators)')
    args = ap.parse_args(argv)

    if args.fit_viewport and args.scale_up:
        ap.error('--fit-viewport and --scale-up are mutually exclusive — pick one.')
    fit_mode = 'viewport' if args.fit_viewport else ('scale' if args.scale_up else 'native')

    with_theme = not args.no_theme
    jobs = []

    if args.map:
        with open(args.map, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
    elif args.src and args.dst:
        jobs = [{'src': args.src, 'dst': args.dst, 'title': args.title or extract_title(open(args.src, encoding='utf-8').read(), slugify(args.src))}]
    elif args.src_dir and args.dst_dir:
        for fn in sorted(os.listdir(args.src_dir)):
            if not fn.lower().endswith('.html'):
                continue
            src_path = os.path.join(args.src_dir, fn)
            slug = slugify(fn)
            dst_path = os.path.join(args.dst_dir, f'{slug}.html')
            with open(src_path, 'r', encoding='utf-8') as f:
                title = extract_title(f.read(), slug)
            jobs.append({'src': src_path, 'dst': dst_path, 'title': title})
    else:
        ap.error('Provide --src+--dst, --src-dir+--dst-dir, or --map')

    ok = 0
    for j in jobs:
        with open(j['src'], 'r', encoding='utf-8') as f:
            html = f.read()
        # Per-job override via --map: {"src":..., "dst":..., "title":..., "fit":"viewport|scale|native"}
        job_fit = j.get('fit') or fit_mode
        out = inject(html, j['title'], with_theme=with_theme, fit_mode=job_fit)
        os.makedirs(os.path.dirname(os.path.abspath(j['dst'])), exist_ok=True)
        with open(j['dst'], 'w', encoding='utf-8') as f:
            f.write(out)
        print(f'OK  {j["src"]}  ->  {j["dst"]}  (title="{j["title"]}", {len(out)} bytes)')
        ok += 1
    print(f'\n{ok}/{len(jobs)} files processed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
