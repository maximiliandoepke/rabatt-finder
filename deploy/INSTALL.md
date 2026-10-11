# Installation auf dem Server (Ubuntu 24.04, Caddy)

Alle Befehle als `root` im Server-Terminal ausführen. Jeder Schritt kann einzeln ausgeführt und geprüft werden.

## 1. Benutzer und Zugriff auf das GitHub-Repository

Der Rabatt-Finder läuft unter einem eigenen Benutzer `rabatt` ohne Login. Für das private Repository bekommt
dieser Benutzer einen eigenen, nur lesenden Schlüssel („Deploy Key“).

```bash
apt-get update && apt-get install -y git python3-venv
useradd --system --create-home --home-dir /var/lib/rabatt --shell /usr/sbin/nologin rabatt
sudo -u rabatt mkdir -p /var/lib/rabatt/.ssh
sudo -u rabatt ssh-keygen -t ed25519 -N "" -C "rabatt-finder-server" -f /var/lib/rabatt/.ssh/id_ed25519
cat /var/lib/rabatt/.ssh/id_ed25519.pub
```

Die ausgegebene Zeile (beginnt mit `ssh-ed25519`) auf GitHub eintragen:
Repository → Settings → Deploy keys → Add deploy key, Titel „Server“, **ohne** „Allow write access“.

## 2. Projekt holen und installieren

```bash
mkdir -p /opt/rabatt-finder /var/www/angebote
chown rabatt:rabatt /opt/rabatt-finder /var/www/angebote
sudo -u rabatt GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new" git clone git@github.com:maximiliandoepke/rabatt-finder.git /opt/rabatt-finder
cd /opt/rabatt-finder
sudo -u rabatt python3 -m venv .venv
sudo -u rabatt .venv/bin/pip install -r requirements.txt
.venv/bin/playwright install-deps chromium
sudo -u rabatt .venv/bin/playwright install chromium
```

## 3. Einstellungen

```bash
cd /opt/rabatt-finder && sudo -u rabatt cp deploy/env.example .env && chmod 600 .env
```

Zugangsdaten werden nicht benötigt (siehe Kommentar in der Datei).

## 4. Erster Lauf (Student Beans und UNiDAYS)

```bash
cd /opt/rabatt-finder && sudo -u rabatt deploy/update.sh
```

Dauert ca. 7 Minuten. Am Ende steht `Fertig: {...}` mit der Anzahl je Plattform.

## 5. Empfangsstelle für den Lesezeichen-Knopf

```bash
cp /opt/rabatt-finder/deploy/rabatt-finder-upload.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now rabatt-finder-upload.service
systemctl status rabatt-finder-upload.service --no-pager
```

## 6. Caddy: Unterseite /angebote/ mit Passwort

Passwort-Hash erzeugen (Caddy fragt das Passwort zweimal ab):

```bash
caddy hash-password
```

Zugangsdatei anlegen – `schnaps` ist der Benutzername, `HASH` durch die Ausgabe von oben ersetzen:

```bash
nano /etc/caddy/rabatt-finder.auth
```

Inhalt:

```
basicauth {
	schnaps HASH
}
```

Snippet übernehmen, Caddyfile sichern und die Zeile `import /etc/caddy/rabatt-finder.caddy` direkt unter
`encode gzip` einfügen:

```bash
cp /opt/rabatt-finder/deploy/caddy-angebote.conf /etc/caddy/rabatt-finder.caddy
cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.vor-angebote
nano /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && systemctl reload caddy
```

Zurück zum alten Stand, falls etwas nicht stimmt:

```bash
cp /etc/caddy/Caddyfile.vor-angebote /etc/caddy/Caddyfile && systemctl reload caddy
```

## 7. Wöchentliches Update einschalten

```bash
cp /opt/rabatt-finder/deploy/rabatt-finder.service /opt/rabatt-finder/deploy/rabatt-finder.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now rabatt-finder.timer
systemctl list-timers rabatt-finder.timer
```

## 8. Corporate Benefits einspielen

`https://srv2025840.hstgr.cloud/angebote/lesezeichen.html` öffnen, den Knopf in die Lesezeichenleiste ziehen und
der Anleitung auf der Seite folgen. Danach einmal pro Woche (oder bei Bedarf) auf Corporate Benefits den Knopf
klicken; die Website erinnert nach 14 Tagen.

## Später: neue Version holen

```bash
cd /opt/rabatt-finder && sudo -u rabatt git pull && sudo -u rabatt deploy/publish.sh && systemctl restart rabatt-finder-upload.service
```

Wenn sich `deploy/caddy-angebote.conf` oder die systemd-Dateien geändert haben, die Kopien in `/etc/caddy/` bzw.
`/etc/systemd/system/` erneuern.
