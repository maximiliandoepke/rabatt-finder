#!/usr/bin/env bash
# Wöchentliches Update: Angebote auslesen, Website-Daten + Excel bauen, Website aktualisieren.
# Wird vom systemd-Timer rabatt-finder.timer aufgerufen (als Benutzer "rabatt").
set -uo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"
set -a
# shellcheck disable=SC1091
. ./.env
set +a
WEB_ROOT="${WEB_ROOT:-/var/www/angebote}"
ARCHIV="$APP_DIR/archiv"
mkdir -p data "$WEB_ROOT" "$ARCHIV"

echo "== Auslesen"
.venv/bin/python -m scraper.scrape --out data
scrape_rc=$?

echo "== Excel der Vorwoche archivieren"
if [ -f "$WEB_ROOT/Angebote_Uebersicht.xlsx" ]; then
  cp "$WEB_ROOT/Angebote_Uebersicht.xlsx" "$ARCHIV/Angebote_$(date +%F).xlsx"
  find "$ARCHIV" -name 'Angebote_*.xlsx' -mtime +120 -delete
fi

echo "== Website-Daten und Excel bauen"
.venv/bin/python build.py data "$WEB_ROOT" || exit 2
cp web/index.html web/app.js web/style.css "$WEB_ROOT/"
cp data/status.json "$WEB_ROOT/status.json"

echo "== Fertig (Auslesen: Exit-Code $scrape_rc)"
exit "$scrape_rc"
