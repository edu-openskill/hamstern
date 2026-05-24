"""Bundle hamstern data into docs/data/ for the static gh-pages viewer.

Stdlib only — pathlib, json, shutil, argparse, datetime.

Sub-D/E: single-project (.hamstern/*.md → docs/data/*).
Sub-F: multi-project (hamstern-data/projects/{uuid}/* → docs/data/p/{uuid}/*).
"""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
SCHEMA_VERSION_MULTI = 2


def run_single_project(src_dir: Path, out_dir: Path) -> dict:
    """직접 source 디렉터리를 받아 out 으로 번들. .hamstern 가정 없음.

    Sub-F: src_dir = hamstern-data/projects/{uuid}/
    Sub-D/E 호환: run() wrapper 가 project_root/.hamstern 으로 호출.
    """
    src_dir = Path(src_dir)
    out_dir = Path(out_dir)

    # stale 정리
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
        "mockups": []
    }

    decisions_src = src_dir / "decisions.md"
    if decisions_src.is_file():
        shutil.copy2(decisions_src, out_dir / "decisions.md")
        manifest["decisions"] = True

    log_src = src_dir / "decisions-log.md"
    if log_src.is_file():
        shutil.copy2(log_src, out_dir / "decisions-log.md")
        manifest["decisions_log"] = True

    sessions_src = src_dir / "sessions"
    if sessions_src.is_dir():
        sessions_out = out_dir / "sessions"
        sessions_out.mkdir(exist_ok=True)
        names = []
        for f in sorted(sessions_src.glob("*.md"),
                        key=lambda p: (-p.stat().st_mtime, p.name)):
            shutil.copy2(f, sessions_out / f.name)
            names.append(f.name)
        manifest["sessions"] = names

    # Sub-F: mockups
    mockups_src = src_dir / "mockups"
    if mockups_src.is_dir():
        mockups_out = out_dir / "mockups"
        mockups_out.mkdir(exist_ok=True)
        mockup_names = []
        for f in sorted(mockups_src.iterdir(), key=lambda p: p.name):
            if f.is_file() and f.name != "_index.json":
                shutil.copy2(f, mockups_out / f.name)
                mockup_names.append(f.name)
        idx = mockups_src / "_index.json"
        if idx.exists():
            shutil.copy2(idx, mockups_out / "_index.json")
        manifest["mockups"] = mockup_names

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def run(project_root: Path, out_dir: Path) -> dict:
    """Sub-D/E 호환: project_root/.hamstern → out_dir."""
    return run_single_project(Path(project_root) / ".hamstern", out_dir)


def run_multiproject(hamstern_data: Path, out_dir: Path) -> dict:
    """Sub-F: hamstern-data/projects/* 전체를 docs/data/p/{uuid}/ 로 번들."""
    hamstern_data = Path(hamstern_data)
    out_dir = Path(out_dir)

    # stale 정리
    if out_dir.exists():
        for child in out_dir.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
    out_dir.mkdir(parents=True, exist_ok=True)

    index_file = hamstern_data / "projects" / "_index.json"
    if not index_file.exists():
        root_manifest = {
            "schema_version": SCHEMA_VERSION_MULTI,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "projects": {}
        }
        (out_dir / "manifest.json").write_text(
            json.dumps(root_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return root_manifest

    index = json.loads(index_file.read_text(encoding="utf-8"))

    root_manifest = {
        "schema_version": SCHEMA_VERSION_MULTI,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "projects": {}
    }

    p_out = out_dir / "p"
    p_out.mkdir(exist_ok=True)

    for uuid, info in index.items():
        proj_src = hamstern_data / "projects" / uuid
        if not proj_src.is_dir():
            continue  # skip stale index entries
        proj_out = p_out / uuid
        proj_out.mkdir(exist_ok=True)

        proj_manifest = run_single_project(proj_src, proj_out)

        root_manifest["projects"][uuid] = {
            "name": info["name"],
            "last_active": info.get("last_active", ""),
            "decision_count": info.get("decision_count", 0),
            "session_count": info.get("session_count", 0),
            "mockup_count": info.get("mockup_count", 0),
            "has_decisions": proj_manifest["decisions"],
            "has_log": proj_manifest["decisions_log"],
            "sessions": proj_manifest["sessions"],
            "mockups": proj_manifest.get("mockups", [])
        }

    (out_dir / "manifest.json").write_text(
        json.dumps(root_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return root_manifest


def main():
    parser = argparse.ArgumentParser(description="Bundle hamstern data -> docs/data")
    parser.add_argument("--project", default=".", help="Sub-D/E 호환: 프로젝트 루트")
    parser.add_argument("--out", default="docs/data", help="출력 디렉터리")
    parser.add_argument("--hamstern-data", help="Sub-F: hamstern-data 루트 (지정 시 multi-project)")
    args = parser.parse_args()

    if args.hamstern_data:
        project = Path(args.hamstern_data).resolve()
        out = Path(args.out) if Path(args.out).is_absolute() else project / args.out
        manifest = run_multiproject(hamstern_data=project, out_dir=out)
        print(f"multi-project bundle: {len(manifest['projects'])} projects")
    else:
        project = Path(args.project).resolve()
        out = Path(args.out)
        if not out.is_absolute():
            out = project / out
        manifest = run_single_project(project / ".hamstern", out)
        print(f"single-project bundle: decisions={manifest['decisions']} sessions={len(manifest['sessions'])}")


if __name__ == "__main__":
    main()
