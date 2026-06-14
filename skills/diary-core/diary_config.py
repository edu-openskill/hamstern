"""Shared config loader/migrator for hams diary skills (server + local).

Config: ~/.claude/hams-diary.json
{
  "activeServer": "<name|null>",
  "activeLocal":  "<name|null>",
  "profiles": {
    "<name>": {"type": "server", "repo": "...", "template": "...", "features": {...}},
    "<name>": {"type": "local",  "dir":  "...", "template": "...", "features": {...}}
  }
}
"""
import json
import os
import shutil

DEFAULT_PATH = os.path.expanduser("~/.claude/hams-diary.json")


def load(path=DEFAULT_PATH):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def migrate(cfg):
    """Return (cfg, changed). Idempotent: a second call returns changed=False."""
    changed = False
    # 1) flat schema {repo, template, ...} -> multi-profile
    if "profiles" not in cfg and ("repo" in cfg or "template" in cfg):
        cfg = {"profiles": {"default": cfg}}
        changed = True
    if not isinstance(cfg.get("profiles"), dict):
        cfg["profiles"] = {}
        changed = True
    # 2) old single 'active' -> 'activeServer'
    if "active" in cfg:
        cfg["activeServer"] = cfg.pop("active")
        changed = True
    # 3) backfill type=server on legacy profiles (all were repo-based)
    for prof in cfg["profiles"].values():
        if isinstance(prof, dict) and "type" not in prof:
            prof["type"] = "server"
            changed = True
    # 4) ensure typed active pointers exist
    if "activeServer" not in cfg:
        names = [n for n, p in cfg["profiles"].items()
                 if isinstance(p, dict) and p.get("type") == "server"]
        cfg["activeServer"] = names[0] if names else None
        changed = True
    if "activeLocal" not in cfg:
        names = [n for n, p in cfg["profiles"].items()
                 if isinstance(p, dict) and p.get("type") == "local"]
        cfg["activeLocal"] = names[0] if names else None
        changed = True
    return cfg, changed


def save(cfg, path=DEFAULT_PATH, backup=False):
    if backup and os.path.exists(path):
        shutil.copy(path, path + ".bak")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def active_name(cfg, skill_type):
    return cfg.get("activeServer") if skill_type == "server" else cfg.get("activeLocal")


def resolve(cfg, skill_type, override=None):
    """Return (name, profile) for skill_type. Raise ValueError on missing/mismatch."""
    name = override or active_name(cfg, skill_type)
    if not name:
        raise ValueError(f"no active {skill_type} profile; add one with config profile add")
    prof = cfg.get("profiles", {}).get(name)
    if prof is None:
        raise ValueError(f"profile '{name}' not found")
    if prof.get("type") != skill_type:
        raise ValueError(f"profile '{name}' is type '{prof.get('type')}', not '{skill_type}'")
    return name, prof


def set_active(cfg, name):
    """Point the type-appropriate active pointer at name. Raise if missing."""
    prof = cfg.get("profiles", {}).get(name)
    if prof is None:
        raise ValueError(f"profile '{name}' not found")
    if prof.get("type") == "local":
        cfg["activeLocal"] = name
    else:
        cfg["activeServer"] = name
    return cfg
