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


def test_resolve_globs_matches_existing(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PRD.md").write_text("x", encoding="utf-8")
    assert ssot.resolve_globs(str(tmp_path), ["docs/*.md"]) == ["docs/PRD.md"]


def test_check_pointers_flags_broken_glob(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PRD.md").write_text("x", encoding="utf-8")
    findings = ssot.check_pointers(str(tmp_path), ["docs/PRD.md", "missing/*.md"])
    locs = [(f.severity, f.location) for f in findings]
    assert ("ERROR", "missing/*.md") in locs
    assert all(f.location != "docs/PRD.md" for f in findings)


def test_run_extractors_merges_stdout(tmp_path):
    # 머지 로직 검증은 플랫폼-독립적으로: .py 추출기 사용 (run_extractors가 sys.executable로 실행).
    # 실제 프로젝트-로컬 seam 은 .sh 지만, 머지 로직은 추출기 언어와 무관하므로
    # bash 가용성(특히 Windows의 WSL bash 핸들 버그)에 의존하지 않도록 .py 로 테스트한다.
    ext = tmp_path / "ext.py"
    ext.write_text('print("WARN\\tfoo.md:3\\thi")\n', encoding="utf-8")
    findings = ssot.run_extractors(str(tmp_path), ["foo.md"], [str(ext)])
    assert ssot.Finding("WARN", "foo.md:3", "hi") in findings


def test_format_report_groups_by_severity():
    out = ssot.format_report([
        ssot.Finding("ERROR", "a:1", "broken"),
        ssot.Finding("WARN", "b:2", "drift"),
    ])
    assert "🔴" in out and "broken" in out and "⚠️" in out and "drift" in out


def test_format_report_clean():
    assert "✅" in ssot.format_report([])
