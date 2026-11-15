#!/usr/bin/env bash
# Chapter 8 Lab: the metric suite skeleton, the wrong-fee card and its dispute, the scale study,
# composites, the fee gate's first before/after tables, the verbosity injection and three try-its.
set -euo pipefail
cd "$(dirname "$0")"
{
  echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### alerts.py"; python3 alerts.py
  echo; echo "### try_its.py"; python3 try_its.py
  echo; echo "### judge_scale.py (real model run, 1 November 2026; analyses the cached calls)"; python3 judge_scale.py
} | tee OUTPUT.txt
(cd ../truss && python3 -m pytest -q)
