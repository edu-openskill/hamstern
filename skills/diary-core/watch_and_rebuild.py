#!/usr/bin/env python3
"""
watch_and_rebuild.py — file watcher for /hams:diary edit mode

Polls a single source file's mtime and re-runs the appropriate build step
when it changes. Designed for the worktree-based edit flow where the user
edits `_src/{slug}.{ext}` and expects `posts/{postId}/{slug}.html` to update.

Usage:
    python watch_and_rebuild.py \
        --src   _src/msa-k8s-websocket.html \
        --dst   posts/1/msa-k8s-websocket.html \
        --engine html \
        --title "MSA · K8s · WebSocket 통합" \
        [--no-theme]

    python watch_and_rebuild.py \
        --src   _src/lecture-1.md \
        --dst   posts/2/lecture-1.html \
        --engine md \
        --frame _post-frame.html \
        --title "Lecture 1" --category 강의 --date 2026-04-26 \
        --blog-title "My Blog"

Stops cleanly on Ctrl-C. Stops automatically if the dst directory disappears.

For MD engine the script reads the .md, calls the same minimal converter
the skill uses (or you can pre-render via SKILL.md inline logic and just
overwrite). For HTML engine it shells out to inject_html_adapter.py.
"""

import argparse
import os
import re
import subprocess
import sys
import time

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
INJECTOR = os.path.join(THIS_DIR, 'inject_html_adapter.py')


def now():
    return time.strftime('%H:%M:%S')


def render_md_minimal(md: str) -> str:
    """Tiny MD→HTML converter matching the skill's inline rules."""
    # Strip frontmatter
    md = re.sub(r'^---\n.*?\n---\n', '', md, count=1, flags=re.DOTALL)
    lines = md.split('\n')
    out = []
    in_code = False
    in_ul = False
    in_ol = False

    def flush_lists():
        nonlocal in_ul, in_ol
        if in_ul: out.append('</ul>'); in_ul = False
        if in_ol: out.append('</ol>'); in_ol = False

    for line in lines:
        if line.startswith('```'):
            flush_lists()
            if not in_code:
                lang = line[3:].strip()
                out.append(f'<pre><code class="language-{lang}">'); in_code = True
            else:
                out.append('</code></pre>'); in_code = False
            continue
        if in_code:
            out.append(html_escape(line)); continue
        if not line.strip():
            flush_lists()
            out.append('')
            continue

        # Headings
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m:
            flush_lists()
            level = len(m.group(1))
            out.append(f'<h{level}>{inline(m.group(2))}</h{level}>')
            continue
        # UL
        m = re.match(r'^[-*]\s+(.*)$', line)
        if m:
            if not in_ul: flush_lists(); out.append('<ul>'); in_ul = True
            out.append(f'<li>{inline(m.group(1))}</li>')
            continue
        # OL
        m = re.match(r'^\d+\.\s+(.*)$', line)
        if m:
            if not in_ol: flush_lists(); out.append('<ol>'); in_ol = True
            out.append(f'<li>{inline(m.group(1))}</li>')
            continue
        # Blockquote
        m = re.match(r'^>\s?(.*)$', line)
        if m:
            flush_lists()
            out.append(f'<blockquote>{inline(m.group(1))}</blockquote>')
            continue
        # Paragraph
        flush_lists()
        out.append(f'<p>{inline(line)}</p>')

    flush_lists()
    if in_code: out.append('</code></pre>')
    return '\n'.join(out)


def html_escape(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def inline(s: str) -> str:
    """Apply inline markdown: **bold**, _italic_, `code`, [link](url)."""
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'_([^_]+)_', r'<em>\1</em>', s)
    return s


def build_md(src, dst, frame_path, vars_):
    with open(src, 'r', encoding='utf-8') as f:
        md = f.read()
    body = render_md_minimal(md)
    with open(frame_path, 'r', encoding='utf-8') as f:
        frame = f.read()
    out = frame
    for k, v in vars_.items():
        out = out.replace('{{' + k + '}}', v or '')
    out = out.replace('{{POST_HTML}}', body)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(out)


def build_html(src, dst, title, no_theme):
    cmd = [sys.executable, INJECTOR, '--src', src, '--dst', dst, '--title', title]
    if no_theme:
        cmd.append('--no-theme')
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--dst', required=True)
    ap.add_argument('--engine', choices=['md', 'html'], required=True)
    ap.add_argument('--title', default='')
    ap.add_argument('--category', default='')
    ap.add_argument('--date', default='')
    ap.add_argument('--blog-title', default='')
    ap.add_argument('--frame', default='', help='_post-frame.html (md engine only)')
    ap.add_argument('--no-theme', action='store_true')
    ap.add_argument('--interval', type=float, default=0.7)
    args = ap.parse_args()

    if not os.path.exists(args.src):
        print(f'ERR: src not found: {args.src}', file=sys.stderr); sys.exit(2)
    if args.engine == 'md' and not args.frame:
        print('ERR: --frame is required for md engine', file=sys.stderr); sys.exit(2)

    vars_ = {
        'POST_TITLE': args.title,
        'POST_CATEGORY': args.category,
        'POST_DATE': args.date,
        'BLOG_TITLE': args.blog_title,
    }

    last = None
    print(f'[{now()}] watching {args.src} → {args.dst} (engine={args.engine})')
    print(f'[{now()}] save the source file in your editor; this script rebuilds automatically.')
    print(f'[{now()}] press Ctrl-C when done.')

    try:
        while True:
            try:
                m = os.path.getmtime(args.src)
            except FileNotFoundError:
                time.sleep(args.interval); continue
            if m != last:
                last = m
                try:
                    if args.engine == 'md':
                        build_md(args.src, args.dst, args.frame, vars_)
                    else:
                        build_html(args.src, args.dst, args.title or os.path.basename(args.src), args.no_theme)
                    print(f'[{now()}] rebuilt {args.dst}  — refresh browser to see changes.')
                except subprocess.CalledProcessError as e:
                    print(f'[{now()}] BUILD ERROR: {e}', file=sys.stderr)
                except Exception as e:
                    print(f'[{now()}] BUILD ERROR: {e}', file=sys.stderr)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f'\n[{now()}] watcher stopped.')


if __name__ == '__main__':
    main()
