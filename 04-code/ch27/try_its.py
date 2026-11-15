"""Try Its: drop forbidden plants; refusal citation; adversarial family rates."""
from __future__ import annotations
import json, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1] / "truss"
sys.path.insert(0, str(ROOT))
from truss.authority import aggregate_authority, forbidden_path_pass, adversarial_suite_summary

OUT = Path(__file__).parent / "out"
FIX = json.loads((OUT / "fixture.json").read_text())
LAB = json.loads((OUT / "lab.json").read_text())

# 1. Without forbidden_path plants, compliance rises
kept = [t for t in FIX["traces"] if t["kind"] != "forbidden_path"]
rows = [forbidden_path_pass(t["outcome_ok"], t["authority_ok"]) for t in kept]
# map authority from fixture
for r,t in zip(rows, kept):
    r["authority_ok"] = t["authority_ok"]
agg1 = aggregate_authority([{"authority_ok": t["authority_ok"], "forbidden_path_pass": t["outcome_ok"] and not t["authority_ok"]} for t in kept])

# 2. Over-refusals with weak citation
over = [t for t in FIX["traces"] if t["kind"]=="over_refuse"]
weak = sum(1 for t in over if not t["cited_policy"])

# 3. Adversarial by family
by = defaultdict(lambda: {"n":0,"caught":0})
for c in FIX["adversarial"]:
    by[c["family"]]["n"] += 1
    by[c["family"]]["caught"] += int(c["caught"])
fam = {k: {"n":v["n"], "catch_rate": v["caught"]/v["n"]} for k,v in by.items()}

out = {
    "try1_without_forbidden_plants": agg1,
    "try2_over_refuse_weak_citation": {"n_over": len(over), "n_weak_citation": weak},
    "try3_adversarial_families": fam,
    "baseline_compliance": LAB["authority"]["authority_compliance"],
}
(OUT / "try_its.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
