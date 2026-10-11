#!/usr/bin/env bash
# Wöchentliches Update: Student Beans und UNiDAYS auslesen, danach die Website neu bauen.
# Corporate Benefits sperrt automatisches Auslesen und wird per Lesezeichen-Knopf eingespielt.
# Wird vom systemd-Timer rabatt-finder.timer aufgerufen (als Benutzer "rabatt").
set -uo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"
mkdir -p data

echo "== Auslesen (Student Beans, UNiDAYS)"
.venv/bin/python -m scraper.scrape --out data --only sb,ud
scrape_rc=$?

echo "== Website bauen"
deploy/publish.sh || exit 2

echo "== Fertig (Auslesen: Exit-Code $scrape_rc)"
exit "$scrape_rc"
