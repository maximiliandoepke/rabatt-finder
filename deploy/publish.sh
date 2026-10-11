#!/usr/bin/env bash
# Baut aus den Rohdaten in data/ die Website-Daten und die Excel-Datei und aktualisiert WEB_ROOT.
# Wird von update.sh (wöchentlich) und vom Upload-Dienst (Lesezeichen-Knopf) aufgerufen.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"
set -a
# shellcheck disable=SC1091
. ./.env
set +a
WEB_ROOT="${WEB_ROOT:-/var/www/angebote}"
ARCHIV="$APP_DIR/archiv"
mkdir -p "$WEB_ROOT" "$ARCHIV"

# Excel des vorherigen Stands archivieren (eine Datei pro Tag), alte Archive nach ca. 4 Monaten löschen
if [ -f "$WEB_ROOT/Angebote_Uebersicht.xlsx" ]; then
  cp "$WEB_ROOT/Angebote_Uebersicht.xlsx" "$ARCHIV/Angebote_$(date +%F).xlsx"
  find "$ARCHIV" -name 'Angebote_*.xlsx' -mtime +120 -delete
fi

.venv/bin/python build.py data "$WEB_ROOT"
cp web/index.html web/app.js web/style.css web/upload.html web/lesezeichen.html web/bookmarklet.js "$WEB_ROOT/"
if [ -f data/status.json ]; then cp data/status.json "$WEB_ROOT/status.json"; fi
