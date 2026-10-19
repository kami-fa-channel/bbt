"""Aiuti condivisi dai test."""
import re
import sys
from pathlib import Path

import pytest
from pypdf import PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RADICE = Path(__file__).resolve().parent.parent


@pytest.fixture
def pdf_numerato(tmp_path):
    """Fabbrica di PDF A5 in cui ogni pagina porta il proprio numero, grande."""
    from reportlab.pdfgen import canvas

    def crea(n_pagine, nome="numerato.pdf"):
        percorso = tmp_path / nome
        w, h = 148 * 72 / 25.4, 210 * 72 / 25.4
        c = canvas.Canvas(str(percorso), pagesize=(w, h))
        for i in range(1, n_pagine + 1):
            c.setFont("Helvetica-Bold", 60)
            c.drawCentredString(w / 2, h / 2, str(i))
            c.showPage()
        c.save()
        return percorso
    return crea


@pytest.fixture
def pdf_bianco(tmp_path):
    """Fabbrica di PDF A5 con pagine vuote (veloce anche con centinaia di pagine)."""
    def crea(n_pagine, nome="bianco.pdf"):
        percorso = tmp_path / nome
        w = PdfWriter()
        for _ in range(n_pagine):
            w.add_blank_page(width=148 * 72 / 25.4, height=210 * 72 / 25.4)
        with open(percorso, "wb") as fh:
            w.write(fh)
        return percorso
    return crea


def numeri_sul_foglio(reader, indice):
    """Numeri di pagina grandi stampati sulla facciata `indice`: [(numero, 'sx'|'dx')]."""
    pagina = reader.pages[indice]
    meta = float(pagina.mediabox.width) / 2
    trovati = []

    def visita(testo, cm, tm, font_dict, font_size):
        t = testo.strip()
        if t.isdigit() and font_size and font_size > 20:
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            trovati.append((x, int(t)))
    pagina.extract_text(visitor_text=visita)
    return [(n, "sx" if x < meta else "dx") for x, n in sorted(trovati)]


def y_marche_di_collazione(reader):
    """Per ogni facciata che ha la marca di collazione: distanza dal bordo alto, in mm."""
    altezza = float(reader.pages[0].mediabox.height)
    out = []
    for i, pagina in enumerate(reader.pages):
        m = re.search(r"q 0\.15 g ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+) re f Q",
                      pagina.get_contents().get_data().decode("latin1"))
        if m:
            out.append((i, round((altezza - (float(m.group(2)) + float(m.group(4)))) * 25.4 / 72, 2)))
    return out
