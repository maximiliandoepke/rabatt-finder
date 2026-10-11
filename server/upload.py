"""Empfangsstelle für die Corporate-Benefits-Daten aus dem Lesezeichen-Knopf.

Läuft als Dienst rabatt-finder-upload.service auf 127.0.0.1:8091 und ist nur über Caddy unter
/angebote/api/cb-upload erreichbar (hinter dem Passwortschutz der Website).
Prüft die Daten, speichert sie in data/ und baut die Website mit deploy/publish.sh neu.
"""
import json
import os
import subprocess
import threading
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA = APP_DIR / "data"
TARGET = DATA / "corporate_benefits_angebote.json"
STATUS = DATA / "status.json"
MAX_BYTES = 20 * 1024 * 1024
MIN_OFFERS = 200          # weniger Angebote deutet auf einen Fehler beim Auslesen hin
MIN_SHARE = 0.6           # und weniger als 60 % des bisherigen Bestands ebenfalls
REQUIRED = {"id", "title", "disc", "info", "cats", "subs"}
LOCK = threading.Lock()


def update_status(entry):
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {"plattformen": {}, "warnungen": []}
    status.setdefault("plattformen", {})["cb"] = entry
    status["warnungen"] = [w for w in status.get("warnungen", []) if not w.startswith("cb:")]
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/cb-upload":
            return self.reply(404, {"ok": False, "fehler": "Unbekannte Adresse"})
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BYTES:
            return self.reply(413, {"ok": False, "fehler": "Daten fehlen oder sind zu groß"})
        try:
            offers = json.loads(self.rfile.read(length)).get("offers")
        except (ValueError, AttributeError):
            return self.reply(400, {"ok": False, "fehler": "Ungültiges Format"})
        if not isinstance(offers, list) or not all(isinstance(o, dict) and REQUIRED <= o.keys() for o in offers):
            return self.reply(400, {"ok": False, "fehler": "Ungültiges Format"})

        old_n = len(json.loads(TARGET.read_text(encoding="utf-8"))) if TARGET.exists() else 0
        if len(offers) < MIN_OFFERS or (old_n and len(offers) < old_n * MIN_SHARE):
            return self.reply(422, {"ok": False, "fehler": f"Nur {len(offers)} Angebote erhalten (bisher {old_n}). "
                                    "Bitte auf Corporate Benefits eingeloggt sein und erneut versuchen."})

        with LOCK:
            DATA.mkdir(exist_ok=True)
            TARGET.write_text(json.dumps(offers, ensure_ascii=False), encoding="utf-8")
            update_status({"ok": True, "anzahl": len(offers), "stand": date.today().strftime("%d.%m.%Y"),
                           "quelle": "Lesezeichen", "zeit": datetime.now().isoformat(timespec="minutes")})
            run = subprocess.run([str(APP_DIR / "deploy" / "publish.sh")], cwd=APP_DIR, capture_output=True,
                                 text=True, timeout=600)
        if run.returncode != 0:
            print(run.stdout, run.stderr, flush=True)
            return self.reply(500, {"ok": False, "fehler": "Daten gespeichert, aber die Website konnte nicht neu "
                                    "gebaut werden (Details: journalctl -u rabatt-finder-upload)"})
        return self.reply(200, {"ok": True, "anzahl": len(offers), "vorher": old_n})

    def log_message(self, fmt, *args):  # nur ins Journal, ohne IP-Adressen
        print(f"[{datetime.now():%Y-%m-%d %H:%M}] {fmt % args}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("UPLOAD_PORT", "8091"))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
