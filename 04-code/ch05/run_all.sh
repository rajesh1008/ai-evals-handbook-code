#!/usr/bin/env bash
# Chapter 5 Lab: reads 150 December traces, builds taxonomy v0.1; writes OUTPUT.txt
set -euo pipefail
cd "$(dirname "$0")"
# Offline by default (cached real replies in out/model/). Pass --live to call the Anthropic API (paid), or set
# LLM_BACKEND=local with LOCAL_LLM_BASE_URL and LOCAL_LLM_MODEL for a local model (written to out/local/).
LIVE="${1:-}"
OUTFILE=OUTPUT.txt
if [[ "${LLM_BACKEND:-}" == "local" ]]; then mkdir -p out/local; OUTFILE=out/local/OUTPUT.local.txt; fi
{
  echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### model_coding.py (cached real responses; --live re-calls the API)"; python3 model_coding.py $LIVE
  echo; echo "### try_its.py"; python3 try_its.py
} | tee "$OUTFILE"
(cd ../truss && python3 -m pytest -q)
