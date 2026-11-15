#!/usr/bin/env bash
# Chapter 10 Lab: five reference metrics on the 200 labelled March fee traces, the candidate-style
# rewrite, partial credit by fact, the stale-reference injection and three try-its.
# Real model runs (1 November 2026) are cached in out/; to repeat them with ANTHROPIC_API_KEY set:
#   python3 replies.py run && python3 restyle.py run && python3 extract.py run
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH" TOKENIZERS_PARALLELISM=false
{
  echo "### replies.py (real model run, cached)"; python3 replies.py
  echo; echo "### restyle.py (real model run, cached)"; python3 restyle.py
  echo; echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### try_its.py"; python3 try_its.py
} 2>/dev/null | grep -v "^Loading weights" | tee OUTPUT.txt
(cd ../truss && python3 -m pytest -q)
