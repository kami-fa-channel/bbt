"""Divisione di un PDF in volumi, prima dell'imposizione.

I punti di taglio sono numeri di pagina del PDF originale: ciascuno e' l'ultima
pagina di un volume.  Con 240 su 352 pagine si ottengono 1-240 e 241-352; con
240 e 300, tre volumi.

A ogni volume si possono aggiungere le pagine per gli appunti: accanto a ogni
pagina del libro ne va una bianca, a quadretti o a righe, a sinistra o a destra.
Perche' le due restino affiancate a libro aperto (la prima pagina e' sempre a
destra) davanti a tutto va una pagina bianca.
"""

import io
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from .errori import ErroreLegatoria
from .imposizione import apri_pdf


def leggi_tagli(testo):
    """I numeri di un elenco scritto a mano (virgole, punti e virgola o spazi)."""
    pezzi = [p for p in re.split(r"[\s,;]+", testo or "") if p]
    try:
        return [int(p) for p in pezzi]
    except ValueError:
        sbagliato = next(p for p in pezzi if not p.isdigit())
        raise ErroreLegatoria(f"'{sbagliato}' non e' un numero di pagina.") from None


def intervalli(n_pagine, tagli):
    """[(prima, ultima), ...] dei volumi, con pagine contate da 1.

    I tagli devono essere crescenti e compresi fra 1 e n_pagine - 1."""
    precedente = 0
    for t in tagli:
        if t <= precedente:
            raise ErroreLegatoria(
                f"i punti di taglio devono essere tutti diversi e crescenti ({t} dopo {precedente})."
                if precedente else f"il punto di taglio {t} non e' una pagina valida.")
        if t >= n_pagine:
            raise ErroreLegatoria(f"il punto di taglio {t} e' oltre la penultima pagina "
                                  f"({n_pagine - 1}): il PDF ha {n_pagine} pagine.")
        precedente = t
    estremi = [0, *tagli, n_pagine]
    return [(a + 1, b) for a, b in zip(estremi, estremi[1:])]


def tagli_uguali(n_pagine, parti):
    """I tagli che dividono `n_pagine` in `parti` volumi il piu' possibile uguali."""
    if not 2 <= parti <= n_pagine:
        raise ErroreLegatoria(f"non si puo' dividere un PDF di {n_pagine} pagine in {parti} parti.")
    return [round(n_pagine * i / parti) for i in range(1, parti)]


LATI = ("sinistra", "destra")
TIPI = ("bianca", "quadretti", "righe")
PASSO_DEFAULT = {"quadretti": 5.0, "righe": 8.0, "bianca": 5.0}
MM = 72 / 25.4


@dataclass(frozen=True)
class Appunti:
    """Dove e come aggiungere le pagine per gli appunti (misure in mm).

    `passo` e' la distanza fra le righe o il lato dei quadretti, `spessore` lo spessore delle linee."""
    lato: str = "destra"
    tipo: str = "quadretti"
    passo: float = 5.0
    margine: float = 10.0
    spessore: float = 0.1

    def controlla(self):
        if self.lato not in LATI:
            raise ErroreLegatoria(f"il lato degli appunti deve essere {' o '.join(LATI)}.")
        if self.tipo not in TIPI:
            raise ErroreLegatoria(f"il tipo di pagina deve essere uno fra {', '.join(TIPI)}.")
        if self.tipo != "bianca" and self.passo < 1:
            raise ErroreLegatoria("il passo della griglia deve essere almeno 1 mm.")
        if self.tipo != "bianca" and not 0.01 <= self.spessore <= self.passo / 2:
            raise ErroreLegatoria("lo spessore delle linee deve essere almeno 0,01 mm "
                                  "e non piu' di meta' del passo.")
        if self.margine < 0:
            raise ErroreLegatoria("il margine degli appunti non puo' essere negativo.")


def percorsi_volumi(percorso, n_volumi, cartella=None, appunti=False):
    """nome_vol1.pdf, nome_vol2.pdf, ... accanto all'originale (o in `cartella`).

    Con gli appunti il nome finisce in _appunti, per non coprire i volumi senza;
    un solo volume si chiama nome_appunti.pdf."""
    p = Path(percorso)
    base = Path(cartella) if cartella else p.parent
    fine = "_appunti" if appunti else ""
    if n_volumi == 1:
        return [base / f"{p.stem}{fine}.pdf"]
    return [base / f"{p.stem}_vol{i}{fine}.pdf" for i in range(1, n_volumi + 1)]


def pagina_appunti(larghezza, altezza, appunti):
    """Una pagina per gli appunti (pypdf) grande `larghezza` x `altezza` punti."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(larghezza, altezza))
    m, passo = appunti.margine * MM, appunti.passo * MM
    util_l, util_a = larghezza - 2 * m, altezza - 2 * m
    if appunti.tipo != "bianca" and util_l > passo and util_a > passo:
        c.setStrokeGray(0.75)
        c.setLineWidth(appunti.spessore * MM)
        colonne, righe = int(util_l / passo), int(util_a / passo)
        x0, y0 = m + (util_l - colonne * passo) / 2, m + (util_a - righe * passo) / 2
        for j in range(righe + 1):
            c.line(x0, y0 + j * passo, x0 + colonne * passo, y0 + j * passo)
        if appunti.tipo == "quadretti":
            for i in range(colonne + 1):
                c.line(x0 + i * passo, y0, x0 + i * passo, y0 + righe * passo)
    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def _misure(pagina):
    """Larghezza e altezza della pagina come si vede (tiene conto di /Rotate)."""
    l, a = float(pagina.mediabox.width), float(pagina.mediabox.height)
    return (a, l) if (pagina.get("/Rotate") or 0) % 180 else (l, a)


def aggiungi_appunti(w, appunti):
    """Mette una pagina per appunti accanto a ogni pagina di `w`, e una bianca all'inizio."""
    appunti.controlla()
    pagine = list(w.pages)
    prime = _misure(pagine[0])
    # un esemplare per misura: le pagine di un libro sono quasi sempre tutte uguali
    modelli = {}
    for i in reversed(range(len(pagine))):
        misura = tuple(round(x, 1) for x in _misure(pagine[i]))
        if misura not in modelli:
            modelli[misura] = pagina_appunti(*_misure(pagine[i]), appunti)
        w.insert_page(modelli[misura], i if appunti.lato == "sinistra" else i + 1)
    w.insert_page(pagina_appunti(*prime, Appunti(tipo="bianca")), 0)


def dividi(percorso, tagli, cartella=None, sovrascrivi=False, appunti=None):
    """Scrive un PDF per volume e ne restituisce i percorsi.

    Con `appunti` (un Appunti) ogni volume ha anche le pagine per gli appunti;
    senza punti di taglio si scrive un solo volume, che allora le deve avere."""
    if not tagli and appunti is None:
        raise ErroreLegatoria("non c'e' niente da fare: servono punti di taglio o gli appunti.")
    if appunti is not None:
        appunti.controlla()
    reader = apri_pdf(percorso)
    parti = intervalli(len(reader.pages), tagli)
    uscite = percorsi_volumi(percorso, len(parti), cartella, appunti is not None)
    if not sovrascrivi:
        esistenti = [u.name for u in uscite if u.exists()]
        if esistenti:
            raise ErroreLegatoria("esistono gia': " + ", ".join(esistenti)
                                  + " (usa l'opzione per sovrascrivere).")
    # pypdf avverte per ogni collegamento interno che punta a un altro volume e
    # viene scartato: e' quello che ci si aspetta, non serve ripeterlo
    log = logging.getLogger("pypdf")
    livello = log.level
    log.setLevel(logging.ERROR)
    try:
        for (prima, ultima), uscita in zip(parti, uscite):
            w = PdfWriter()
            w.append(reader, pages=(prima - 1, ultima))
            if appunti is not None:
                aggiungi_appunti(w, appunti)
            with open(uscita, "wb") as fh:
                w.write(fh)
    finally:
        log.setLevel(livello)
    return uscite
