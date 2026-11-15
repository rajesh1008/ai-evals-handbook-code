from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'truss'))
from truss.prgate import deterministic_checks, ci_cost, gate_ladder_decision

OUT=Path(__file__).parent/'out'

def main():
    lab=json.loads((OUT/'lab.json').read_text())
    d=deterministic_checks({'schema_ok':False,'pattern_ok':True,'status':'ok','similarity':0.9})
    cost=ci_cost(40, cost_per_case=0.01, repeats=3, judge_share=0.5)
    ladder=gate_ladder_decision(deterministic_pass=False, fast_pass=True, slow_pass=True, flake_blocked=False)
    out={'try1_schema_fail':d,'try2_cost':cost,'try3_ladder':ladder,'simulated':True}
    (OUT/'try_its.json').write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
if __name__=='__main__':
    main()
