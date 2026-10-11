"""Liest die Angebote von Corporate Benefits, Student Beans und UNiDAYS mit einem automatisch gesteuerten Browser aus.

Aufruf:  python -m scraper.scrape --out data [--only cb,sb,ud]
Corporate Benefits braucht die Umgebungsvariablen CB_URL, CB_EMAIL und CB_PASSWORD.

Je Plattform entsteht eine JSON-Datei im Ausgabeordner (gleiches Format wie die bisherigen Rohdaten).
Liefert eine Plattform deutlich weniger Angebote als beim letzten Lauf, bleibt die alte Datei erhalten.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

FILES = {"cb": "corporate_benefits_angebote.json", "sb": "studentbeans_angebote.json", "ud": "unidays_angebote.json"}
MIN_SHARE = 0.6  # neue Daten nur übernehmen, wenn mindestens 60 % der bisherigen Anzahl erreicht werden
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/141.0.0.0 Safari/537.36")

COOKIE_REJECT = ["Alle ablehnen", "Ablehnen", "Nur notwendige", "Nur erforderliche", "Nur notwendige Cookies",
                 "Notwendige Cookies akzeptieren", "Reject all", "Reject All", "Necessary only"]


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def dismiss_cookies(page):
    """Klickt – falls vorhanden – die datensparsamste Option im Cookie-Banner."""
    page.evaluate(
        """(labels) => {
          const els = [...document.querySelectorAll('button, a, [role=button]')];
          const hit = els.find(e => labels.includes((e.innerText || '').trim()));
          if (hit) hit.click();
          const ot = document.querySelector('#onetrust-reject-all-handler');
          if (ot) ot.click();
        }""",
        COOKIE_REJECT,
    )


def click_until_done(page, root_selector, button_text, item_selector, max_clicks=80, wait_ms=1200):
    """Klickt "Mehr laden", bis der Button verschwindet oder keine neuen Einträge mehr kommen."""
    clicks, same, prev = 0, 0, -1
    for _ in range(max_clicks):
        n = page.locator(item_selector).count()
        found = page.evaluate(
            """([root, text]) => {
              const b = [...document.querySelectorAll(root + ' button')].find(b => b.textContent.trim() === text);
              if (!b) return false;
              b.scrollIntoView({block: 'center'});
              b.click();
              return true;
            }""",
            [root_selector, button_text],
        )
        if not found:
            break
        if n == prev:
            same += 1
            if same > 5:
                break
        else:
            same, prev = 0, n
            clicks += 1
        page.wait_for_timeout(wait_ms)
    return clicks


# ---------------- Corporate Benefits ----------------
# Hauptkategorien (Stand 10/2026) – nur Rückfall, falls das Menü nicht gefunden wird
CB_FALLBACK_CATS = {"21": "Auto", "22": "Finanzen", "23": "Reisen", "35": "Mode", "36": "Freizeit", "1740": "Sport",
                    "42": "Tickets", "37": "Wohnen", "4428": "Food", "38": "Technik", "40": "Mobilfunk",
                    "5675": "Beauty & Gesundheit", "41": "Regionales"}

CB_CATS_JS = """
() => {
  const cats = {};
  document.querySelectorAll('a[href^="/overview/"]').forEach(a => {
    const h = a.getAttribute('href');
    const t = a.textContent.trim();
    if (!h.includes('#') && t.startsWith('Alle Angebote')) cats[h.split('/')[2]] = t.replace('Alle Angebote', '').trim();
  });
  return cats;
}
"""

# Liest die Angebote der aktuell geöffneten Kategorieseite aus (Zwischenüberschrift h2 = Unterkategorie)
CB_PARSE_JS = r"""
() => {
  const T = e => e ? e.textContent.replace(/\s+/g, ' ').trim() : '';
  let sub = '';
  const items = [];
  document.querySelectorAll('main h2, main .cbg3-list-item').forEach(el => {
    if (el.tagName === 'H2') { sub = T(el); return; }
    const a = el.querySelector('a[href*="/offer/"]');
    if (!a) return;
    items.push({id: (a.getAttribute('href').match(/offer\/(\d+)/) || [])[1], title: T(el.querySelector('h3')),
      copy: T(el.querySelector('.cbg3-list-item--copy')), disc: T(el.querySelector('.cbg3-list-item--discount')),
      info: T(el.querySelector('.cbg3-offerlistitem--infos')),
      rest: T(el.querySelector('.cbg3-offer-list-item--rest-days')), sub});
  });
  return items;
}
"""

CB_DIAG_JS = """
() => ({offerLinks: document.querySelectorAll('a[href*="/offer/"]').length,
        listItems: document.querySelectorAll('.cbg3-list-item').length,
        main: !!document.querySelector('main'), html: document.documentElement.outerHTML.length})
"""


def scrape_cb(ctx):
    base = os.environ.get("CB_URL", "").rstrip("/")
    email, password = os.environ.get("CB_EMAIL"), os.environ.get("CB_PASSWORD")
    if not (base and email and password):
        raise RuntimeError("CB_URL, CB_EMAIL oder CB_PASSWORD fehlt in der .env-Datei")
    page = ctx.new_page()
    page.goto(base + "/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    dismiss_cookies(page)
    if "/login" in page.url:
        log("Corporate Benefits: Anmeldung …")
        page.fill('input[name="loginData[email]"]', email)
        page.fill('input[name="loginData[password]"]', password)
        page.click("#cbg3-submit-login")
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        if "/login" in page.url:
            raise RuntimeError("Anmeldung bei Corporate Benefits fehlgeschlagen (Zugangsdaten prüfen oder "
                               "zusätzliche Bestätigung erforderlich)")
        log("Corporate Benefits: angemeldet")
    page.goto(base + "/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    dismiss_cookies(page)
    cats = page.evaluate(CB_CATS_JS) or CB_FALLBACK_CATS
    try:
        with urllib.request.urlopen("https://ipinfo.io/json", timeout=10) as r:
            j = json.load(r)
        geo = f"{j.get('country')} / {j.get('city')} / {j.get('org')}"
    except Exception:
        geo = "unbekannt"
    log(f"Corporate Benefits: {len(cats)} Kategorien, Server-Standort laut IP: {geo}")

    out, stats = {}, {}
    for cid, name in cats.items():
        # Seite richtig öffnen: die Angebotsliste wird per JavaScript nachgeladen
        url = f"{base}/overview/{cid}"
        resp = page.goto(url, wait_until="domcontentloaded", timeout=60000, referer=base + "/")
        if not page.url.split("?")[0].split("#")[0].endswith(f"/overview/{cid}"):
            chain, req = [], resp.request if resp else None
            while req:
                chain.append(req.url.split("?")[0])
                req = req.redirected_from
            stats[name] = f"umgeleitet auf {page.url.split('?')[0]} (Kette: {' <- '.join(chain)})"
            continue
        if "/login" in page.url:
            stats[name] = "Login verlangt"
            continue
        try:
            page.wait_for_selector("main .cbg3-list-item", timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(1500)  # nachlaufende Listen-Abschnitte abwarten
        items = page.evaluate(CB_PARSE_JS)
        if not items:
            stats[name] = f"0 – Diagnose {page.evaluate(CB_DIAG_JS)}"
            continue
        for it in items:
            o = out.setdefault(it["id"], {k: it[k] for k in ("id", "title", "copy", "disc", "info", "rest")}
                               | {"cats": [], "subs": []})
            if name not in o["cats"]:
                o["cats"].append(name)
            if it["sub"] and it["sub"] != "ANGEBOT DES MONATS" and it["sub"] not in o["subs"]:
                o["subs"].append(it["sub"])
        stats[name] = len(items)
    log(f"Corporate Benefits: {len(out)} Angebote, je Kategorie: {stats}")
    page.close()
    if not out:
        raise RuntimeError("keine Angebote gefunden (Diagnose siehe Protokoll)")
    return list(out.values())


# ---------------- Student Beans ----------------
SB_BASE = "https://www.studentbeans.com"


def scrape_sb(ctx):
    page = ctx.new_page()
    page.goto(SB_BASE + "/de", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    dismiss_cookies(page)
    cats = page.evaluate(
        """() => [...new Set([...document.querySelectorAll('a[href*="/student-discount/de/cats/"]')]
              .map(a => a.getAttribute('href').split('?')[0].split('/cats/')[1]))].filter(Boolean)"""
    )
    if not cats:
        raise RuntimeError("Student Beans: keine Kategorien gefunden")
    seen, offers = set(), []
    for c in cats:
        page.goto(f"{SB_BASE}/student-discount/de/cats/{c}", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        dismiss_cookies(page)
        clicks = click_until_done(page, "main, body", "Mehr Rabatte laden", 'main a[href*="/student-discount/de/"]')
        cards = page.evaluate(
            """() => [...document.querySelectorAll('main a[href*="/student-discount/de/"]')]
              .filter(a => !a.getAttribute('href').includes('/cats/'))
              .map(a => ({href: a.getAttribute('href').split('?')[0],
                          lines: a.innerText.split('\\n').map(s => s.trim()).filter(Boolean)}))"""
        )
        for card in cards:
            key = card["href"] + "|" + "|".join(card["lines"])
            if key not in seen:
                seen.add(key)
                offers.append({**card, "cat": c})
        log(f"Student Beans {c}: {len(cards)} Karten, {clicks}x nachgeladen")
    page.close()
    return offers


# ---------------- UNiDAYS ----------------
UD_BASE = "https://www.myunidays.com/DE/de-DE"


def scrape_ud(ctx):
    page = ctx.new_page()
    page.goto(UD_BASE, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    dismiss_cookies(page)
    slugs = page.evaluate(
        """() => [...new Set([...document.querySelectorAll('a[href*="/categories/"]')]
              .map(a => a.getAttribute('href').split('?')[0].split('/categories/')[1]))].filter(Boolean)"""
    )
    if not slugs:
        raise RuntimeError("UNiDAYS: keine Kategorien gefunden")
    texts = {}
    for s in slugs:
        page.goto(f"{UD_BASE}/categories/{s}", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        dismiss_cookies(page)
        clicks = click_until_done(page, "main", "Mehr ansehen", 'main a[href*="/partners/"]')
        texts[s] = page.evaluate("() => document.querySelector('main')?.innerText || ''")
        log(f"UNiDAYS {s}: {page.locator('main a[href*=\"/partners/\"]').count()} Links, {clicks}x nachgeladen")
    page.close()
    return texts


SCRAPERS = {"cb": scrape_cb, "sb": scrape_sb, "ud": scrape_ud}


def count(data):
    return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="cb,sb,ud")
    ap.add_argument("--headed", action="store_true", help="Browser sichtbar starten (zum Testen)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    status = {"lauf": datetime.now().isoformat(timespec="minutes"), "plattformen": {}, "warnungen": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        ctx = browser.new_context(locale="de-DE", user_agent=UA, viewport={"width": 1366, "height": 900})
        for key in args.only.split(","):
            target = out / FILES[key]
            t0 = time.time()
            try:
                data = SCRAPERS[key](ctx)
            except Exception as e:  # eine Plattform darf scheitern, ohne die anderen zu blockieren
                msg = f"{key}: {e}"
                log("FEHLER " + msg)
                status["warnungen"].append(msg)
                status["plattformen"][key] = {"ok": False}
                continue
            old_n = count(json.loads(target.read_text(encoding="utf-8"))) if target.exists() else 0
            new_n = count(data)
            if new_n == 0 or (old_n and new_n < old_n * MIN_SHARE):
                msg = f"{key}: nur {new_n} statt bisher {old_n} Einträge – alte Daten werden behalten"
                log("WARNUNG " + msg)
                status["warnungen"].append(msg)
                status["plattformen"][key] = {"ok": False, "anzahl": new_n}
                continue
            target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            status["plattformen"][key] = {"ok": True, "anzahl": new_n, "sekunden": round(time.time() - t0)}
        browser.close()
    (out / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Fertig: {status}")
    return 0 if not status["warnungen"] else 1


if __name__ == "__main__":
    sys.exit(main())
