#!/usr/bin/env bash
# Chapter 14: rebuild every number in the chapter. The pre-labels and the Try It 3 answers are cached in out/;
# delete out/prelabel.jsonl or out/try3_ops10.jsonl to rerun the REAL model calls (needs ANTHROPIC_API_KEY).
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/../truss:${PYTHONPATH:-}"
{
  echo "### fixture"; python3 fixture.py | head -3
  echo "### pre-labeller (REAL, cached)"; python3 prelabel.py
  echo "### lab"; python3 lab.py
  echo "### failure injection"; python3 inject.py
  echo "### try it"; python3 try_its.py
  echo "### annotation screen"; python3 -m pytest -q test_app.py 2>&1 | tail -1; rm -f out/labels.jsonl
  echo "### truss tests"; (cd ../truss && python3 -m pytest -q 2>&1 | tail -1)
} > OUTPUT.txt 2>&1
cat OUTPUT.txt
