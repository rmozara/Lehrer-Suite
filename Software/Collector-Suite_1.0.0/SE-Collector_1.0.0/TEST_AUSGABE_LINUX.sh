#!/usr/bin/env bash
set -euo pipefail
software_dir="$(cd "$(dirname "$0")" && pwd)"
suite_dir="$(cd "$software_dir/.." && pwd)"
python_bin="$suite_dir/.venv/bin/python"
cd "$software_dir"
if [ ! -x "$python_bin" ]; then
  echo "Die Python-Umgebung fehlt. Bitte SE-Collector zuerst einmal mit ./run_on_linux.sh starten."
  exit 1
fi
exec "$python_bin" test_ausgabe.py
