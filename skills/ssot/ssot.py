import json, os, sys, glob, subprocess
from collections import namedtuple

Finding = namedtuple("Finding", "severity location message")


def _home():
    return os.environ.get("HOME") or os.environ.get("USERPROFILE") or os.path.expanduser("~")


def resolve_active_project():
    cfg = os.path.join(_home(), ".config", "hamstern", "active-project.json")
    if not os.path.isfile(cfg):
        sys.exit('❌ active project 없음. /hams:link "name" 또는 /hams:init "name" 먼저.')
    c = json.load(open(cfg, encoding="utf-8"))
    proj_dir = os.path.join(c["hamstern_data_path"], "projects", c["uuid"])
    return {"uuid": c["uuid"], "name": c["name"],
            "hamstern_data": c["hamstern_data_path"], "proj_dir": proj_dir}


def _meta_path(active):
    return os.path.join(active["proj_dir"], "meta.json")


def load_meta(active):
    return json.load(open(_meta_path(active), encoding="utf-8"))


def save_meta(active, meta):
    json.dump(meta, open(_meta_path(active), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
