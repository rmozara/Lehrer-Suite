#!/usr/bin/env bash
set -euo pipefail

software_dir="$(cd "$(dirname "$0")" && pwd)"
suite_dir="$(cd "$software_dir/.." && pwd)"
python_bin="$suite_dir/.venv/bin/python"

if [ "$#" -ge 1 ]; then
  work_dir="$1"
elif command -v zenity >/dev/null 2>&1; then
  work_dir="$(zenity --file-selection --directory \
    --title='Unterrichtsordner für SE-Collector auswählen')" || exit 0
else
  echo "Bitte den Unterrichtsordner angeben."
  read -r -p "Arbeitsordner: " work_dir
fi

if [ -z "${work_dir:-}" ]; then
  echo "Kein Arbeitsordner ausgewählt."
  exit 1
fi

mkdir -p "$work_dir"
work_dir="$(cd "$work_dir" && pwd)"
if [ "$work_dir" = "$software_dir" ]; then
  echo "Der Programmordner kann nicht als Unterrichtsordner verwendet werden."
  echo "Bitte einen separaten Klassen- oder Unterrichtsordner auswählen."
  exit 1
fi
export SE_COLLECTOR_WORKDIR="$work_dir"

cd "$software_dir"
if [ ! -x "$python_bin" ]; then
  echo "Gemeinsame Suite-Umgebung wird einmalig eingerichtet …"
  python3 -m venv "$suite_dir/.venv"
fi

if ! "$python_bin" -c \
  "import fastapi, uvicorn, jinja2, multipart, qrcode, cv2, psutil, pypdf" \
  >/dev/null 2>&1; then
  echo "Fehlende Programmbestandteile werden einmalig installiert …"
  "$python_bin" -m pip install --upgrade pip
  "$python_bin" -m pip install -r "$suite_dir/requirements.txt"
fi
exec "$python_bin" app.py
