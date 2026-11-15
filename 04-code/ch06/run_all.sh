#!/usr/bin/env bash
# Chapter 6 Lab: re-codes January under taxonomy v0.1, releases v0.2, measures it; writes OUTPUT.txt
set -euo pipefail
cd "$(dirname "$0")"
{
  echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### try_its.py"; python3 try_its.py
} | tee OUTPUT.txt
(cd ../truss && python3 -m pytest -q)
