#!/usr/bin/env python3
"""
extract_original_html.py — reverse of inject_html_adapter.py

Reads a published HTML post and writes the pre-injection original by
stripping the OSD theme adapter blocks (style + floating bar + scripts).

Used by `/hams:diary --rebuild-remote {slug}` when the repo's `_src/{slug}.html`
backup is missing — the original HTML is reconstructed from the published
`posts/{slug}.html`, then re-fed through inject_html_adapter for re-themeing.

Usage:
    python extract_original_html.py --src posts/foo.html --dst _src/foo.html
"""

import argparse
import os
import re
import sys

# Marker-wrapped blocks. The inject script emits matching open/close comments
# around the style and floating-bar regions, so we can strip them safely.
MARKER_PATTERNS = [
    # ADAPTER_STYLE_FULL: <style id="osd-theme-adapter"> + SOURCE_THEME setter <script>
    re.compile(
        r'<!--\s*=+\s*Open Skill Diary theme adapter \(injected\)\s*=+\s*-->'
        r'.*?'
        r'<!--\s*=+\s*/theme adapter\s*=+\s*-->\s*',
        re.DOTALL | re.IGNORECASE,
    ),
    # ADAPTER_STYLE_NOTHEME: lighter variant (no filter, no SOURCE_THEME setter)
    re.compile(
        r'<!--\s*=+\s*Open Skill Diary adapter \(no-theme\)\s*=+\s*-->'
        r'.*?'
        r'<!--\s*=+\s*/adapter\s*=+\s*-->\s*',
        re.DOTALL | re.IGNORECASE,
    ),
    # Floating navigation bar (the visible top strip)
    re.compile(
        r'<!--\s*=+\s*OSD floating bar \(injected\)\s*=+\s*-->'
        r'.*?'
        r'<!--\s*=+\s*/OSD floating bar\s*=+\s*-->\s*',
        re.DOTALL | re.IGNORECASE,
    ),
]

# Marker-less <script> blocks injected by inject (WRAP_SCRIPT, THEME_TOGGLE_SCRIPT).
# Identified by unique strings inside their bodies.
SCRIPT_SIGNATURES = (
    "osd-content-wrapper",  # WRAP_SCRIPT
    "osd-theme-toggle",     # THEME_TOGGLE_SCRIPT
)

SCRIPT_BLOCK_RE = re.compile(
    r'<script\b[^>]*>.*?</script>\s*',
    re.DOTALL | re.IGNORECASE,
)


def strip_adapter(html: str) -> str:
    """Remove every adapter-injected fragment, returning the original HTML."""
    out = html

    for pat in MARKER_PATTERNS:
        out = pat.sub('', out)

    def _maybe_strip(m: re.Match) -> str:
        block = m.group(0)
        for sig in SCRIPT_SIGNATURES:
            if sig in block:
                return ''
        return block

    out = SCRIPT_BLOCK_RE.sub(_maybe_strip, out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='Strip OSD adapter to recover pre-injection HTML')
    ap.add_argument('--src', required=True, help='Published HTML (post output)')
    ap.add_argument('--dst', required=True, help='Destination path for stripped original')
    args = ap.parse_args(argv)

    with open(args.src, 'r', encoding='utf-8') as f:
        html = f.read()
    out = strip_adapter(html)

    os.makedirs(os.path.dirname(os.path.abspath(args.dst)), exist_ok=True)
    with open(args.dst, 'w', encoding='utf-8') as f:
        f.write(out)

    delta = len(html) - len(out)
    print(f'OK  {args.src}  ->  {args.dst}  '
          f'(stripped {delta} bytes; {len(out)} bytes remain)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
