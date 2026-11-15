"""Failure injection: flaky judge blocks a correct release."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'truss'))
from truss.prgate import flake_rate, gate_ladder_decision

OUT=Path(__file__).parent/'out'

def main():
    lab=json.loads((OUT/'lab.json').read_text())
    fix=json.loads((OUT/'fixture.json').read_text())
    fr=flake_rate(fix['flake_repeats'])
    # Correct release: det+fast+slow would pass, but flake blocks
    ladder=gate_ladder_decision(
        deterministic_pass=True,
        fast_pass=True,
        slow_pass=True,
        flake_blocked=fr['quarantine'],
    )
    out={
        'simulated': True,
        'flake': fr,
        'ladder': ladder,
        'correct_release_blocked_by_flake': ladder['decision']=='BLOCK_FLAKE',
        'lesson': 'Quarantine flaky judges from the PR gate; do not block correct releases on noise.',
    }
    (OUT/'inject.json').write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
if __name__=='__main__':
    main()
