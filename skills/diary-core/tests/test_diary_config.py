import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import diary_config as dc


def test_flat_to_multi():
    cfg, changed = dc.migrate({"repo": "u", "template": "tech"})
    assert changed
    assert cfg["profiles"]["default"]["repo"] == "u"
    assert cfg["profiles"]["default"]["type"] == "server"
    assert cfg["activeServer"] == "default"
    assert cfg["activeLocal"] is None


def test_active_rename_to_active_server():
    cfg, changed = dc.migrate({"active": "x", "profiles": {"x": {"type": "server", "repo": "u"}}})
    assert changed
    assert "active" not in cfg
    assert cfg["activeServer"] == "x"


def test_type_backfilled_as_server():
    cfg, _ = dc.migrate({"active": "d", "profiles": {"d": {"repo": "u"}}})
    assert cfg["profiles"]["d"]["type"] == "server"


def test_migrate_is_idempotent():
    once, _ = dc.migrate({"repo": "u", "template": "tech"})
    twice, changed = dc.migrate(json.loads(json.dumps(once)))
    assert changed is False
    assert twice == once


def test_resolve_returns_typed_profile():
    cfg, _ = dc.migrate({"activeServer": "s", "activeLocal": "l",
                         "profiles": {"s": {"type": "server", "repo": "u"},
                                      "l": {"type": "local", "dir": "/tmp/b"}}})
    name, prof = dc.resolve(cfg, "local")
    assert name == "l" and prof["dir"] == "/tmp/b"


def test_resolve_rejects_type_mismatch():
    cfg, _ = dc.migrate({"profiles": {"l": {"type": "local", "dir": "/tmp/b"}},
                         "activeLocal": "l"})
    try:
        dc.resolve(cfg, "server", override="l")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_set_active_routes_by_type():
    cfg = {"activeServer": "s", "activeLocal": None,
           "profiles": {"s": {"type": "server"}, "l": {"type": "local"}}}
    dc.set_active(cfg, "l")
    assert cfg["activeLocal"] == "l"
    assert cfg["activeServer"] == "s"


def test_save_load_roundtrip():
    cfg, _ = dc.migrate({"repo": "u", "template": "tech"})
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "hams-diary.json")
        dc.save(cfg, p)
        assert dc.load(p) == cfg


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
