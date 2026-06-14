import json, os, importlib.util, pathlib

_spec = importlib.util.spec_from_file_location(
    "ssot", pathlib.Path(__file__).parent / "ssot.py")
ssot = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ssot)


def _make_hamstern_data(tmp_path, uuid="u1"):
    data = tmp_path / "hamstern-data"
    proj = data / "projects" / uuid
    proj.mkdir(parents=True)
    (proj / "meta.json").write_text(json.dumps(
        {"uuid": uuid, "name": "t", "repos": [],
         "created_at": "x", "last_active": "x"}), encoding="utf-8")
    cfg_dir = tmp_path / ".config" / "hamstern"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "active-project.json").write_text(json.dumps(
        {"uuid": uuid, "name": "t",
         "hamstern_data_path": str(data), "linked_at": "x"}), encoding="utf-8")
    return tmp_path


def test_load_and_save_meta_roundtrip(tmp_path, monkeypatch):
    home = _make_hamstern_data(tmp_path)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    active = ssot.resolve_active_project()
    meta = ssot.load_meta(active)
    meta["ssot_paths"] = [".claude/rules/*.md"]
    ssot.save_meta(active, meta)
    assert ssot.load_meta(active)["ssot_paths"] == [".claude/rules/*.md"]
    assert ssot.load_meta(active)["uuid"] == "u1"
