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

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
