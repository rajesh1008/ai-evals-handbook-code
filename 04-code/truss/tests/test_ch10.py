from truss.reference import (FactKey, RefSet, auc, exact_match, gate_cost, normalise, partial_credit,
                             recall_at_k, rouge_l, stale, supported_role, token_f1)


def test_normalise_and_exact_match():
    assert normalise("The $25 fee, stands.") == "the $25 fee stands"
    assert exact_match("The fee stands.", "the fee  stands") == 1.0
    assert exact_match("The fee stands.", "The fee does not stand.") == 0.0


def test_overlap_rewards_shared_words_not_meaning():
    ref = "The $25 late fee will be waived."
    assert rouge_l("The $25 late fee will not be waived.", ref) > rouge_l("We are removing that charge.", ref)
    assert abs(token_f1("fifty years", "50 years") - 0.5) < 1e-9


def test_auc_and_recall():
    assert auc([0.9, 0.8], [0.1]) == 1.0
    assert auc([0.5], [0.5]) == 0.5
    assert recall_at_k([0.1, 0.9, 0.2, 0.8], [1, 0, 0, 1], 2) == 1


def test_gate_cost_counts_right_replies_flagged():
    cut, caught, right_flagged = gate_cost([0.1, 0.2, 0.3, 0.9], [0, 1, 0, 1], 2)
    assert (cut, caught, right_flagged) == (0.9, 2, 2)


def test_supported_role():
    held = [(0.99, 15, 15, 5, 185), (0.99, 14, 15, 2, 185)]
    assert supported_role(held) == "order"                       # 14 of 15 on the second set
    assert supported_role(held[:1]) == "order"                   # one set is never enough to decide
    assert supported_role([(0.99, 15, 15, 5, 185), (0.98, 15, 15, 4, 185)]) == "decide"
    assert supported_role([(0.48, 6, 15, 120, 185)]) == "none"


def test_refset_staleness_and_partial_credit():
    r = RefSet("key", "Ryan", "2026", "fee-schedule-2024-01", {"stands": "Fee {fee} stands."})
    assert r.text("stands", fee="$25") == "Fee $25 stands."
    assert len(r.digest()) == 12
    why = stale(r, {"fee-schedule-2026-03"}, ("stands", "officer_tool"))
    assert len(why) == 2
    keys = [FactKey("status", True), FactKey("amount"), FactKey("loan", True), FactKey("grace")]
    share, crit, _ = partial_credit({"status": "stands", "amount": 25, "loan": "1234", "grace": 15},
                                    {"status": "waive", "amount": 25, "loan": "1234", "grace": 15}, keys)
    assert share == 0.75 and crit == ["status"]
