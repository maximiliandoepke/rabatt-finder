"""Baut aus den Rohdaten die Website-Daten und die Excel-Datei.

Aufruf: python build.py <rohdaten-ordner> <ausgabe-ordner> [stand]
"""
import sys
from datetime import date
from pathlib import Path

from angebote.excel import build_excel
from angebote.parse import load_offers
from angebote.site import write_site_data

src, out = Path(sys.argv[1]), Path(sys.argv[2])
stand = sys.argv[3] if len(sys.argv) > 3 else date.today().strftime("%d.%m.%Y")
out.mkdir(parents=True, exist_ok=True)
rows = load_offers(src)
print(write_site_data(rows, out, stand))
print(build_excel(rows, str(out / "Angebote_Uebersicht.xlsx"), stand))
