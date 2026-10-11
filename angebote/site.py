"""Schreibt die Daten für die Website (offers.json) inkl. Vergleich mit dem vorherigen Stand."""
import hashlib
import json
import re
from pathlib import Path

from .parse import PLAT_KURZ, PLATTS


def offer_id(row):
    key = f'{row["Plattform"]}|{row["Anbieter"].lower()}|{row["Angebot"].lower()}'
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def brand_key(name):
    s = name.lower()
    s = re.sub(r"[®™©’'`´]", "", s)
    s = re.sub(r"\b(geschenkgutscheine?|gutscheine?|gift ?cards?|online ?shop|deutschland|germany|international|"
               r"store|shop|de)\b", "", s)
    return re.sub(r"[^a-z0-9äöüß]+", "", s)


def write_site_data(rows, out, stand):
    out = Path(out)
    target = out / "offers.json"
    previous = {}
    if target.exists():
        old = json.loads(target.read_text(encoding="utf-8"))
        previous = {o["id"]: o for o in old.get("offers", [])}
        first_seen_old = {o["id"]: o.get("seit") for o in old.get("offers", [])}
    else:
        first_seen_old = {}

    # Plattformen, die im vorherigen Stand schon Angebote hatten – beim ersten Einspielen ist nichts „neu“
    known_platforms = {o["p"] for o in previous.values()}

    offers = []
    for row in rows:
        oid = offer_id(row)
        pct = row["Max. Rabatt"]
        platform = PLATTS.index(row["Plattform"])
        if oid in previous:
            seit = first_seen_old[oid]
        else:
            seit = stand if platform in known_platforms else None
        offers.append({
            "id": oid,
            "p": platform,
            "a": row["Anbieter"],
            "o": row["Angebot"],
            "k": row["Kategorie"],
            "r": round(pct * 100) if pct is not None else None,
            "ra": row["Rabatt-Art"],
            "ch": row["Kanal"],
            "u": row["Unterkategorie"],
            "d": row["Beschreibung"],
            "h": row["Hinweis"],
            "s": row["Schlagworte"],
            "l": row["Link"],
            "b": brand_key(row["Anbieter"]),
            # Datum, seit dem das Angebot in den Daten ist; leer, wenn es schon beim ersten Einspielen dabei war
            "seit": seit,
        })
    ids = {o["id"] for o in offers}
    removed = [{"p": o["p"], "a": o["a"], "o": o["o"]} for oid, o in previous.items() if oid not in ids]
    new_count = sum(1 for o in offers if o["seit"] == stand and o["id"] not in previous)

    data = {
        "stand": stand,
        "plattformen": [PLAT_KURZ[p] for p in PLATTS],
        "anzahl": [sum(o["p"] == i for o in offers) for i in range(len(PLATTS))],
        "neu": new_count,
        "entfallen": removed,
        "offers": offers,
    }
    target.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"angebote": len(offers), "neu": new_count, "entfallen": len(removed)}
