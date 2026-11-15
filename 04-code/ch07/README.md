# Chapter 7 Lab: Error Analysis Notebook

Truss v0.10. Harbor Lending and Compass are fictional. The Lab builds its own February 2027
fixture (`february.py`, seed 2026): 8,025 Compass conversations from Mon 1 to Sun 14 February
(t-084024 to t-092048), including the February tool-call wrapper's two planted faults. The
fifty annotated entries live in `notebook_data.py`; the lab checks each one against the planted
facts and refuses to run if an entry contradicts the trace. Readers and their disagreements are
simulated and said so. Nothing here reads earlier chapters' stores.

Run everything: `./run_all.sh` (writes `OUTPUT.txt`, then runs the Truss tests; 40 pass).

| Step | File | What it shows |
|---|---|---|
| A | `lab.py` | Frame (declared exclusions), frame audit, quota draw with risk weights, manifest; frame vs sample shares |
| B | `lab.py` | The fifty entries: first-pass note, open code, cluster, decision; saturation |
| C | `lab.py` | Agreement before adjudication (verdict and label kappa); six disagreements settled by kind |
| D | `lab.py` | The cluster rule on ten clusters; taxonomy v0.3 release, fitted coverage and new-mode rate under v0.2 |
| E | `lab.py` | Census of FM-22 and FM-24 over all two weeks; restatement of FM-20; hours by activity and person |
| Injection | `inject.py` | A frame query that keeps `status = 'completed'` drops tool errors; frame audit refuses; discovery odds |
| Try it | `try_its.py` | Sample size and discovery; a uniform fifty; second-reading failures only |
| Fresh | `fresh.py` | A new fifty (seed 2027) through the annotation CLI |

New Truss module: `truss/notebook.py` (`Entry`, `pps_quota`, `frame_audit`, `share_check`,
`saturation`, `agreement`, `adjudicate`, `cluster_decision`, `hours`, CLI); tests in
`../truss/tests/test_ch07.py`.

Outputs in `out/`: `lab.json` (every number the chapter prints), `notebook-feb.csv` and `.md`,
`taxonomy-v0.3.json` and `.md` (the next seed for Appendix C), the sample manifest, and the
fresh fifty.
