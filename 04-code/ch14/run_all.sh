#!/usr/bin/env bash
# Chapter 14: rebuild every number in the chapter. The pre-labels and the Try It 3 answers are cached in out/;
# delete out/prelabel.jsonl or out/try3_ops10.jsonl to rerun the REAL model calls (needs ANTHROPIC_API_KEY).
# Offline by default: no model is called. Pass `run` (or --live) to call the Anthropic API for uncached rows (paid),
# or set LLM_BACKEND=local with LOCAL_LLM_BASE_URL and LOCAL_LLM_MODEL to use a local model (written to out/local/).
# OUTPUT.txt is rewritten only when the REAL caches are present (or on an explicit live run); otherwise this run
# goes to out/OUTPUT.offline.txt and the recorded OUTPUT.txt is left as the reference.
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/../truss:${PYTHONPATH:-}"
MODE="${1:-}"
if [[ "$MODE" == "run" || "$MODE" == "--live" ]]; then export LABS_LIVE=1; fi
mkdir -p out
OUTFILE=OUTPUT.txt
if [[ "${LLM_BACKEND:-}" == "local" ]]; then mkdir -p out/local; OUTFILE=out/local/OUTPUT.local.txt
elif [[ -z "${LABS_LIVE:-}" && ( ! -s out/prelabel.jsonl || ! -s out/try3_ops10.jsonl ) ]]; then OUTFILE=out/OUTPUT.offline.txt; fi
{
  echo "### fixture"; python3 fixture.py | head -3
  echo "### pre-labeller (REAL, cached)"; python3 prelabel.py
  echo "### lab"; python3 lab.py
  echo "### failure injection"; python3 inject.py
  echo "### try it"; python3 try_its.py
  echo "### annotation screen"; python3 -m pytest -q test_app.py 2>&1 | tail -1; rm -f out/labels.jsonl
  echo "### truss tests"; (cd ../truss && python3 -m pytest -q 2>&1 | tail -1)
} > "$OUTFILE" 2>&1
cat "$OUTFILE"
if [[ "$OUTFILE" != OUTPUT.txt ]]; then echo "(wrote $OUTFILE; the recorded reference run is OUTPUT.txt)"; fi
