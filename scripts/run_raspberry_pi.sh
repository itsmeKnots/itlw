#!/usr/bin/env bash
# Start the workbench full-screen on the Pi display.
set -euo pipefail

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
python_bin="$project_dir/.venv/bin/python"

if [ ! -x "$python_bin" ]; then
    echo "Virtual environment not found. Run: bash scripts/install_raspberry_pi.sh" >&2
    exit 1
fi

cd "$project_dir"
export TRANSFORMER_FULLSCREEN=1
exec "$python_bin" main.py
