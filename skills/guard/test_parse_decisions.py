import importlib.util, pathlib

_spec = importlib.util.spec_from_file_location(
    "pd", pathlib.Path(__file__).parent / "parse_decisions.py")
pd = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(pd)


def test_parses_standard_line():
    text = "## Architecture\n- use HEAD not branch (이유: 기본 브랜치 리다이렉트) <!-- session: s1 -->\n"
    assert pd.parse_decisions(text) == [
        {"n": 1, "category": "Architecture", "text": "use HEAD not branch",
         "reason": "기본 브랜치 리다이렉트", "session": "s1"}]


def test_tracks_categories_and_numbers():
    text = ("## Architecture\n- A (이유: x) <!-- session: s1 -->\n"
            "## Testing\n- B (이유: y) <!-- session: s2 -->\n")
    ds = pd.parse_decisions(text)
    assert [(d["n"], d["category"], d["text"]) for d in ds] == [
        (1, "Architecture", "A"), (2, "Testing", "B")]


def test_decision_text_with_parens_keeps_reason_separate():
    text = "## Architecture\n- L1/L2 model (L1 dev/L2 biz) (이유: 분배) <!-- session: s1 -->\n"
    d = pd.parse_decisions(text)[0]
    assert d["text"] == "L1/L2 model (L1 dev/L2 biz)"
    assert d["reason"] == "분배"


def test_no_reason_and_no_session():
    text = "## Other\n- bare decision\n"
    assert pd.parse_decisions(text) == [
        {"n": 1, "category": "Other", "text": "bare decision",
         "reason": None, "session": None}]


def test_empty_and_non_decision_lines_ignored():
    text = "# 프로젝트 결정사항\n\n_마지막 업데이트: x_\n\n## Architecture\n"
    assert pd.parse_decisions(text) == []


def test_reason_with_inner_parens():
    text = "## Other\n- d (이유: foo (bar) baz) <!-- session: s1 -->\n"
    d = pd.parse_decisions(text)[0]
    assert d["reason"] == "foo (bar) baz"
    assert d["text"] == "d"
