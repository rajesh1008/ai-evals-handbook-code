#!/usr/bin/env bash
# Chapter 7 Lab: February's fifty, annotated; v0.3; census; injection; try-its; a fresh fifty. Writes OUTPUT.txt
set -euo pipefail
cd "$(dirname "$0")"
{
  echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### try_its.py"; python3 try_its.py
  echo; echo "### fresh.py"; python3 fresh.py
} | tee OUTPUT.txt
(cd ../truss && python3 -m pytest -q)
