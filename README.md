# Rabatt-Finder

Private Website, die einmal pro Woche alle Angebote von **Corporate Benefits (Miele)**, **Student Beans** und
**UNiDAYS** ausliest und durchsuchbar macht: Suche, Filter, Übersicht je Kategorie, Top-Angebote,
Anbieter-Vergleich und Excel-Download. Erreichbar unter `/angebote/`, geschützt mit Benutzername und Passwort.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `scraper/scrape.py` | liest Student Beans und UNiDAYS mit Playwright (Chromium) aus und schreibt die Rohdaten nach `data/` |
| `web/bookmarklet.js` | Lesezeichen-Knopf: liest Corporate Benefits im eigenen Browser aus und übergibt die Daten an `upload.html` |
| `server/upload.py` | Empfangsstelle (`/angebote/api/cb-upload`): prüft die Corporate-Benefits-Daten und baut die Website neu |
| `angebote/parse.py` | vereinheitlicht die Rohdaten (Kategorien, Rabatt, Kanal, Schlagworte …) |
| `angebote/site.py` | schreibt `offers.json` für die Website inkl. „neu“/„entfallen“ gegenüber dem letzten Lauf |
| `angebote/excel.py` | erzeugt `Angebote_Uebersicht.xlsx` |
| `build.py` | `python build.py <rohdaten> <zielordner>` – baut Website-Daten und Excel |
| `web/` | die statische Website (`index.html`, `app.js`, `style.css`), `lesezeichen.html` (Einrichtung des Knopfs), `upload.html` |
| `deploy/` | `update.sh` (wöchentlich), `publish.sh` (Website bauen), systemd-Dateien, Caddy-Snippet, `.env`-Vorlage, `INSTALL.md` |

## Ablauf auf dem Server

- **Student Beans und UNiDAYS:** Der Timer `rabatt-finder.timer` startet jeden Montag gegen 5 Uhr `deploy/update.sh`.
  Liefert eine Plattform deutlich weniger Angebote als beim letzten Mal, bleiben deren alte Daten erhalten und die
  Website zeigt einen Hinweis an.
- **Corporate Benefits:** sperrt automatische Zugriffe auf die Angebotslisten. Die Daten kommen deshalb über den
  Lesezeichen-Knopf aus dem eigenen, eingeloggten Browser (Einrichtung: `/angebote/lesezeichen.html`). Der Knopf
  öffnet `upload.html`, das die Daten an `server/upload.py` schickt; die Website ist danach sofort aktuell.
- `deploy/publish.sh` baut in beiden Fällen `offers.json`, `Angebote_Uebersicht.xlsx` und `status.json` nach
  `WEB_ROOT` und archiviert die vorherige Excel-Datei in `archiv/`.

Installation: siehe [deploy/INSTALL.md](deploy/INSTALL.md).

## Nützliche Befehle (auf dem Server)

```bash
sudo systemctl start rabatt-finder.service      # Update sofort ausführen
journalctl -u rabatt-finder.service -n 100      # Protokoll des letzten Laufs
journalctl -u rabatt-finder-upload -n 50        # Protokoll der Empfangsstelle
systemctl list-timers rabatt-finder.timer       # wann läuft das nächste Update?
cd /opt/rabatt-finder && sudo -u rabatt git pull # neue Version aus GitHub holen
```

## Lokal testen

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m scraper.scrape --out data --only sb,ud
python build.py data web
python -m http.server 8765 --directory web          # dann http://127.0.0.1:8765/ öffnen
```
