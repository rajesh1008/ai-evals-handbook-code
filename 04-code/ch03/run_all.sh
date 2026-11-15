#!/usr/bin/env bash
# Chapter 3 Lab: builds the v0.5 trace store, runs every step, writes OUTPUT.txt
set -euo pipefail
cd "$(dirname "$0")"
{
  echo "### build_store.py"; python3 build_store.py
  echo; echo "### lab.py"; python3 lab.py
  echo; echo "### inject.py"; python3 inject.py
  echo; echo "### try_its.py"; python3 try_its.py
} | tee OUTPUT.txt
(cd ../truss && python3 -m pytest -q)
