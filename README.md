# Rabatt-Finder

Private Website, die einmal pro Woche alle Angebote von **Corporate Benefits (Miele)**, **Student Beans** und
**UNiDAYS** ausliest und durchsuchbar macht: Suche, Filter, Übersicht je Kategorie, Top-Angebote,
Anbieter-Vergleich und Excel-Download. Erreichbar unter `/angebote/`, geschützt mit Benutzername und Passwort.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `scraper/scrape.py` | liest die drei Seiten mit Playwright (Chromium) aus und schreibt die Rohdaten nach `data/` |
| `angebote/parse.py` | vereinheitlicht die Rohdaten (Kategorien, Rabatt, Kanal, Schlagworte …) |
| `angebote/site.py` | schreibt `offers.json` für die Website inkl. „neu“/„entfallen“ gegenüber dem letzten Lauf |
| `angebote/excel.py` | erzeugt `Angebote_Uebersicht.xlsx` |
| `build.py` | `python build.py <rohdaten> <zielordner>` – baut Website-Daten und Excel |
| `web/` | die statische Website (`index.html`, `app.js`, `style.css`) |
| `deploy/` | Update-Skript, systemd-Timer, Caddy-Konfiguration für `/angebote/`, Vorlage für `.env` |

## Ablauf auf dem Server

Der Timer `rabatt-finder.timer` startet jeden Montag gegen 5 Uhr `deploy/update.sh`:

1. `scraper/scrape.py` liest alle drei Plattformen aus. Liefert eine Plattform deutlich weniger Angebote als beim
   letzten Mal (z. B. weil der Login abgelaufen ist), bleiben deren alte Daten erhalten und die Website zeigt einen
   Hinweis an.
2. Die Excel-Datei der Vorwoche wird nach `archiv/` kopiert (Aufbewahrung ca. 4 Monate).
3. `build.py` schreibt `offers.json`, `Angebote_Uebersicht.xlsx` und `status.json` nach `WEB_ROOT`.

Zugangsdaten stehen ausschließlich in `/opt/rabatt-finder/.env` (Vorlage: `deploy/env.example`, Rechte `600`).

## Nützliche Befehle (auf dem Server)

```bash
sudo systemctl start rabatt-finder.service      # Update sofort ausführen
journalctl -u rabatt-finder.service -n 100      # Protokoll des letzten Laufs
systemctl list-timers rabatt-finder.timer       # wann läuft das nächste Update?
cd /opt/rabatt-finder && sudo -u rabatt git pull # neue Version aus GitHub holen
```

## Lokal testen

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m scraper.scrape --out data --only sb,ud   # Corporate Benefits braucht CB_* Umgebungsvariablen
python build.py data web
python -m http.server 8765 --directory web          # dann http://127.0.0.1:8765/ öffnen
```
