#!/usr/bin/env bash
set -u
cd "$(dirname "$0")" || exit 1

if command -v zenity >/dev/null 2>&1; then
  QUELLE="$(zenity --file-selection --directory --title='Bisherigen Collector-Suite-Ordner auswählen')" || exit 0
else
  echo "Bitte den bisherigen Collector-Suite-Ordner hierher ziehen oder seinen Pfad eingeben:"
  read -r QUELLE
fi

python3 upgrade_suite.py "$QUELLE" --apply
STATUS=$?
echo
read -r -p "Zum Schließen Eingabetaste drücken …"
exit "$STATUS"
