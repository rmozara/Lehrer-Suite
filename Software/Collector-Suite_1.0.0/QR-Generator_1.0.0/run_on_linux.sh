#!/usr/bin/env bash
set -euo pipefail
software_dir="$(cd "$(dirname "$0")" && pwd)"
suite_dir="$(cd "$software_dir/.." && pwd)"
python_bin="$suite_dir/.venv/bin/python"

work_dir="${QR_GENERATOR_WORKDIR:-${1:-}}"

cd "$software_dir"
if [ ! -x "$python_bin" ]; then
  echo "Gemeinsame Suite-Umgebung wird einmalig eingerichtet …"
  python3 -m venv "$suite_dir/.venv"
fi
if ! "$python_bin" -c "import fastapi,uvicorn,jinja2,multipart,qrcode,pypdf,psutil,cv2" >/dev/null 2>&1; then
  "$python_bin" -m pip install -r "$suite_dir/requirements.txt"
fi
while true; do
  if [ -z "$work_dir" ] && command -v zenity >/dev/null 2>&1; then
    work_dir="$(zenity --file-selection --directory --title='Persönlichen Arbeitsordner mit Namensliste.ods auswählen')" || exit 0
  fi
  if [ -z "$work_dir" ]; then
    echo "Bitte deinen persönlichen Arbeitsordner mit Namensliste.ods angeben."
    read -r -p "Ordner: " work_dir
  fi
  work_dir="$(cd "$work_dir" 2>/dev/null && pwd)" || {
    echo "Der gewählte Ordner wurde nicht gefunden: $work_dir"
    exit 1
  }
  if [ ! -f "$work_dir/Namensliste.ods" ]; then
    echo "Im gewählten Ordner fehlt Namensliste.ods: $work_dir"
    exit 1
  fi
  export QR_GENERATOR_WORKDIR="$work_dir"
  set +e
  "$python_bin" app.py
  app_status=$?
  set -e
  if [ "$app_status" -ne 23 ]; then
    exit "$app_status"
  fi
  work_dir=""
  unset QR_GENERATOR_WORKDIR
  export QR_GENERATOR_SWITCHED=1
done
