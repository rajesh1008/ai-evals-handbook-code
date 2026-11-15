# Chapter 8 Lab: From Failure Modes to Metrics

Truss v1 (package 0.11.0). Harbor Lending and Compass are fictional. The Lab builds its own March
2027 fixture (`march.py`) with Chapter 7's generator: 8,050 Compass conversations from Mon 1 to
Sun 14 March 2027 (t-092049 to t-100098), the same release as February, so FM-22 and FM-24 are
still live. Fee conversations carry extra planted facts (what the fee tool returned, whether
Compass deferred to a loan officer, reply length, fee-schedule terms mentioned).

**What is simulated, and said so in the chapter.** Apart from the real run in `judge_scale.py`, no model is called. Compass's replies
under Ryan's two candidate prompts (`rc-0322-1`, `rc-0326-2`) are stand-ins whose effects are stated
probabilities in `compass_sim.py`. The two readers of the scale study (the evaluation lead and Ben
Fletcher) are simulated from stated assumptions: miss and false-alarm rates for the binary
question, a polish effect, leniency and noise for the 1-to-5 scale, a preference for the longer
reply in pairwise. The scale study therefore demonstrates a mechanism; the published evidence
is in the chapter's Recent Research box. Fixture "truth" rates (for example the composite's
per-flow pass rates) are computed over planted causes, which a real team never sees.

Run everything: `./run_all.sh` (writes `OUTPUT.txt`, then runs the Truss tests; 52 pass).

| Step | File | What it shows |
|---|---|---|
| A | `lab.py`, `suite.py` | The registry: 21 metric cards for 19 active modes plus two outcome metrics, four signals, five refused proposals |
| B | `lab.py` | The wrong-fee card v1.0 on a 200-trace March fee draw (deferred counted as fail), the 38 non-passing traces by category, v1.1 after Victor's ruling |
| C | `lab.py`, `compass_sim.py` | The same 200 under binary, 1-to-5 and pairwise: agreement, cut-points, length preference |
| D | `lab.py` | The traffic-weighted Compass score, what moves it, and three scenarios |
| E | `lab.py`, `alerts.py` | Monitor alerts by exact binomial: quiet-period false alert and chance of catching a doubling at weekly 50/100/200 and census; alerts reset 26 March 2027 to a four-week pooled draw of 200 (cards v1.1) |
| F | `lab.py` | All metric cards written to `out/metric-cards.md` |
| G | `lab.py` | Fee replay set (70 frozen + 200 March): before/after tables and the fee gate for two candidates |
| H | `lab.py` | Hours and dollars at the ledger's rates |
| Injection | `inject.py` | Vendor "answer completeness" against MC-02, stratified by reply length; Truss's `length_bias` flag |
| Real run | `judge_scale.py` | claude-haiku-4-5-20251001 asked the MC-02 binary question and a 1-to-5 question, twice each, on 40 templated fee cases in a short and a long version (320 calls, 1 November 2026). `python3 judge_scale.py run` calls the API (needs ANTHROPIC_API_KEY) and caches `out/judge_raw.jsonl`; without `run` it analyses the cache |
| Try it | `try_its.py` | Defer-everything release; 1-to-5 readers without polish; make-or-break composite |

New Truss module: `truss/metrics.py` (`Card`, `Registry`, `measure`, `length_table`, `length_bias`,
`composite`, `move_needed`, `paired`, `before_after`, `weighted_kappa`, `to_markdown`); tests in
`../truss/tests/test_ch08.py`.

Real model output: `judge_scale.py` (above) is the only live model run in this chapter. Its replies
come from templates, not from Compass, and its fee values are illustrative.

Simulated, by design: Compass, its two release candidates and the human readers in `compass_sim.py`
are fixtures; there is no real Compass to replay. Pending (another provider): the same
`judge_scale.py` prompts on a non-Anthropic model, to see whether the length effect's direction
holds across model families (marked [RESULT PENDING] in the book).
