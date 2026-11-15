#!/usr/bin/env bash
# Chapter 11 Lab: per-field scoring of Compass's income-verification extraction on 200 hardship
# documents, the rounding-normaliser injection, generated account-lookup queries and three try-its.
# Real model runs (1 November 2026) are cached in out/; to repeat them with ANTHROPIC_API_KEY set:
#   python3 extract.py run haiku && python3 extract.py run sonnet && python3 sql_lab.py run && python3 try_its.py run
set -euo pipefail
cd "$(dirname "$0")"
{
  echo "### docs.py"; python3 docs.py
  echo; echo "### extract.py (real model runs, cached)"; python3 extract.py
  echo; echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### sql_lab.py (real model run, cached)"; python3 sql_lab.py
  echo; echo "### try_its.py (real model run, cached)"; python3 try_its.py
} 2>/dev/null | tee OUTPUT.txt
(cd ../truss && python3 -m pytest -q)
