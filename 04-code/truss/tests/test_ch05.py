import math

from truss.coding import (OpenCode, Category, Index, axial, cohen_kappa, confusion, detect_prob,
                          detectable_rate, first_wrong_step, jaccard_search, last_new, note_problems,
                          precision_at_k, purity, saturation_curve, suggest_groups, codebook_markdown)


def test_note_lint_sends_back_category_names_and_keeps_observations():
    assert note_problems("wrong balance date") == ["too short to check", "names a category, not what happened"]
    assert note_problems("Said the $25 fee applied after ten days; the schedule says fifteen.") == []
    assert "more than one sentence" in note_problems("Quoted the fee. Then it offered a waiver for 2 months.")
    assert note_problems("anything", verdict="pass") == []


def test_index_finds_paraphrase_before_unrelated_note():
    notes = ["told the borrower the late fee starts after ten days",
             "said a late fee applies after 10 days instead of fifteen",
             "release sent to the wrong state title office"]
    idx = Index(notes, ids=["a", "b", "c"])
    assert idx.search(notes[0], k=1, exclude="a")[0][0] == "b"
    assert jaccard_search(notes, ["a", "b", "c"], notes[2], k=1, exclude="c")[0][0] in ("a", "b")
    assert precision_at_k({"a": ["b"], "c": ["a"]}, {"a": 1, "b": 1, "c": 2}) == 0.5


def test_suggest_groups_and_purity():
    idx = Index(["fee after ten days", "fee after 10 days", "title office wrong state"], ids=[1, 2, 3])
    groups = suggest_groups(idx, threshold=0.3)
    assert [1, 2] in [sorted(g) for g in groups] and [3] in groups
    assert purity(groups, {1: "F", 2: "F", 3: "L"}) == 1.0


def test_axial_never_forces_an_unassigned_code():
    codes = [OpenCode(1, "t1", "sample", "f", "fail", "x"), OpenCode(2, "t2", "sample", "f", "fail", "y"),
             OpenCode(3, "t3", "sample", "f", "pass")]
    cats, left = axial(codes, lambda c: "FM-01" if c.note == "x" else None,
                       [Category("FM-01", "x mode", ("f",), "def")])
    assert cats[0].members == ["t1"] and [c.trace_id for c in left] == ["t2"]
    assert "| FM-01 | x mode |" in codebook_markdown(cats, codes)


def test_saturation_and_detection_floor():
    codes = [OpenCode(i, f"t{i}", "sample", "f", "fail" if i in (2, 5, 9) else "pass",
                      category={2: "A", 5: "B", 9: "A"}.get(i, "")) for i in range(1, 11)]
    curve = saturation_curve(codes)
    assert curve[-1] == (10, 3, 2) and last_new(curve) == 5
    assert math.isclose(detectable_rate(40), 1 - 0.05 ** (1 / 40))
    assert math.isclose(detect_prob(detectable_rate(40), 40), 0.95)


def test_kappa_confusion_and_first_wrong_step():
    a, b = ["p", "p", "f", "f"], ["p", "p", "f", "f"]
    assert cohen_kappa(a, b) == 1.0
    assert round(cohen_kappa(["p", "f", "f", "f"], ["p", "p", "f", "f"]), 3) == 0.5
    assert confusion(["p", "f"], ["f", "f"]) == {("p", "f"): 1}
    spans = [{"kind": "user", "name": "", "seq": 0}, {"kind": "tool", "name": "get_fee_schedule", "seq": 1},
             {"kind": "assistant", "name": "", "seq": 2}]
    i, s = first_wrong_step(spans, lambda i, s, ss: s["kind"] == "tool")
    assert i == 1 and s["name"] == "get_fee_schedule"
    assert first_wrong_step(spans, lambda *x: False) == (None, None)
