#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
test -d .venv || python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
exec .venv/bin/python desktop.py
