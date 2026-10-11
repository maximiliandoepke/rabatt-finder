"""Liest die Rohdaten der drei Plattformen ein und vereinheitlicht sie."""
import json
import re
from pathlib import Path


CB, SB, UD = "Corporate Benefits (Miele)", "Student Beans", "UNiDAYS"

AUTO = "Auto & Mobilität"
REISE = "Reisen & Hotels"
MODE = "Mode & Accessoires"
BEAUTY = "Beauty & Gesundheit"
SPORT = "Sport & Outdoor"
TECH = "Elektronik & Technik"
TEL = "Mobilfunk, Internet & Energie"
MEDIEN = "Medien, Software & Abos"
WOHN = "Möbel & Wohnen"
HAUS = "Haushalt & Heimwerken"
FOOD = "Lebensmittel & Getränke"
TICKET = "Freizeit, Tickets & Events"
FIN = "Finanzen & Versicherungen"
BILD = "Bildung & Lernen"
FAM = "Familie, Kinder & Tiere"
GESCH = "Geschenke & Gutscheine"
REGIO = "Regional / vor Ort"
SONST = "Sonstiges"

# ---------- Suchbegriffe ----------
KW_CAT = {
    AUTO: "Auto, Fahrzeug, Mobilität",
    REISE: "Reise, Urlaub",
    MODE: "Mode, Kleidung, Bekleidung, Fashion",
    BEAUTY: "Beauty, Kosmetik, Pflege, Gesundheit",
    SPORT: "Sport, Fitness, Outdoor",
    TECH: "Technik, Elektronik, Elektro",
    TEL: "Tarif, Vertrag",
    MEDIEN: "Abo, Medien",
    WOHN: "Wohnen, Einrichtung, Möbel",
    HAUS: "Haushalt, Heimwerken",
    FOOD: "Essen, Lebensmittel, Getränke",
    TICKET: "Freizeit, Tickets, Event, Ausflug",
    FIN: "Finanzen, Geld",
    BILD: "Bildung, Lernen, Kurs",
    FAM: "Familie, Kinder",
    GESCH: "Geschenk, Gutschein",
    REGIO: "regional, vor Ort, lokal",
}
KW_SUB = [
    (r"Home Entertainment|HD Fernsehen", "Fernseher, TV, Heimkino, Soundbar, Beamer, Streaming"),
    (r"hotel|Hotels & Hostels", "Hotel, Übernachtung, Unterkunft, Kurzurlaub, Wellness"),
    (r"Ferienh", "Ferienwohnung, Ferienhaus, Unterkunft, Urlaub"),
    (r"Reiseportale|Spezialreise|Urlaub", "Pauschalreise, Hotel, Flug, Urlaub, Reise"),
    (r"Camping", "Camping, Glamping, Zelt, Wohnmobil"),
    (r"Kreuzfahrt", "Kreuzfahrt, Schiff, Fähre, Urlaub"),
    (r"Fluggesellschaften|Flüge", "Flug, Fliegen, Airline"),
    (r"Bahn|Züge|Reisebusse", "Bahn, Zug, Bus, Ticket"),
    (r"Taxis|Transport|Scooter", "Taxi, Fahrdienst, E-Scooter, Mobilität"),
    (r"Mietwagen", "Mietwagen, Autovermietung, Auto mieten"),
    (r"Reisegepäck|Taschen", "Koffer, Gepäck, Tasche, Rucksack"),
    (r"Computer|laptops|desktops", "Laptop, Notebook, PC, Computer, Monitor, Tablet"),
    (r"Smartphone|Handys|mobile|Mobilfunk", "Handy, Smartphone, iPhone, Tablet"),
    (r"tech-accessories|Zubehör Handys", "Zubehör, Kopfhörer, Ladegerät, Hülle"),
    (r"gaming", "Gaming, Konsole, Spiele, PC"),
    (r"home-appliances|Haushalt$", "Haushaltsgeräte, Staubsauger, Küche"),
    (r"^Möbel|Büro", "Möbel, Sofa, Couch, Tisch, Stuhl, Schrank"),
    (r"Bett / Bad", "Bett, Matratze, Bettwäsche, Bad, Handtuch"),
    (r"Licht|Leuchtmittel", "Lampe, Leuchte, LED, Beleuchtung"),
    (r"Garten", "Garten, Pflanzen, Grill, Gartenmöbel"),
    (r"Heimwerker|Bauen|Bodenbel|Fenster", "Werkzeug, Heimwerken, Baumarkt, Renovieren"),
    (r"Porzellan", "Geschirr, Besteck, Küche, Backen"),
    (r"Smart home", "Smart Home, Haustechnik"),
    (r"Heizl", "Heizung, Kamin, Ofen"),
    (r"Neuwagen|Leasing|Gebrauchtwagen|Auto Abo", "Auto, Neuwagen, PKW, Leasing, Autokauf"),
    (r"Elektroauto", "E-Auto, Elektroauto, Wallbox, Laden"),
    (r"Autoservice|Tanken|Motorrad", "Werkstatt, Autoteile, Reifen, Tanken"),
    (r"Fahrräder", "Fahrrad, E-Bike, Rad, Pedelec"),
    (r"Sportclubs|gym", "Fitnessstudio, Gym, Training"),
    (r"Sportbekleidung|sportswear|fitness-clothing", "Sportbekleidung, Laufschuhe, Trainingskleidung"),
    (r"Energieversorgung", "Strom, Gas, Ökostrom, Energie"),
    (r"DSL|Festnetz|Datentarif", "Internet, DSL, Glasfaser, WLAN"),
    (r"Kino|Pay-TV|Streaming|subscriptions|Unterhaltung", "Streaming, Kino, Serien, Filme, Musik, Fernsehen"),
    (r"Zeitungen|Bücher|books|Musik & B", "Bücher, Zeitung, Zeitschrift, E-Book, Hörbuch"),
    (r"Drucker", "Drucker, Tinte, Toner, Patronen"),
    (r"Foto & Video|Fotodruck", "Kamera, Foto, Fotobuch, Video"),
    (r"Software", "Software, Programm, Lizenz"),
    (r"Brillen|Optik", "Brille, Sonnenbrille, Kontaktlinsen, Optiker"),
    (r"Schuhe|shoes", "Schuhe, Sneaker, Stiefel"),
    (r"Uhren|Schmuck|accessories", "Uhr, Schmuck, Accessoires"),
    (r"Unterwäsche|lingerie", "Unterwäsche, Dessous, Socken"),
    (r"Kinder- & Babymode|Spielwaren", "Kinder, Baby, Spielzeug, Kinderwagen"),
    (r"Kaffee", "Kaffee, Tee, Espresso"),
    (r"Wein", "Wein, Sekt, Champagner"),
    (r"Restaurants|Lieferdienst|Essen", "Restaurant, Lieferdienst, Essen bestellen"),
    (r"Nahrungsergänzung|Sportnahrung|proteins", "Vitamine, Protein, Nahrungsergänzung"),
    (r"Freizeitparks", "Freizeitpark, Ausflug, Achterbahn"),
    (r"Musicals|Konzerte|Comedy|Theater|Shows|Sport Events|Familienshows|Festivals|Messen|Ausstellungen|Highlights",
     "Tickets, Event, Veranstaltung, Konzert, Show"),
    (r"Versicherung", "Versicherung"),
    (r"Kredite", "Kredit, Darlehen, Finanzierung"),
    (r"Kreditkarten|Festgeld|Robo|banking|Finanzen", "Bank, Konto, Kreditkarte, Geldanlage"),
    (r"Tier", "Hund, Katze, Tierfutter, Haustier"),
    (r"Haut|Make-up|make-up|Parf|skincare|fragrance|haircare|Haarpflege", "Kosmetik, Pflege, Parfum, Make-up, Haare"),
    (r"Medizin|health-wellbeing|Wohlbefinden", "Apotheke, Medikamente, Gesundheit, Wellness"),
    (r"Partnersuche", "Dating, Partnersuche"),
    (r"Bildung|Studieren|learning", "Kurs, Weiterbildung, Studium, Sprache"),
    (r"Geschenk|Blumen", "Geschenk, Gutschein, Blumen"),
]
TV_BRANDS = re.compile(r"^(Samsung|LG|Sony|Philips TV|Panasonic|TCL|Hisense|Loewe|Metz|Telefunken|Grundig|"
                       r"MediaMarkt|Saturn|Cyberport|notebooksbilliger|expert|Euronics|Sky|MagentaTV|waipu\.tv|Zattoo)\b",
                       re.I)


def keywords(cat, *subs, text=""):
    kws = [KW_CAT.get(cat, "")]
    for s in subs:
        for pat, kw in KW_SUB:
            if s and re.search(pat, s, re.I):
                kws.append(kw)
    if TV_BRANDS.search(text):
        kws.append("Fernseher, TV")
    seen, out = set(), []
    for k in ", ".join(k for k in kws if k).split(", "):
        if k and k.lower() not in seen:
            seen.add(k.lower())
            out.append(k)
    return ", ".join(out)


def max_pct(text):
    vals = [float(v.replace(",", ".")) for v in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", text or "")]
    vals = [v for v in vals if 0 < v <= 100]
    return max(vals) / 100 if vals else None


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def rabatt_art(text, pct):
    if pct is not None:
        return "Prozent"
    if re.search(r"\d+(?:[.,]\d+)?\s*(€|\$|£|Euro)|(€|\$|£)\s*\d", text or ""):
        return "Betrag"
    if re.search(r"gratis|kostenlos|0,00|free|Probe|Testzeitraum|\d+\s*(Tage|Monate)", text or "", re.I):
        return "Gratis / Test"
    return "Aktion / Sonstiges"


rows = []  # wird von load_offers() befüllt


def add(plattform, anbieter, angebot, kat, pct, unterkat, beschreibung, hinweis, schlagworte, kanal, link):
    rows.append({"Plattform": plattform, "Anbieter": anbieter, "Angebot": angebot, "Kategorie": kat,
                 "Max. Rabatt": pct, "Rabatt-Art": rabatt_art(angebot, pct), "Kanal": kanal,
                 "Unterkategorie": unterkat, "Beschreibung": beschreibung, "Hinweis": hinweis,
                 "Schlagworte": schlagworte, "Link": link})


def _parse_cb(src):
    """Corporate Benefits (Miele)."""
    CB_MAIN = {"Auto": AUTO, "Finanzen": FIN, "Reisen": REISE, "Mode": MODE, "Freizeit": TICKET, "Sport": SPORT,
               "Tickets": TICKET, "Wohnen": WOHN, "Food": FOOD, "Technik": TECH, "Mobilfunk": TEL,
               "Beauty & Gesundheit": BEAUTY, "Regionales": REGIO}
    CB_SUB = [
        (r"Partnersuche", SONST), (r"Bildung", BILD), (r"Kino|Musik & B|Zeitungen|^Software", MEDIEN),
        (r"Spielwaren|Tierbedarf|Tierversicherung", FAM), (r"Bike-Sharing", AUTO), (r"Blumen|Geschenk|Fotodruck", GESCH),
        (r"Outdoor- & Freizeitger", SPORT), (r"Heimwerker|^Haushalt$|Bauen|DIY", HAUS), (r"Energieversorgung", TEL),
        (r"Dienstleistungen", SONST),
    ]
    cb = json.loads((src / "corporate_benefits_angebote.json").read_text(encoding="utf-8"))
    for o in cb:
        title = clean(o["title"]).rstrip(" -").strip()
        anbieter, _, sub_title = title.partition(" - ")
        subs = [re.sub(r"\s*\(\d+\)$", "", s) for s in o["subs"] if s not in ("ANGEBOT DES MONATS",)]
        subs = [s for s in subs if s != "Angebot des Monats"] or subs
        main = next((c for c in o["cats"] if c != "Regionales"), o["cats"][0])
        sub = next((s for s in subs if not s.startswith(("Metropolregion", "Hauptstadtregion"))), subs[0] if subs else "")
        region = ", ".join(s for s in subs if s.startswith(("Metropolregion", "Hauptstadtregion")))
        cat = CB_MAIN.get(main, SONST)
        for pat, c in CB_SUB:
            if re.search(pat, sub):
                cat = c
                break
        disc = clean(o["disc"]).replace("Rabatt", "").strip()
        disc_txt = (disc.replace("<", "bis zu").replace(">", "über") + " Rabatt").strip() if disc else ""
        hin = []
        if "km" in o["info"]:
            hin.append("vor Ort")
        if region:
            hin.append(region)
        if o.get("rest"):
            hin.append("noch " + clean(o["rest"]).rstrip("!"))
        angebot = disc_txt + (f" – {sub_title}" if sub_title else "")
        desc = clean(o["copy"])
        kanal = "nur vor Ort" if cat == REGIO else ("online & vor Ort" if "km" in o["info"] else "online")
        add(CB, anbieter.strip(), angebot, cat, max_pct(o["disc"]), " / ".join(subs), desc, "; ".join(hin),
            keywords(cat, *subs, text=anbieter + " " + desc), kanal,
            f"https://miele.mitarbeiterangebote.de/offer/{o['id']}")


def _parse_sb(src):
    """Student Beans."""
    SB_CAT = {"essen-trinken": FOOD, "mode": MODE, "technik-handy": TECH, "gesundheit-beauty": BEAUTY,
              "unterhaltung": MEDIEN, "heim-versorgung": WOHN, "reisen": REISE, "bucher-magazine-zeitungen": MEDIEN,
              "geschenke-gerate": GESCH, "sport-outdoor": SPORT, "finanzen": FIN}
    BADGES = {"Nur auf", "Nur für Studierende", "Online", "Im Geschäft"}
    sb = json.loads((src / "studentbeans_angebote.json").read_text(encoding="utf-8"))
    seen = {}
    for o in sb:
        lines = [clean(l) for l in o["lines"]]
        endet = next((l for l in lines if l.startswith("Endet")), "")
        vorher = next((l[4:] for l in lines if l.startswith("War ")), "")
        fuer_alle = "Für jeden, der es benutzen kann" in lines
        rest = [l for l in lines if l not in BADGES and not l.startswith(("Endet", "War "))
                and l != "Für jeden, der es benutzen kann"]
        if len(rest) < 2:
            continue
        offer, brand, sbsub = rest[0], rest[1], (rest[-1] if len(rest) > 2 else "")
        key = (brand.lower(), offer.lower())
        if key in seen:
            continue
        cat = SB_CAT.get(o["cat"], SONST)
        if re.search(r"Studieren|Lernen", sbsub):
            cat = BILD
        hin = []
        if "Nur auf" in lines:
            hin.append("nur auf Student Beans")
        if "Im Geschäft" in lines:
            hin.append("im Geschäft")
        if "Nur für Studierende" in lines:
            hin.append("nur für Studierende")
        if fuer_alle:
            hin.append("für alle (ohne Studi-Nachweis)")
        if endet:
            hin.append(endet[0].lower() + endet[1:])
        if vorher:
            hin.append(f"vorher: {vorher}")
        seen[key] = True
        href = o["href"] if o["href"].startswith("http") else "https://www.studentbeans.com" + o["href"]
        add(SB, brand, offer, cat, max_pct(offer), sbsub, "", "; ".join(hin), keywords(cat, sbsub, text=brand),
            "vor Ort" if "Im Geschäft" in lines else "online", href)


def _parse_ud(src):
    """UNiDAYS inkl. Banner-Angebote."""
    UD_TOP = {"fashion": MODE, "technology": TECH, "beauty": BEAUTY, "food-drink": FOOD, "health-fitness": SPORT,
              "lifestyle": SONST, "sports-media": MEDIEN, "learning": BILD, "earning": SONST}
    UD_SUB = {"technology_subscriptions": MEDIEN, "lifestyle_lifestyle-travel-transport": REISE,
              "lifestyle_lifestyle-subscriptions": MEDIEN, "lifestyle_lifestyle-home-banking": WOHN,
              "lifestyle_lifestyle-books-stationery": MEDIEN, "health-fitness_health-fitness-proteins-supplement": BEAUTY}
    UD_LABEL = {"fashion": "Fashion", "fashion_womenswear": "Womenswear", "fashion_menswear": "Menswear",
                "fashion_shoes": "Schuhe", "fashion_sportswear": "Activewear", "fashion_lingerie-underwear": "Dessous & Underwear",
                "fashion_accessories": "Accessoires", "technology": "Technik", "technology_laptops-tablets": "Laptops & Tablets",
                "technology_tech-accessories": "Tech-Zubehör", "technology_mobile": "Handys",
                "technology_desktops": "Desktops", "technology_gaming": "Gaming", "technology_subscriptions": "Abos",
                "technology_home-appliances": "Haushaltsgeräte", "beauty": "Beauty", "beauty_make-up": "Make-up",
                "beauty_skincare": "Hautpflege", "beauty_haircare-tools": "Haarpflege", "beauty_health-wellbeing": "Gesundheit & Wohlbefinden",
                "beauty_fragrance": "Düfte", "food-drink": "Essen & Trinken", "health-fitness": "Health & Fitness",
                "health-fitness_health-fitness-gym-and-fitness-apps": "Gym & Fitness-Apps",
                "health-fitness_health-fitness-proteins-supplement": "Proteine & Supplements",
                "health-fitness_health-fitness-fitness-clothing": "Fitnesskleidung",
                "health-fitness_health-fitness-fitness-accessories": "Fitness-Zubehör",
                "health-fitness_health-fitness-workouts": "Workouts", "lifestyle": "Lifestyle",
                "lifestyle_lifestyle-travel-transport": "Reisen & Transport", "lifestyle_lifestyle-subscriptions": "Abos",
                "lifestyle_lifestyle-home-banking": "Zuhause & Banking", "lifestyle_lifestyle-books-stationery": "Bücher & Schreibwaren",
                "sports-media": "Sport & Medien", "learning": "Lernen", "earning": "Verdienen"}
    TIME_RE = re.compile(r"^\d+\s+(Tage?|Stunden?|Minuten?)$")
    ud_texts = json.loads((src / "unidays_angebote.json").read_text(encoding="utf-8"))
    squash = lambda s: re.sub(r"\s+", "", s).lower()  # noqa: E731
    ud = {}
    for slug, text in ud_texts.items():
        L = [clean(l) for l in text.split("\n") if clean(l)]
        i = 0
        while i < len(L) - 2:
            brand, offer = L[i + 1], L[i + 2]
            if squash(L[i]) == squash(f"{brand},{offer}"):
                info = set()
                if i > 0 and L[i - 1] == "Im Store":
                    info.add("im Geschäft")
                j = i + 3
                while j < len(L) and (TIME_RE.match(L[j]) or L[j] in ("Exklusiv", "Boosted")):
                    if L[j] == "Exklusiv":
                        info.add("exklusiv")
                    elif TIME_RE.match(L[j]):
                        info.add("noch " + L[j])
                    j += 1
                key = (brand.lower(), offer.lower())
                rec = ud.setdefault(key, {"brand": brand, "offer": offer, "slugs": [], "info": set()})
                if slug not in rec["slugs"]:
                    rec["slugs"].append(slug)
                rec["info"] |= info
                i = j
            else:
                i += 1

    # Banner oberhalb von "Top-Marken": Hero-Banner (Titel, Text, "Jetzt einlösen") und Markenkarten (Marke, Titel, Text)
    OFFERISH = re.compile(r"%|€|gratis|kostenlos|rabatt|extra|spar|free|bonus|\bab\s+\d|\d+\s*monat", re.I)
    BANNER_BRAND_ALIAS = {"gigamobil": "Vodafone"}
    BANNER_BRAND_IGNORE = {"papier"}
    brand_names = {}
    for rec in ud.values():
        brand_names.setdefault(rec["brand"].lower(), rec["brand"])
    brand_names.update({k: v for k, v in ((v.lower(), v) for v in BANNER_BRAND_ALIAS.values())})


    EMOJI = re.compile(r"[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]")


    def add_banner(slug, brand, title, desc):
        title, desc = clean(EMOJI.sub("", title)), clean(EMOJI.sub("", desc))
        key = (brand.lower(), title.lower())
        if any(k[0] == key[0] and squash(k[1]) == squash(title) for k in ud):
            return
        # Kategorie von bereits erfassten Angeboten derselben Marke übernehmen
        known = next((r["slugs"] for k, r in ud.items() if k[0] == key[0] and "Banner-Angebot" not in r["info"]), None)
        ud[key] = {"brand": brand, "offer": title, "slugs": list(known or [slug]), "info": {"Banner-Angebot"}, "desc": desc}


    for slug, text in ud_texts.items():
        L = [clean(l) for l in text.split("\n") if clean(l)]
        if "Top-Marken" not in L:
            continue
        seg = L[1:L.index("Top-Marken")]
        for i in range(len(seg) - 2):  # Markenkarten
            b, title, desc = seg[i], seg[i + 1], seg[i + 2]
            if b.lower() in brand_names and title.lower() not in brand_names and OFFERISH.search(title + " " + desc) \
                    and not desc.startswith("Option"):
                add_banner(slug, brand_names[b.lower()], title, desc)
        for i, l in enumerate(seg):  # Hero-Banner
            if l != "Jetzt einlösen" or i < 2:
                continue
            title, desc = seg[i - 2], seg[i - 1]
            text_l = f"{title} {desc}".lower()
            brand = next((v for k, v in BANNER_BRAND_ALIAS.items() if k in text_l), None) or next(
                (brand_names[b] for b in sorted(brand_names, key=len, reverse=True)
                 if len(b) >= 3 and b not in BANNER_BRAND_IGNORE
                 and re.search(r"(?<!\w)" + re.escape(b) + r"(?!\w)", text_l)), None)
            if brand and OFFERISH.search(text_l):
                add_banner(slug, brand, title, desc)

    for rec in ud.values():
        subs = [s for s in rec["slugs"] if "_" in s] or rec["slugs"]
        s0 = subs[0]
        cat = UD_SUB.get(s0) or UD_TOP.get(s0.split("_")[0], SONST)
        if s0 == "lifestyle_lifestyle-home-banking" and re.search(r"bank|konto|kredit|finanz|N26|bunq|trade", rec["brand"] + rec["offer"], re.I):
            cat = FIN
        labels = [UD_LABEL.get(s, s) for s in subs]
        info = sorted(rec["info"], key=lambda x: (not x.startswith("exkl"), x))
        add(UD, rec["brand"], rec["offer"], cat, max_pct(rec["offer"]), " / ".join(labels), rec.get("desc", ""),
            "; ".join(info),
            keywords(cat, *subs, *labels, text=rec["brand"]), "vor Ort" if "im Geschäft" in rec["info"] else "online",
            f"https://www.myunidays.com/DE/de-DE/categories/{s0}")


PLATTS = [CB, SB, UD]
PLAT_KURZ = {CB: "Corporate Benefits", SB: "Student Beans", UD: "UNiDAYS"}


def load_offers(src):
    """Liest die drei JSON-Rohdateien aus `src` und gibt die vereinheitlichten Angebote zurück."""
    src = Path(src)
    rows.clear()
    for fname, parser in (("corporate_benefits_angebote.json", _parse_cb), ("studentbeans_angebote.json", _parse_sb),
                          ("unidays_angebote.json", _parse_ud)):
        if (src / fname).exists():  # fehlt eine Plattform (z. B. erster Lauf), werden die anderen trotzdem gebaut
            parser(src)
    result = sorted(rows, key=lambda r: (PLATTS.index(r["Plattform"]), r["Kategorie"], r["Anbieter"].lower()))
    rows.clear()
    return result
