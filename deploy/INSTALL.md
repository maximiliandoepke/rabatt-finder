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

## 3. Zugangsdaten eintragen

```bash
cd /opt/rabatt-finder
sudo -u rabatt cp deploy/env.example .env
chmod 600 .env
nano .env
```

`CB_EMAIL` und `CB_PASSWORD` ausfüllen, speichern mit Strg+O, Enter, Strg+X.

## 4. Erster Lauf

```bash
cd /opt/rabatt-finder && sudo -u rabatt deploy/update.sh
```

Dauert ca. 10 Minuten. Am Ende steht `Fertig: {...}` mit der Anzahl je Plattform.

## 5. Caddy: Unterseite /angebote/ mit Passwort

Passwort-Hash erzeugen (Caddy fragt das Passwort zweimal ab):

```bash
caddy hash-password
```

Zugangsdatei anlegen – `freunde` ist der Benutzername, `HASH` durch die Ausgabe von oben ersetzen:

```bash
nano /etc/caddy/rabatt-finder.auth
```

Inhalt:

```
basicauth {
	freunde HASH
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

## 6. Wöchentliches Update einschalten

```bash
cp /opt/rabatt-finder/deploy/rabatt-finder.service /opt/rabatt-finder/deploy/rabatt-finder.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now rabatt-finder.timer
systemctl list-timers rabatt-finder.timer
```

## Später: neue Version holen

```bash
cd /opt/rabatt-finder && sudo -u rabatt git pull
```

Wenn sich `deploy/caddy-angebote.conf` oder die systemd-Dateien geändert haben, die Kopien in `/etc/caddy/` bzw.
`/etc/systemd/system/` erneuern.
