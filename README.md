# The AI Evals in Practice Handbook: companion code

Companion code for **The AI Evals in Practice Handbook: Measuring Agents Before They Cost You** (AI at Work series) by **Rajesh Ranjan Mahapatra**.

Repository: <https://github.com/rajesh1008/ai-evals-handbook-code>

Every chapter of the book has a lab here. The labs rebuild the numbers the chapters print from pinned fixtures and cached model replies, on a laptop, offline, without an API key. Every chapter folder also keeps its reference output, so you can compare a run with what the book prints. See [Reproduction status](#reproduction-status) for what reruns exactly and for the three chapters whose model step can only be replayed from its recorded output.

## Layout

| Path | Contents |
|---|---|
| `04-code/truss/` | `truss`, the small evaluation library the book grows chapter by chapter (sampling, rates, gates, judges, calibration, statistics, reports and more), with its tests in `04-code/truss/tests/` |
| `04-code/truss/fixtures/` | Seeded teaching stores (seed 2026 unless a chapter names another). `make_fixture.py` builds the shared pilot store |
| `04-code/chNN/` | One folder per chapter: `lab.py` and its helper scripts, a `README.md`, `run_all.sh`, and the reference output (`OUTPUT.txt` and/or `out/`) |
| `04-code/requirements.txt` | Pinned Python packages for every lab |

The folder names match the paths printed in the book, so a reference such as `04-code/ch24/lab.py` points at the same file here.

All companies, people, borrowers, traces and datasets in this repository are fictional and were created for teaching (the running examples follow Harbor Lending and its Compass assistant). Any resemblance to real organisations is coincidental.

## Requirements

- Python 3.11 or newer (developed and tested on Python 3.13).
- Linux or macOS; Windows should work under WSL.

## Setup

```bash
git clone https://github.com/rajesh1008/ai-evals-handbook-code.git
cd ai-evals-handbook-code
python3 -m venv .venv
source .venv/bin/activate
pip install -r 04-code/requirements.txt
python3 04-code/truss/fixtures/make_fixture.py   # build the shared fixtures once
```

## Running offline (no API key)

Run a chapter lab from its folder:

```bash
cd 04-code/ch02
./run_all.sh          # reruns the lab, its failure injection and try-it-yourself scripts
git diff --stat .     # no change to OUTPUT.txt means you reproduced the chapter
```

`run_all.sh` rewrites the chapter's reference output (`OUTPUT.txt`, or files under `out/`), so `git diff` shows straight away whether your run matches the book, and `git checkout -- .` puts the reference files back. Run chapters in order: some labs read stores that an earlier chapter builds (for example, Chapter 5 reads the trace store that Chapter 3's lab writes). Each chapter's `README.md` says which script is behind each section, listing and figure. Chapter 53 has no `OUTPUT.txt`; its `run_all.sh` runs the fixture, the lab, its tests and the try-it-yourself scripts and prints to the terminal.

Run the `truss` tests:

```bash
cd 04-code/truss
python3 -m pytest -q
```

Expect `261 passed, 5 skipped`: the five skipped modules check the book manuscript itself, which is not part of this repository.

Offline runs use fixtures, cached replies and clearly labelled SIMULATED stand-ins. No script calls a model on its own: a paid Anthropic call needs both an explicit `run` or `--live` argument and `ANTHROPIC_API_KEY` in your environment, and a cached real result is reported, never overwritten, unless you pass that argument.

## Reproduction status

Checked on 15 November 2026 by running every chapter's `run_all.sh` in order (Chapters 1 to 53) from a fresh clone, with no API key set. Every `run_all.sh` exits 0.

- **Matches the reference output exactly:** Chapters 1, 5, 6, 10, 11, 23, 29, 31, 32 and 34 to 51. Chapter 53 has no `OUTPUT.txt`; its `run_all.sh` completes. Chapter 16's `run_all.sh` replays the cached run `ch16-full-new-2026-11-08-2131` and its `lab.py` output matches `new_run/ch16-full-new-2026-11-08-2131/reports/lab_NEW_stdout.txt` exactly; the folder's `OUTPUT.txt` is the legacy harness output and is not rewritten.
- **Matches apart from run stamps** (a date or timestamp, a timing, the absolute path of the folder, the `truss` version line, the test count of the full `truss` suite, or the printing order of a dictionary): Chapters 2, 3, 4, 7, 8, 9, 12, 17 to 22, 24 to 28, 30 and 33. Chapters 13 and 15 to 22 print to the terminal instead of rewriting `OUTPUT.txt`; compare with `diff`. In Chapter 3 the count of span writes refused under two concurrent writers in rollback mode also varies from run to run, since it depends on timing; the WAL line it is compared with does not.
- **Same values, different layout:** Chapter 52 prints the fixture digest, record digest, injection result and open targets that its `OUTPUT.txt` summarises, in a different layout.
- **Model step replayed from the recorded output only:** Chapters 13, 14 and 15. Their REAL model replies (Chapter 13's June extraction run and guideline probe, Chapter 14's pre-labeller and Try It 3 answers, Chapter 15's decision-step probe) could not be recovered and are not in this repository. Every SIMULATED part of these labs reruns and matches; each REAL step prints a `SKIP` line that points to the chapter's `OUTPUT.txt`, which holds the recorded run the book quotes. Chapter 14 writes such a run to `out/OUTPUT.offline.txt` and leaves `OUTPUT.txt` as it is. Chapter 13's `OUTPUT.txt` also predates the listing script (`listings.py`), whose output is printed but not recorded there. To rerun the model steps yourself, see [Running the model steps on a local model](04-code/LOCAL_MODEL.md) or pass `run` with your own key; neither will reproduce the book's numbers exactly.

The labs chain: run them in order, since later chapters read stores and files that earlier ones write (for example, Chapter 5 reads Chapter 3's trace store, Chapters 8 and 9 read Chapter 7's taxonomy, and Chapter 15 reads Chapter 13's gold records).

## Running a model step on a local model

The model steps of Chapters 5, 13, 14 and 15 can call any OpenAI-compatible server instead of the Anthropic API (Ollama, llama.cpp's `llama-server`, vLLM, LM Studio):

```bash
export LLM_BACKEND=local
export LOCAL_LLM_BASE_URL=http://localhost:11434/v1   # Ollama
export LOCAL_LLM_MODEL=qwen2.5:0.5b
cd 04-code/ch15 && ./run_all.sh run
```

Such runs are labelled `LOCAL-MODEL`, write only under the chapter's `out/local/` folder (ignored by git), and never touch the cached reference replies or `OUTPUT.txt`. A local model's numbers will differ from the book's. Details, and a mock-server test of the plumbing, are in [`04-code/LOCAL_MODEL.md`](04-code/LOCAL_MODEL.md).

## Live runs and PENDING results

Some scripts can call a real model, but only when you ask them to (for example `ch21/real_judge.py --live`, or a script's `run` argument). Those runs are optional and need your own key in the environment:

```bash
export ANTHROPIC_API_KEY=...   # in your own shell; never commit it
```

The book labels every number by where it came from: **Measured** (an observed result from a recorded experiment, such as a live model run whose replies are cached here), **SIMULATED** (seeded teaching data) or **[RESULT PENDING]** (a live experiment that has not been run yet, such as the cross-family judge batteries). This repository does not fill in PENDING results; several of the scripts behind them print the command to run once a provider client is wired. Never put an API key in this repository, a README or a committed environment file.

Live work the book marks PENDING includes (non-exhaustive) the Chapter 17 three-model bias battery, the Chapter 19 frozen-canary temperature-0 repeats, the Chapter 20 live confidence comparison, the Chapter 21 live shipped-prompt trial, the Chapter 22 cross-family cue check, the Chapter 26 and 27 cross-family vision and authority labels, the Chapter 42 thinking-budget bake-off and the Chapter 43 hosted-platform pilots. Where a live run was made (for example the Chapter 16 judge study), its raw replies are cached in that chapter's folder and the chapter README gives the model identifiers and run details.

## Chapter index

| Ch | Title | Code |
|---:|---|---|
| 1 | How Would You Know If It Weren't Good? | [`04-code/ch01/`](04-code/ch01/) |
| 2 | A First Honest Evaluation, End to End | [`04-code/ch02/`](04-code/ch02/) |
| 3 | Traces Worth Evaluating | [`04-code/ch03/`](04-code/ch03/) |
| 4 | The Test Pyramid for AI Systems | [`04-code/ch04/`](04-code/ch04/) |
| 5 | Error Analysis: Reading Traces Like a Scientist | [`04-code/ch05/`](04-code/ch05/) |
| 6 | The Living Taxonomy | [`04-code/ch06/`](04-code/ch06/) |
| 7 | Error Analysis Notebook: Fifty Traces, Annotated in Full | [`04-code/ch07/`](04-code/ch07/) |
| 8 | From Failure Modes to Metrics | [`04-code/ch08/`](04-code/ch08/) |
| 9 | Code-Based Checks: Format, Policy, Arithmetic, Citations | [`04-code/ch09/`](04-code/ch09/) |
| 10 | Reference-Based Metrics and Their Limits | [`04-code/ch10/`](04-code/ch10/) |
| 11 | Evaluating Extraction and Structured Outputs | [`04-code/ch11/`](04-code/ch11/) |
| 12 | Datasets: Golden, Synthetic and Alive | [`04-code/ch12/`](04-code/ch12/) |
| 13 | Building the Gold Set With the Customer's Experts | [`04-code/ch13/`](04-code/ch13/) |
| 14 | Annotation as an Operation | [`04-code/ch14/`](04-code/ch14/) |
| 15 | Workshop: The Metric Suite for the Hardship Flow | [`04-code/ch15/`](04-code/ch15/) |
| 16 | LLM-as-Judge, Done Properly | [`04-code/ch16/`](04-code/ch16/) |
| 17 | Judge Biases and How to Catch Them | [`04-code/ch17/`](04-code/ch17/) |
| 18 | Validating and Correcting Judge Estimates | [`04-code/ch18/`](04-code/ch18/) |
| 19 | Keeping Judges Honest | [`04-code/ch19/`](04-code/ch19/) |
| 20 | Confidence, Calibration and Routing, Evaluated | [`04-code/ch20/`](04-code/ch20/) |
| 21 | Workshop: A Judge Fails Its Trial | [`04-code/ch21/`](04-code/ch21/) |
| 22 | Judging the Judge's Explanations | [`04-code/ch22/`](04-code/ch22/) |
| 23 | Evaluating Retrieval and Grounding | [`04-code/ch23/`](04-code/ch23/) |
| 24 | Evaluating Agent Trajectories | [`04-code/ch24/`](04-code/ch24/) |
| 25 | Simulated Users and Multi-Turn Evaluation | [`04-code/ch25/`](04-code/ch25/) |
| 26 | Evaluating Documents, Images and Voice Inputs | [`04-code/ch26/`](04-code/ch26/) |
| 27 | Authority Compliance and Safety Behaviour | [`04-code/ch27/`](04-code/ch27/) |
| 28 | Evaluating the Human in the Loop | [`04-code/ch28/`](04-code/ch28/) |
| 29 | Evals That Survive Change | [`04-code/ch29/`](04-code/ch29/) |
| 30 | Evaluating Under a Model Gateway: Versions, Deprecations and Vendor Changes | [`04-code/ch30/`](04-code/ch30/) |
| 31 | Statistics You Can Defend | [`04-code/ch31/`](04-code/ch31/) |
| 32 | Variance, Repeats and the Noise Floor | [`04-code/ch32/`](04-code/ch32/) |
| 33 | Eval Data Governance: Privacy, Residency, Retention and Reproducibility | [`04-code/ch33/`](04-code/ch33/) |
| 34 | Evals in the Pull Request | [`04-code/ch34/`](04-code/ch34/) |
| 35 | From Offline Scores to Online Outcomes | [`04-code/ch35/`](04-code/ch35/) |
| 36 | Experiments on Live Traffic | [`04-code/ch36/`](04-code/ch36/) |
| 37 | Guardrails, Monitoring and Evals: One Family | [`04-code/ch37/`](04-code/ch37/) |
| 38 | Shadow Mode: Evaluating a Release on Live Traffic Without Serving It | [`04-code/ch38/`](04-code/ch38/) |
| 39 | Incident to Eval: The Post-Mortem Loop | [`04-code/ch39/`](04-code/ch39/) |
| 40 | The Weekly Report | [`04-code/ch40/`](04-code/ch40/) |
| 41 | The Cost of Knowing | [`04-code/ch41/`](04-code/ch41/) |
| 42 | Comparative Evals: Prompts, Routers and Small Models | [`04-code/ch42/`](04-code/ch42/) |
| 43 | The Tooling Matrix, Having Built Your Own | [`04-code/ch43/`](04-code/ch43/) |
| 44 | Evaluating Systems You Did Not Build | [`04-code/ch44/`](04-code/ch44/) |
| 45 | Evaluating for Compliance and Fairness | [`04-code/ch45/`](04-code/ch45/) |
| 46 | The Validation Pack for Model Risk | [`04-code/ch46/`](04-code/ch46/) |
| 47 | The Eval-First Company | [`04-code/ch47/`](04-code/ch47/) |
| 48 | The Evaluation Lead's Interview, From Both Sides | [`04-code/ch48/`](04-code/ch48/) |
| 49 | Operating the Practice for Twelve Months | [`04-code/ch49/`](04-code/ch49/) |
| 50 | Patterns and Anti-Patterns | [`04-code/ch50/`](04-code/ch50/) |
| 51 | End-to-End Case Studies | [`04-code/ch51/`](04-code/ch51/) |
| 52 | The Last Twenty Percent | [`04-code/ch52/`](04-code/ch52/) |
| 53 | Where This Is Going | [`04-code/ch53/`](04-code/ch53/) |

## Corrections

If a lab does not reproduce the number printed in the book, please open an issue with the chapter, the command you ran and the output you got.

## License

MIT, see [LICENSE](LICENSE). Copyright (c) 2026 Rajesh Ranjan Mahapatra.
