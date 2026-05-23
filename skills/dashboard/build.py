"""Bundle .hamstern/*.md into docs/data/ for the static gh-pages viewer.

Stdlib only — pathlib, json, shutil, argparse, datetime.
"""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1


def run(project_root: Path, out_dir: Path) -> dict:
    """Bundle .hamstern -> out_dir. Returns the manifest dict."""
    project_root = Path(project_root)
    out_dir = Path(out_dir)
    src = project_root / ".hamstern"

    if out_dir.exists():
        for child in out_dir.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decisions": False,
        "decisions_log": False,
        "sessions": [],
    }

    decisions_src = src / "decisions.md"
    if decisions_src.is_file():
        shutil.copy2(decisions_src, out_dir / "decisions.md")
        manifest["decisions"] = True

    log_src = src / "decisions-log.md"
    if log_src.is_file():
        shutil.copy2(log_src, out_dir / "decisions-log.md")
        manifest["decisions_log"] = True

    sessions_src = src / "sessions"
    if sessions_src.is_dir():
        sessions_out = out_dir / "sessions"
        sessions_out.mkdir(exist_ok=True)
        names = []
        for f in sorted(sessions_src.glob("*.md"),
                        key=lambda p: (-p.stat().st_mtime, p.name)):
            shutil.copy2(f, sessions_out / f.name)
            names.append(f.name)
        manifest["sessions"] = names

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Bundle .hamstern -> docs/data")
    parser.add_argument("--project", default=".", help="프로젝트 루트 (.hamstern/ 가 있는 곳)")
    parser.add_argument("--out", default="docs/data", help="출력 디렉터리 (project 기준 상대 또는 절대)")
    args = parser.parse_args()
    project = Path(args.project).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = project / out
    manifest = run(project_root=project, out_dir=out)
    print(f"built: decisions={manifest['decisions']} log={manifest['decisions_log']} sessions={len(manifest['sessions'])}")


if __name__ == "__main__":
    main()
