#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "[run] .venv not found — creating"
  python3 -m venv .venv
fi

# Optional deps
if [ -f requirements.txt ]; then
  "$PY" -m pip install -r requirements.txt
fi

# Optional CP-SAT tuning
: "${CPSAT_PHASE2_MAX_TIME:=300}"
export CPSAT_PHASE2_MAX_TIME

echo "[run] Starting simulation with $PY"
"$PY" main.py
