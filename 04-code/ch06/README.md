# Chapter 6 Lab: The Living Taxonomy

Truss v0.9. Harbor Lending and Compass are fictional. The Lab builds its own January 2027
fixture (`january.py`, seed 2026): 15,993 Compass conversations from Mon 4 to Sun 31 January,
with planted causes, the first coder's free-text note on each failing trace, and the evidence
an inclusion test reads. The coders and their confusions are simulated; `january.CODERS` says
exactly what is planted. Nothing here reads earlier chapters' stores.

Run everything: `./run_all.sh` (about two seconds; writes `OUTPUT.txt`, then runs the Truss tests).

| Step | File | What it shows |
|---|---|---|
| A | `lab.py` | Risk-weighted re-code sample (4 to 17 Jan) and holdout (18 to 31 Jan), with manifests |
| B | `lab.py` | January coded under v0.1, then the v0.1.1 patch that writes inclusion tests: 10 labels stop fitting |
| C | `lab.py` | Per-mode rates, pilot first pass against January, one-sided Fisher exact tests |
| D | `lab.py` | Note clusters inside FM-02 and FM-13; coder agreement (Cohen's kappa) under v0.1.1 |
| E, G | `lab.py`, `modes.py` | The v0.2 change set: two splits, one merge, two additions (one from an incident), one retirement; crosswalk |
| F | `lab.py` | The same traces under v0.2 (circular, reported only to show agreement) |
| H | `lab.py` | Holdout coverage, check coverage by mode and by failure, the FM-05 retirement bound |
| Injection | `inject.py` | Payoff quoted for the borrower's other loan, absorbed by FM-19; coverage with and without inclusion tests |
| Try it | `try_its.py` | Re-code sample size; keep FM-09 and FM-10 apart; the retirement bound |

New Truss module: `truss/taxonomy.py` (`Mode`, `Taxonomy` with add, split, merge, retire,
promote, reword, release, crosswalk, digest, validate; `coverage`, `new_mode_rate`, `wilson`,
`kappa`, `drift`, `clusters`, `zero_bound`, `clean_traces_to_retire`, `check_coverage`);
tests in `../truss/tests/test_ch06.py`.

Outputs in `out/`: `lab.json` (every number the chapter prints), `taxonomy-v0.2.json` and
`taxonomy-v0.2.md` (the seed for Appendix C), and the two sample manifests.
