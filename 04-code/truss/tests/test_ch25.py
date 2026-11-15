from truss.simuser import (
    goal_completed, turns_to_resolution, abandoned, pushback_rate,
    fidelity_table, perturbation_survive, aggregate_conversations, polite_mask_failure,
)
from truss import __version__

def test_version_at_least_028():
    parts = [int(x) for x in __version__.split(".")[:2]]
    assert parts[0] > 0 or parts[1] >= 28

def test_goal_and_turns():
    turns = [{"role": "user"}, {"role": "assistant", "goal_met": True, "outcome": "resolved"}]
    assert goal_completed(turns)
    assert turns_to_resolution(turns) == 2
    assert not abandoned(turns)

def test_abandon():
    turns = [{"role": "user", "abandoned": True, "outcome": "abandoned"}]
    assert abandoned(turns)

def test_pushback():
    turns = [{"role": "user", "pushback": True}, {"role": "user", "pushback": False}]
    r = pushback_rate(turns)
    assert r["n_pushback"] == 1 and abs(r["rate"] - 0.5) < 1e-9

def test_fidelity_and_perturbation():
    ft = fidelity_table({"goal_completion": 0.84}, {"goal_completion": 0.79})
    assert abs(ft["rows"][0]["gap"] - 0.05) < 1e-9
    p = perturbation_survive(True, False)
    assert p["regressed"] and not p["survived"]

def test_aggregate_and_polite():
    convs = [
        {"goal_completed": True, "abandoned": False, "turns_to_resolution": 4, "pushback_rate": 0.2},
        {"goal_completed": False, "abandoned": True, "turns_to_resolution": None, "pushback_rate": 0.0},
    ]
    a = aggregate_conversations(convs)
    assert a["n"] == 2 and a["n_completed"] == 1
    assert polite_mask_failure(0.01)
    assert not polite_mask_failure(0.2)

def test_fixture_touchpoints():
    import json
    from pathlib import Path
    fix = Path(__file__).resolve().parents[2] / "ch25" / "out" / "fixture.json"
    if not fix.exists():
        return  # allow unit tests before fixture build
    d = json.loads(fix.read_text())
    assert abs(d["sim_goal_completion"] - 0.84) < 0.015
    assert abs(d["real_goal_completion"] - 0.79) < 0.015
    assert d["n"] == 300
