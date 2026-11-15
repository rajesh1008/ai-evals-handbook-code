#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 fixture.py
python3 lab.py
python3 -m pytest -q test_ch53_local.py
python3 try_its.py
