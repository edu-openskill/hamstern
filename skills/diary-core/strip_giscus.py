#!/usr/bin/env python3
"""Strip hamstern giscus comment blocks from already-published posts.

Usage:
  python strip_giscus.py <posts_dir> [--dry-run]

Walks posts_dir for *.html and removes the region between
<!-- hamstern:comments:start --> and <!-- hamstern:comments:end -->
(markers included). Prints per-file action and summary.
"""
import argparse
import pathlib
import re
import sys

START = '<!-- hamstern:comments:start -->'
END = '<!-- hamstern:comments:end -->'
PAT = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.DOTALL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('posts_dir')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    root = pathlib.Path(args.posts_dir)
    if not root.is_dir():
        sys.exit(f'not a directory: {root}')

    changed = unchanged = 0
    for p in sorted(root.rglob('*.html')):
        src = p.read_text(encoding='utf-8')
        new = PAT.sub('', src)
        new = re.sub(r'\n\s*\n\s*\n', '\n\n', new)
        if new != src:
            print(f'[strip] {p}')
            if not args.dry_run:
                p.write_text(new, encoding='utf-8')
            changed += 1
        else:
            unchanged += 1

    suffix = 'dry-run' if args.dry_run else 'applied'
    print(f'\n{changed} stripped, {unchanged} unchanged ({suffix})')


if __name__ == '__main__':
    main()
