#!/bin/bash
# Chapter 16 lab. Replays the cached REAL run ch16-full-new-2026-11-08-2131 over the SIMULATED fixture.
# No API key is required unless you pass `run` to judges.py, gen.py or agent.py yourself.
# OUTPUT.txt in this folder is the legacy (historical) harness output and is not rewritten here; the
# reference for this replay is new_run/ch16-full-new-2026-11-08-2131/reports/lab_NEW_stdout.txt.
set -euo pipefail
cd "$(dirname "$0")"
export CH16_OUT="${CH16_OUT:-$PWD/new_run/ch16-full-new-2026-11-08-2131/out}"
REF=new_run/ch16-full-new-2026-11-08-2131/reports/lab_NEW_stdout.txt
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
echo "===== fixture ====="
python3 fixture.py
echo
echo "===== lab (CH16_OUT=${CH16_OUT#$PWD/}) ====="
python3 lab.py | tee "$TMP"
if cmp -s "$TMP" "$REF"; then echo "lab.py output matches $REF"; else echo "NOTE: lab.py output differs from $REF"; fi
echo
echo "===== inject ====="
python3 inject.py
echo
echo "===== try_its ====="
python3 try_its.py
