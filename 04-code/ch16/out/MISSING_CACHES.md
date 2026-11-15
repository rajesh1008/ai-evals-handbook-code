# Chapter 16 model caches — missing

Searched 2026-11-08 (Asia/Calcutta): `04-code/ch16/out/` and every archived copy of the
chapter's working files. **No genuine Anthropic jsonl caches from the original study were
found.** Do not invent cache files.

**Current status:** the chapter now reports a full new run, `ch16-full-new-2026-11-08-2131`,
whose caches are in `../new_run/ch16-full-new-2026-11-08-2131/out/`. See `../README.md`.
The notes below describe the original gap.

## Runnable re-cache (Anthropic)

Requires `ANTHROPIC_API_KEY` in the environment (never print or commit it).

```bash
cd 04-code/ch16
# Wire live=True through gen.py / judges.py / lab.py (llm.run(tag, jobs, live=True))
# so out/replies.jsonl, out/judge.jsonl, out/alt_replies.jsonl, out/spanish.jsonl are written.
python3 -c "import gen, judges; print('see lab.py / run_all.sh for live entrypoints')"
# Preferred once run_all supports --live:
#   python3 run_all.sh --live
# Then re-analyse offline:
#   python3 run_all.sh
```

Before the new run, figures and captions that cited "Real model run" /
"cached run" for judge, agent or reply text were held as **[RESULT PENDING]**.
SIMULATED fixture counts in `OUTPUT.txt` (1,640 traces, kind mix, strata) remain valid.

## Modest NEW study (2026-11-08 Asia/Calcutta)

A stratified **n=24** live Haiku run is in `out/modest_study/` (`ch16-modest-2026-11-08`).
It does **not** restore full `out/judge.jsonl` / `out/replies.jsonl` and must not replace historical n=200 / 2,480-call claims.
Full re-cache remains pending via `gen.py run` + `judges.py run` + `agent.py run`.
