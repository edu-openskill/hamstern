import json, os, sys, glob, subprocess
from collections import namedtuple

Finding = namedtuple("Finding", "severity location message")


def _home():
    return os.environ.get("HOME") or os.environ.get("USERPROFILE") or os.path.expanduser("~")


def resolve_active_project():
    cfg = os.path.join(_home(), ".config", "hamstern", "active-project.json")
    if not os.path.isfile(cfg):
        sys.exit('❌ active project 없음. /hams:link "name" 또는 /hams:init "name" 먼저.')
    with open(cfg, encoding="utf-8") as f:
        c = json.load(f)
    proj_dir = os.path.join(c["hamstern_data_path"], "projects", c["uuid"])
    return {"uuid": c["uuid"], "name": c["name"],
            "hamstern_data": c["hamstern_data_path"], "proj_dir": proj_dir}


def _meta_path(active):
    return os.path.join(active["proj_dir"], "meta.json")


def load_meta(active):
    with open(_meta_path(active), encoding="utf-8") as f:
        return json.load(f)


def save_meta(active, meta):
    with open(_meta_path(active), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def resolve_globs(project_root, ssot_paths):
    files = []
    for pat in ssot_paths:
        for m in glob.glob(os.path.join(project_root, pat), recursive=True):
            if os.path.isfile(m):
                files.append(os.path.relpath(m, project_root).replace(os.sep, "/"))
    return sorted(set(files))


def check_pointers(project_root, ssot_paths):
    findings = []
    for pat in ssot_paths:
        hits = glob.glob(os.path.join(project_root, pat), recursive=True)
        if not any(os.path.isfile(h) for h in hits):
            findings.append(Finding("ERROR", pat,
                                    "지정된 SSOT 경로가 더는 존재하지 않음 (메타-드리프트)"))
    return findings


def parse_finding_line(line):
    parts = line.rstrip("\n").split("\t")
    if len(parts) != 3 or parts[0] not in ("ERROR", "WARN"):
        return None
    return Finding(parts[0], parts[1], parts[2])


def discover_extractors(project_root, builtin_dir):
    found = [os.path.join(builtin_dir, "skill_registry_check.py")]
    seam = os.path.join(project_root, ".hamstern", "ssot-extractors")
    if os.path.isdir(seam):
        for f in sorted(os.listdir(seam)):
            if f.endswith(".sh"):
                found.append(os.path.join(seam, f))
    return found


def run_extractors(project_root, ssot_files, extractor_paths):
    findings = []
    for ext in extractor_paths:
        cmd = ([sys.executable, ext] if ext.endswith(".py") else ["bash", ext])
        proc = subprocess.run(cmd + [project_root, *ssot_files],
                              capture_output=True, text=True)
        for line in proc.stdout.splitlines():
            f = parse_finding_line(line)
            if f:
                findings.append(f)
    return findings


def format_report(findings):
    if not findings:
        return "✅ SSOT freshness: 이상 없음"
    icon = {"ERROR": "🔴", "WARN": "⚠️"}
    lines = ["SSOT freshness 리포트 (advisory):"]
    for f in findings:
        lines.append(f"  {icon[f.severity]} {f.location} · {f.message}")
    return "\n".join(lines)
