#!/usr/bin/env bash
# Chapter 12: reruns the lab from caches (no API key needed) and the Truss suite; writes OUTPUT.txt.
# To redo the real model runs: python3 synth.py run && python3 validate.py && python3 leak.py run
set -euo pipefail
cd "$(dirname "$0")"
{
  echo "### synth.py (cache summary)"; python3 synth.py
  echo; echo "### validate.py"; python3 validate.py
  echo; echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### try_its.py"; python3 try_its.py
  echo; echo "### truss tests"; (cd ../truss && python3 -m pytest -q 2>&1 | tail -2)
} 2>&1 | tee OUTPUT.txt
