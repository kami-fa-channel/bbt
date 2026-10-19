"""
Tasselli per legatoria - un libro alla volta (motore, senza interfaccia).

Compone su UN SOLO foglio PDF i tasselli di un singolo volume:
  * tassello del piatto anteriore (orizzontale)
  * uno o due tasselli di dorso (verticali, testo ruotato)
  * un tassello supplementare facoltativo

Ogni tassello puo' contenere autore, titolo e una riga extra, con corpi
diversi (titolo grande, autore piccolo), definiti come ALTEZZA DELLE
MAIUSCOLE in millimetri.

Altre funzioni:
  * font di sistema (TrueType), tutte le misure in mm
  * angoli arrotondati, testo ruotato 0/90/180/270
  * bordi di ritaglio: contorno, tratteggio, crocini agli angoli, linee dei
    bordi prolungate fuori dal pezzo (per allinearlo alla lama di una
    taglierina), oppure su una seconda pagina registrata (per non dorare
    le guide)
  * modalita' solo nero con ingrossamento, per doratura da toner
  * pagina di prova facoltativa con corpi crescenti
  * posizionamento automatico oppure libero (i tasselli si trascinano
    con il mouse nell'anteprima)

Dipendenze:  pip install reportlab fonttools
L'interfaccia grafica sta in legatoria/gui/scheda_tasselli.py.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
from dataclasses import dataclass, asdict, field, fields, replace


try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:  # pragma: no cover
    raise ImportError("Manca reportlab.  Installa con:  pip install reportlab")

try:
    from fontTools.ttLib import TTFont as FTFont
    from fontTools.pens.boundsPen import BoundsPen
    HAVE_FONTTOOLS = True
except ImportError:
    HAVE_FONTTOOLS = False


APP_NAME = "Tasselli per legatoria - un libro"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".tasselli_legatoria")
# libreria delle cornici bitmap: la cartella "cornici" nella radice del progetto
# (accanto a bbt.py), dove estrai_cornice.py salva di default
CARTELLA_CORNICI = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cornici")
FONT_CACHE = os.path.join(CONFIG_DIR, "font_cache.json")
ULTIMO = os.path.join(CONFIG_DIR, "ultimo_libro.json")

PAGE_SIZES = {
    "A4 (210x297)": (210.0, 297.0),
    "A5 (148x210)": (148.0, 210.0),
    "A3 (297x420)": (297.0, 420.0),
    "Letter (215.9x279.4)": (215.9, 279.4),
    "Personalizzata": None,
}

BORDER_STYLES = [
    "nessuno",
    "contorno",
    "contorno tratteggiato",
    "crocini agli angoli",
    "contorno + crocini",
    "linee estese",
    "contorno + linee estese",
]

# composizioni disponibili: elenco di ruoli
COMPOSIZIONI = {
    "titolo": ["titolo"],
    "autore + titolo": ["autore", "titolo"],
    "titolo + autore": ["titolo", "autore"],
    "autore + titolo + extra": ["autore", "titolo", "extra"],
    "titolo + extra": ["titolo", "extra"],
    "autore": ["autore"],
    "extra": ["extra"],
    "vuoto (senza testo)": [],
}

VUOTO = "vuoto (senza testo)"

DECORI = [
    "nessuno",
    "filetto semplice",
    "doppio filetto",
    "filetto tratteggiato",
    "angoli incrociati",
    "cantonali (solo angoli)",
    "filetto con punti agli angoli",
    "fleuron agli angoli",
    "greca continua",
    "festone continuo",
    "dentelli continui",
    "cornice bitmap",
]

# Cornice composta con blocchetti bitmap (PNG) presi da file: quattro angoli,
# due tratti orizzontali e due verticali.  Il suffisso del file dice il ruolo:
# u/l = upper/lower, l/r = left/right, h = orizzontale, v = verticale.
DECORO_BITMAP = "cornice bitmap"
BITMAP_RUOLI = ("ul", "ur", "ll", "lr", "hu", "hl", "vl", "vr")
# modo a 16 blocchetti: per ogni lato, accanto al pezzo di mezzo (hu, hl, vl, vr),
# due tratti ripetuti, numerati in senso antiorario (come li numera estrai_cornice):
# hu: 1 a destra, 2 a sinistra; hl: 1 a sinistra, 2 a destra;
# vl: 1 in alto, 2 in basso; vr: 1 in basso, 2 in alto.
# Un lato e' a 16 se ci sono entrambi i suoi tratti; altrimenti "hu" & C. e' il
# tratto ripetuto (modo a 8, come prima).
BITMAP_RUOLI_EXTRA = ("hu1", "hu2", "hl1", "hl2", "vl1", "vl2", "vr1", "vr2")
BITMAP_RUOLI_TUTTI = BITMAP_RUOLI + BITMAP_RUOLI_EXTRA

# Stili di decoro che corrono lungo tutto il perimetro (non solo agli angoli),
# a moduli ripetuti: usati per scegliere quale funzione di geometria applicare.
DECORI_CONTINUI = ("greca continua", "festone continuo", "dentelli continui")

SPAZI = ["generale", "personalizzato", "ai bordi (massimo)"]

# Spessore minimo raccomandato perche' un tratto regga la doratura a caldo con
# foil: sotto questa soglia il foil rischia di non trasferirsi in modo continuo,
# specie su un tratto stampato con toner da ufficio invece che inciso su una
# fustella.  Le fonti del settore (fustelle e macchine calibrate) indicano
# 0,2 mm come minimo pratico; qui e' solo un avviso, non un limite imposto: chi
# dora a mano con toner puo' comunque scegliere di tentare uno spessore minore.
SPESSORE_DORATURA_MIN_MM = 0.2

RIF_VERTICALI = ["maiuscole", "ottico (tutto il testo)", "solo il titolo"]

ROTAZIONI = {    "0 (orizzontale)": 0,
    "90 (dal basso in alto)": 90,
    "270 (dall'alto in basso)": 270,
    "180 (capovolto)": 180,
}


# --------------------------------------------------------------------------
# Font di sistema
# --------------------------------------------------------------------------

@dataclass
class FontEntry:
    family: str
    style: str
    path: str
    index: int = 0

    @property
    def ext(self) -> str:
        return os.path.splitext(self.path)[1].lower()

    @property
    def supported(self) -> bool:
        # reportlab gestisce solo contorni TrueType: i .otf con contorni
        # PostScript/CFF non sono utilizzabili.
        return self.ext in (".ttf", ".ttc")


def font_dirs() -> list[str]:
    home = os.path.expanduser("~")
    s = platform.system()
    if s == "Windows":
        dirs = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")]
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(os.path.join(local, "Microsoft", "Windows", "Fonts"))
    elif s == "Darwin":
        dirs = ["/System/Library/Fonts", "/Library/Fonts",
                os.path.join(home, "Library", "Fonts")]
    else:
        dirs = ["/usr/share/fonts", "/usr/local/share/fonts",
                os.path.join(home, ".fonts"),
                os.path.join(home, ".local", "share", "fonts")]
    return [d for d in dirs if os.path.isdir(d)]


def _iter_font_files():
    seen = set()
    for d in font_dirs():
        for root, _dirs, files in os.walk(d):
            for fn in files:
                if os.path.splitext(fn)[1].lower() in (".ttf", ".ttc", ".otf", ".otc"):
                    p = os.path.join(root, fn)
                    rp = os.path.realpath(p)
                    if rp not in seen:
                        seen.add(rp)
                        yield p


def _names_from_file(path: str) -> list[tuple[str, str, int]]:
    if not HAVE_FONTTOOLS:
        return [(os.path.splitext(os.path.basename(path))[0], "Regular", 0)]
    n_fonts = 1
    try:
        with open(path, "rb") as fh:
            if fh.read(4) == b"ttcf":
                fh.seek(8)
                n_fonts = int.from_bytes(fh.read(4), "big")
    except OSError:
        return []
    out = []
    for i in range(min(n_fonts, 64)):
        try:
            f = FTFont(path, fontNumber=i, lazy=True)
            nm = f["name"]
            fam = nm.getDebugName(16) or nm.getDebugName(1) or ""
            sty = nm.getDebugName(17) or nm.getDebugName(2) or "Regular"
            f.close()
        except Exception:
            fam, sty = os.path.splitext(os.path.basename(path))[0], "Regular"
        if not fam:
            fam = os.path.splitext(os.path.basename(path))[0]
        out.append((fam.strip(), (sty or "Regular").strip(), i))
    return out


def _dirs_signature() -> str:
    h = hashlib.sha1()
    for p in sorted(_iter_font_files()):
        try:
            h.update(p.encode("utf-8", "replace"))
            h.update(str(int(os.path.getmtime(p))).encode())
        except OSError:
            pass
    return h.hexdigest()


def scan_fonts(use_cache: bool = True) -> list[FontEntry]:
    sig = _dirs_signature()
    if use_cache and os.path.isfile(FONT_CACHE):
        try:
            with open(FONT_CACHE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("sig") == sig:
                return [FontEntry(**e) for e in data["fonts"]]
        except Exception:
            pass
    fonts = []
    for path in _iter_font_files():
        for fam, sty, idx in _names_from_file(path):
            fonts.append(FontEntry(fam, sty, path, idx))
    fonts.sort(key=lambda e: (e.family.lower(), e.style.lower()))
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(FONT_CACHE, "w", encoding="utf-8") as fh:
            json.dump({"sig": sig, "fonts": [asdict(e) for e in fonts]}, fh)
    except OSError:
        pass
    return fonts


# --------------------------------------------------------------------------
# Metriche
# --------------------------------------------------------------------------

_registered: dict[tuple[str, int], str] = {}
_cap_cache: dict[tuple[str, int], float] = {}


def register_font(path: str, index: int = 0) -> str:
    key = (os.path.realpath(path), index)
    if key in _registered:
        return _registered[key]
    name = "TL%03d" % (len(_registered) + 1)
    pdfmetrics.registerFont(TTFont(name, path, subfontIndex=index))
    _registered[key] = name
    return name


def cap_ratio(path: str, index: int = 0) -> float:
    """Altezza delle maiuscole in frazione del corpo, misurata sulla 'H'."""
    key = (os.path.realpath(path), index)
    if key in _cap_cache:
        return _cap_cache[key]
    ratio = 0.0
    if HAVE_FONTTOOLS:
        try:
            f = FTFont(path, fontNumber=index, lazy=True)
            upm = f["head"].unitsPerEm or 1000
            cmap = f.getBestCmap()
            gs = f.getGlyphSet()
            for ch in "HEXO":
                gn = cmap.get(ord(ch))
                if gn and gn in gs:
                    pen = BoundsPen(gs)
                    gs[gn].draw(pen)
                    if pen.bounds:
                        ratio = pen.bounds[3] / upm
                        break
            if not ratio and "OS/2" in f:
                ratio = (getattr(f["OS/2"], "sCapHeight", 0) or 0) / upm
            f.close()
        except Exception:
            ratio = 0.0
    if not ratio:
        try:
            face = pdfmetrics.getFont(register_font(path, index)).face
            ratio = (getattr(face, "capHeight", 0) or 0) / 1000.0
        except Exception:
            ratio = 0.0
    if not 0.3 < ratio < 1.2:
        ratio = 0.70
    _cap_cache[key] = ratio
    return ratio


# --------------------------------------------------------------------------
# Modello
# --------------------------------------------------------------------------

def _numeri_come_float(oggetto):
    """I campi annotati `float` che contengono un intero diventano float.

    Serve alla finestra: sceglie il tipo di ogni campo (intero o decimale) dal valore di
    partenza, e con un intero (per esempio `larghezza_mm=95`) creava un campo intero,
    che tronca i decimali: una larghezza di 23,5 mm diventava 23.  Vale anche per i
    file salvati dalle versioni che avevano questo difetto, in cui i numeri sono interi.
    """
    for f in fields(oggetto):
        valore = getattr(oggetto, f.name)
        if f.type in ("float", float) and isinstance(valore, int) and not isinstance(valore, bool):
            setattr(oggetto, f.name, float(valore))


@dataclass
class Tassello:
    nome: str = "Tassello"
    attivo: bool = True
    larghezza_mm: float = 90.0
    altezza_mm: float = 30.0
    raggio_mm: float = 2.0
    margine_interno_mm: float = 4.0
    rotazione: int = 0
    composizione: str = "autore + titolo"
    scala: float = 1.0          # moltiplica i corpi definiti in Config
    spazio_modo: str = "generale"   # generale | personalizzato | ai bordi
    spazio_mm: float = 6.0          # usato se spazio_modo = personalizzato
    decoro: bool = True             # cornice stampata su questo tassello
    cornice_mm: float = 0.0         # base da incollare sotto: sporgenza per lato, in mm
    dx_mm: float = 0.0              # ritocco manuale del testo (+ = destra)
    dy_mm: float = 0.0              # ritocco manuale del testo (+ = in basso)
    copie: int = 1
    auto: bool = True           # posizione automatica sul foglio
    x_mm: float = 20.0          # da sinistra (se auto = falso)
    y_mm: float = 20.0          # dall'alto  (se auto = falso)
    # posizione di questo stesso tassello nelle serie ripetute 2, 3, 4:
    # stessa logica di auto/x_mm/y_mm ma indipendente per ogni serie, cosi'
    # spostare una serie non ne sposta un'altra.
    serie2_auto: bool = True
    serie2_x_mm: float = 20.0
    serie2_y_mm: float = 20.0
    serie3_auto: bool = True
    serie3_x_mm: float = 20.0
    serie3_y_mm: float = 20.0
    serie4_auto: bool = True
    serie4_x_mm: float = 20.0
    serie4_y_mm: float = 20.0

    def __post_init__(self):
        _numeri_come_float(self)


def tasselli_default() -> list[Tassello]:
    return [
        Tassello(nome="Piatto", attivo=True, larghezza_mm=95, altezza_mm=32,
                 rotazione=0, composizione="autore + titolo", scala=1.0),
        Tassello(nome="Dorso 1", attivo=True, larghezza_mm=24, altezza_mm=85,
                 rotazione=90, composizione="titolo", scala=0.75,
                 margine_interno_mm=3.0, y_mm=60),
        Tassello(nome="Dorso 2", attivo=True, larghezza_mm=24, altezza_mm=40,
                 rotazione=90, composizione="autore", scala=0.75,
                 margine_interno_mm=3.0, y_mm=160),
        Tassello(nome="Extra", attivo=False, larghezza_mm=60, altezza_mm=20,
                 rotazione=0, composizione="extra", scala=0.8, y_mm=220),
    ]


@dataclass
class Config:
    # contenuto
    autore: str = "Alessandro Manzoni"
    titolo: str = "I Promessi Sposi"
    extra: str = "VOL. I"

    # font
    font_path: str = ""
    font_index: int = 0
    font_label: str = ""
    # tagli per ruolo: vuoto = usa il font principale
    font_titolo_path: str = ""
    font_titolo_index: int = 0
    font_titolo_label: str = ""
    font_autore_path: str = ""
    font_autore_index: int = 0
    font_autore_label: str = ""
    font_extra_path: str = ""
    font_extra_index: int = 0
    font_extra_label: str = ""

    # corpi (altezza maiuscole in mm) e spaziature
    cap_titolo_mm: float = 5.0
    cap_autore_mm: float = 3.0
    cap_extra_mm: float = 3.0
    interlinea: float = 1.5        # multiplo dell'altezza maiuscole
    spazio_blocchi_mm: float = 3.0  # fra autore e titolo
    tracking_titolo_mm: float = 0.0
    tracking_autore_mm: float = 0.0
    maiusc_titolo: bool = False
    maiusc_autore: bool = False
    allineamento: str = "centro"
    centratura_ottica: bool = False
    rif_verticale: str = "maiuscole"
    adatta: bool = True

    # filetto fra i blocchi
    filetto: bool = False
    filetto_spessore_mm: float = 0.3
    filetto_larghezza_perc: float = 40.0

    # serie multiple sullo stesso foglio
    serie: int = 1
    serie_modo: str = "automatica"      # "automatica" | "manuale"
    serie_gap_mm: float = 8.0

    # foglio
    formato: str = "A4 (210x297)"
    pagina_w_mm: float = 210.0
    pagina_h_mm: float = 297.0
    orizzontale: bool = False
    margine_mm: float = 15.0
    gap_mm: float = 12.0

    # bordi di ritaglio
    bordo_stile: str = "contorno"
    bordo_spessore_mm: float = 0.10
    bordo_grigio: float = 0.55
    bordo_tratto_mm: float = 1.0
    crocini_offset_mm: float = 1.5
    crocini_lung_mm: float = 4.0
    bordo_pagina_separata: bool = False
    crocini_registro: bool = False
    # linee estese: i quattro bordi di ogni pezzo prolungati fuori dagli angoli
    linee_offset_mm: float = 0.5        # distanza dall'angolo a cui parte la linea
    linee_lung_mm: float = 10.0         # lunghezza della linea

    # cornice stampata (viene dorata insieme al testo)
    decoro_modello: str = "nessuno"
    decoro_rientro_mm: float = 2.5      # distanza dal bordo del tassello
    decoro_spessore_mm: float = 0.4     # filetto principale
    decoro_spessore2_mm: float = 0.15   # filetto secondario
    decoro_distanza_mm: float = 1.2     # fra i due filetti
    decoro_sporgenza_mm: float = 1.5    # oltre l'incrocio degli angoli
    decoro_angolo_mm: float = 7.0       # lunghezza dei cantonali
    decoro_punto_mm: float = 0.9        # diametro dei punti
    decoro_rispetta: bool = True        # il testo si scosta dalla cornice
    # fleuron agli angoli: un motivo di foglie e un ricciolo, radicato in ogni
    # angolo del tassello e rivolto verso l'interno
    decoro_fleuron_dim_mm: float = 11.0     # lunghezza delle due foglie d'angolo
    decoro_fleuron_ricciolo: bool = True    # aggiunge il piccolo ricciolo fra le foglie
    decoro_fleuron_centrale: bool = False   # aggiunge un motivo piu' piccolo a meta' dei due lati lunghi

    # bordi decorativi continui (greca, festone, dentelli): corrono lungo tutto
    # il perimetro del tassello, a moduli ripetuti
    decoro_continuo_rientro_mm: float = 2.0     # distanza dal bordo del tassello
    decoro_continuo_modulo_mm: float = 6.0      # lunghezza di un modulo (greca, dentelli)
    decoro_continuo_fascia_mm: float = 4.0      # larghezza della fascia (greca)
    decoro_continuo_raggio_mm: float = 3.5      # raggio dei semicerchi (festone)
    decoro_continuo_altezza_mm: float = 2.5     # altezza dei denti (dentelli)

    # cornice bitmap: blocchetti PNG usati cosi' come sono, solo affiancati
    decoro_bitmap_prefisso: str = ""    # percorso + nome comune, es. /cartella/cornice1_
    decoro_bitmap_dpi: float = 0.0      # risoluzione dei PNG; 0 = quella scritta nel file
    decoro_bitmap_riduci: bool = True   # se gli angoli non stanno, rimpicciolisce tutti i blocchetti
    decoro_bitmap_taglio: bool = True   # completa con porzioni di blocchetto invece di lasciare vuoti

    # doratura
    solo_nero: bool = True
    ingrosso_mm: float = 0.0

    # pagina di prova
    prova: bool = False
    prova_da_mm: float = 3.0
    prova_a_mm: float = 7.0
    prova_passo_mm: float = 0.5

    tasselli: list[Tassello] = field(default_factory=tasselli_default)

    def __post_init__(self):
        _numeri_come_float(self)

    def pagina_pt(self) -> tuple[float, float]:
        w, h = self.pagina_w_mm * mm, self.pagina_h_mm * mm
        return (h, w) if self.orizzontale else (w, h)


def config_da_dict(d: dict) -> Config:
    base = asdict(Config())
    ts = d.pop("tasselli", None)
    base.update({k: v for k, v in d.items() if k in base})
    cfg = Config(**base)
    if isinstance(ts, list) and ts:
        campi = {f.name for f in fields(Tassello)}
        cfg.tasselli = [Tassello(**{k: v for k, v in t.items() if k in campi})
                        for t in ts]
    return cfg


# --------------------------------------------------------------------------
# Composizione del testo
# --------------------------------------------------------------------------

def testo_ruolo(cfg: Config, ruolo: str) -> list[str]:
    grezzo = {"titolo": cfg.titolo, "autore": cfg.autore,
              "extra": cfg.extra}.get(ruolo, "")
    if ruolo == "titolo" and cfg.maiusc_titolo:
        grezzo = grezzo.upper()
    if ruolo == "autore" and cfg.maiusc_autore:
        grezzo = grezzo.upper()
    righe = [r.strip() for r in grezzo.replace("\r\n", "\n").split("\n")]
    return [r for r in righe if r]


def righe_tassello(cfg: Config, t: Tassello) -> list[tuple[str, str]]:
    """[(testo, ruolo), ...] secondo la composizione scelta."""
    out = []
    for ruolo in COMPOSIZIONI.get(t.composizione, ["titolo"]):
        for r in testo_ruolo(cfg, ruolo):
            out.append((r, ruolo))
    return out


def _cap_ruolo(cfg: Config, ruolo: str) -> float:
    return {"titolo": cfg.cap_titolo_mm, "autore": cfg.cap_autore_mm,
            "extra": cfg.cap_extra_mm}.get(ruolo, cfg.cap_titolo_mm)


def _track_ruolo(cfg: Config, ruolo: str) -> float:
    return {"titolo": cfg.tracking_titolo_mm,
            "autore": cfg.tracking_autore_mm}.get(ruolo, cfg.tracking_autore_mm)


def _larghezza(text, fontname, size, track):
    w = pdfmetrics.stringWidth(text, fontname, size)
    if track and len(text) > 1:
        w += track * (len(text) - 1)
    return w


class _Metriche:
    """Contorni reali dei glifi, per la centratura ottica."""

    def __init__(self, path, index=0):
        self.ok = False
        self._c = {}
        if not HAVE_FONTTOOLS:
            return
        try:
            self.f = FTFont(path, fontNumber=index, lazy=True)
            self.upm = self.f["head"].unitsPerEm or 1000
            self.cmap = self.f.getBestCmap()
            self.gs = self.f.getGlyphSet()
            self.hmtx = self.f["hmtx"]
            self.ok = True
        except Exception:
            self.ok = False

    def glifo(self, ch):
        """(xMin, yMin, xMax, yMax, avanzamento) in frazioni di em."""
        if ch in self._c:
            return self._c[ch]
        r = None
        try:
            gn = self.cmap.get(ord(ch))
            if gn and gn in self.gs:
                adv = self.hmtx[gn][0] / self.upm
                pen = BoundsPen(self.gs)
                self.gs[gn].draw(pen)
                if pen.bounds:
                    x0, y0, x1, y1 = (v / self.upm for v in pen.bounds)
                    r = (x0, y0, x1, y1, adv)
                else:                       # spazio o glifo vuoto
                    r = (0.0, 0.0, adv, 0.0, adv)
        except Exception:
            r = None
        self._c[ch] = r
        return r


_met_cache: dict[tuple[str, int], _Metriche] = {}


def metriche_font(path: str, index: int = 0) -> _Metriche | None:
    if not path or not os.path.isfile(path):
        return None
    key = (os.path.realpath(path), index)
    if key not in _met_cache:
        _met_cache[key] = _Metriche(path, index)
    return _met_cache[key]


def _ink_riga(met, testo: str, size: float):
    """(lsb, rsb, cima, fondo) dell'inchiostro della riga, in punti."""
    if not met or not met.ok or not testo:
        return 0.0, 0.0, None, None
    primo, ultimo = met.glifo(testo[0]), met.glifo(testo[-1])
    lsb = primo[0] * size if primo else 0.0
    rsb = (ultimo[4] - ultimo[2]) * size if ultimo else 0.0
    cime, fondi = [], []
    for ch in set(testo):
        g = met.glifo(ch)
        if g and (g[1] or g[3]):
            cime.append(g[3] * size)
            fondi.append(g[1] * size)
    return lsb, rsb, (max(cime) if cime else None), (min(fondi) if fondi else None)


RUOLI = ("titolo", "autore", "extra")


def font_ruolo(cfg: Config, ruolo: str):
    """(percorso, indice) del taglio scelto per il ruolo, o del font base."""
    p = getattr(cfg, "font_%s_path" % ruolo, "")
    if p and os.path.isfile(p):
        return p, getattr(cfg, "font_%s_index" % ruolo, 0)
    return cfg.font_path, cfg.font_index


def risolvi_fonti(cfg: Config) -> dict:
    """{ruolo: (nome reportlab, cap ratio, metriche)} piu' la voce '_base'."""
    fonti = {"_base": (register_font(cfg.font_path, cfg.font_index),
                       cap_ratio(cfg.font_path, cfg.font_index),
                       metriche_font(cfg.font_path, cfg.font_index))}
    for ruolo in RUOLI:
        pth, idx = font_ruolo(cfg, ruolo)
        if (pth, idx) == (cfg.font_path, cfg.font_index):
            continue
        try:
            fonti[ruolo] = (register_font(pth, idx), cap_ratio(pth, idx),
                            metriche_font(pth, idx))
        except Exception:
            pass
    return fonti


def componi_blocco(cfg: Config, t: Tassello, entries, fonti,
                   aw: float, ah: float):
    """Calcola la posizione delle righe dentro il tassello.

    Coordinate relative al centro del riquadro utile (gia' ruotato).
    Ritorna (righe, filetti, overflow) dove righe = lista di dizionari con
    testo, corpo, tracking, x, y (linea di base).
    """
    if not entries:
        return [], [], False

    dati = []
    for testo, ruolo in entries:
        fn, ratio_r, met_r = fonti.get(ruolo, fonti["_base"])
        cap = _cap_ruolo(cfg, ruolo) * mm * max(t.scala, 0.01)
        size = cap / ratio_r
        track = _track_ruolo(cfg, ruolo) * mm * max(t.scala, 0.01)
        dati.append({"testo": testo, "ruolo": ruolo, "cap": cap,
                     "size": size, "track": track, "font": fn, "met": met_r})

    def misura(k):
        """Applica il fattore k e calcola posizioni, larghezza e altezza."""
        avanzamenti = []
        for i, d in enumerate(dati):
            if i == 0:
                avanzamenti.append(0.0)
            elif d["ruolo"] == dati[i - 1]["ruolo"]:
                avanzamenti.append(max(cfg.interlinea, 0.1) * d["cap"] * k)
            else:
                avanzamenti.append(gap_base * mm * k + d["cap"] * k)
        h = sum(avanzamenti) + dati[0]["cap"] * k
        larg = []
        for d in dati:
            larg.append(_larghezza(d["testo"], d["font"], d["size"] * k,
                                   d["track"] * k))
        return avanzamenti, h, max(larg), larg

    # spazio fra blocchi di ruolo diverso: generale, personalizzato o massimo
    modo = getattr(t, "spazio_modo", "generale")
    ai_bordi = modo.startswith("ai bordi")
    if ai_bordi:
        gap_base = 0.0
    elif modo.startswith("personal"):
        gap_base = max(t.spazio_mm, 0.0)
    else:
        gap_base = max(cfg.spazio_blocchi_mm, 0.0)

    avanz, bh, bw, larg = misura(1.0)
    overflow = bw > aw + 1e-6 or bh > ah + 1e-6
    k = 1.0
    if overflow and cfg.adatta:
        k = min(aw / bw if bw > 0 else 1.0, ah / bh if bh > 0 else 1.0)
        avanz, bh, bw, larg = misura(k)
        overflow = False

    if ai_bordi:
        salti = [i for i in range(1, len(dati))
                 if dati[i]["ruolo"] != dati[i - 1]["ruolo"]]
        if salti and ah > bh:
            extra = (ah - bh) / len(salti)
            for i in salti:
                avanz[i] += extra
            bh = ah

    righe, filetti = [], []
    y = bh / 2.0 - dati[0]["cap"] * k
    for i, d in enumerate(dati):
        if i:
            y -= avanz[i]
        lw = larg[i]
        lsb, rsb, cima, fondo = _ink_riga(d["met"], d["testo"], d["size"] * k)
        if cfg.allineamento == "sinistra":
            x = -aw / 2.0 - (lsb if cfg.centratura_ottica else 0.0)
        elif cfg.allineamento == "destra":
            x = aw / 2.0 - lw + (rsb if cfg.centratura_ottica else 0.0)
        else:
            x = -lw / 2.0 - ((lsb - rsb) / 2.0 if cfg.centratura_ottica else 0.0)
        righe.append({"testo": d["testo"], "ruolo": d["ruolo"],
                      "size": d["size"] * k, "cap": d["cap"] * k,
                      "track": d["track"] * k, "x": x, "y": y, "w": lw,
                      "cima": cima, "fondo": fondo, "font": d["font"]})
        if i and d["ruolo"] != dati[i - 1]["ruolo"] and cfg.filetto:
            ytop = y + d["cap"] * k
            fondo_prec = righe[i - 1]["y"] - 0.22 * righe[i - 1]["cap"]
            filetti.append((fondo_prec + (ytop - fondo_prec) / 2.0,
                            aw * max(min(cfg.filetto_larghezza_perc, 100), 5) / 100.0))

    # riferimento per la centratura verticale
    dy = 0.0
    rif = cfg.rif_verticale
    if rif.startswith("ottico"):
        cime = [r["y"] + (r["cima"] if r["cima"] is not None else r["cap"])
                for r in righe]
        fondi = [r["y"] + (r["fondo"] if r["fondo"] is not None else 0.0)
                 for r in righe]
        if cime and fondi:
            dy = -(max(cime) + min(fondi)) / 2.0
    elif rif.startswith("solo il titolo"):
        tit = [r for r in righe if r["ruolo"] == "titolo"]
        if tit and len(tit) != len(righe):
            dy = -(max(r["y"] + r["cap"] for r in tit)
                   + min(r["y"] for r in tit)) / 2.0
    # ritocco manuale, nel senso di lettura del tassello
    dy -= getattr(t, "dy_mm", 0.0) * mm
    dx = getattr(t, "dx_mm", 0.0) * mm
    if dy or dx:
        for r in righe:
            r["y"] += dy
            r["x"] += dx
        filetti = [(fy + dy, flw) for fy, flw in filetti]

    return righe, filetti, overflow


# --------------------------------------------------------------------------
# Disposizione sul foglio
# --------------------------------------------------------------------------

def _base_da_incollare(t: Tassello):
    """Il pezzo di base da incollare sotto un tassello, o None.

    Esiste solo se la sporgenza (cornice_mm) e' maggiore di zero, e solo per i
    tasselli attivi: con il tassello disattivato il valore resta nella
    configurazione ma la base non si vede.  Ha le stesse proporzioni del
    tassello, sporge di cornice_mm per lato e ha gli angoli concentrici; e'
    vuota (niente testo, niente decoro).  Non va confusa con la cornice stampata
    dentro il tassello (il campo decoro).
    """
    c = max(getattr(t, "cornice_mm", 0.0), 0.0)
    if c <= 0:
        return None
    return replace(t, nome=t.nome + " (base)",
                   larghezza_mm=t.larghezza_mm + 2 * c,
                   altezza_mm=t.altezza_mm + 2 * c,
                   raggio_mm=(t.raggio_mm + c) if t.raggio_mm > 0 else 0.0,
                   composizione=VUOTO, cornice_mm=0.0, auto=True, decoro=False)


def linee_estese_attive(cfg: Config) -> bool:
    return "estese" in cfg.bordo_stile


def distanza_minima_linee_mm(cfg: Config) -> float:
    """Distanza minima fra due pezzi perche' le linee estese stiano per intero.

    Ogni linea puo' occupare al massimo meta' dello spazio libero verso il pezzo
    vicino (vedi segmenti_linee_estese): fra due pezzi allineati servono quindi
    due volte distanza + lunghezza, piu' un po' di respiro.
    """
    return 2.0 * (max(cfg.linee_offset_mm, 0.0) + max(cfg.linee_lung_mm, 0.0)) + 0.5


def gap_effettivo_mm(cfg: Config) -> float:
    """Distanza fra i pezzi nella disposizione automatica: quella impostata, ma
    con le linee estese non meno di distanza_minima_linee_mm()."""
    gap = max(cfg.gap_mm, 0.0)
    return max(gap, distanza_minima_linee_mm(cfg)) if linee_estese_attive(cfg) else gap


def serie_gap_effettivo_mm(cfg: Config) -> float:
    """Come gap_effettivo_mm, per la distanza fra una serie e la successiva."""
    gap = max(cfg.serie_gap_mm, 0.0)
    return max(gap, distanza_minima_linee_mm(cfg)) if linee_estese_attive(cfg) else gap


def _disponi_singola(cfg: Config) -> list[tuple[Tassello, float, float, int]]:
    """[(tassello, x, y_bottom, indice_in_cfg.tasselli)] in punti.
    Una sola serie: e' il layout che si vede nella scheda Tasselli. L'indice
    e' quello del tassello che genera il pezzo (la cornice porta l'indice
    del suo tassello, non un indice proprio, perche' non e' modificabile
    da sola)."""
    pw, ph = cfg.pagina_pt()
    mar = cfg.margine_mm * mm
    gap = gap_effettivo_mm(cfg) * mm
    fuori = []
    stato = {"x": mar, "y_top": ph - mar, "riga_h": 0.0}

    def piazza(t, origine):
        w, h = t.larghezza_mm * mm, t.altezza_mm * mm
        if not t.auto:
            fuori.append((t, t.x_mm * mm, ph - t.y_mm * mm - h, origine))
            return
        if stato["x"] + w > pw - mar + 1e-6 and stato["x"] > mar:
            stato["x"] = mar
            stato["y_top"] -= stato["riga_h"] + gap
            stato["riga_h"] = 0.0
        fuori.append((t, stato["x"], stato["y_top"] - h, origine))
        stato["x"] += w + gap
        stato["riga_h"] = max(stato["riga_h"], h)

    for i, t in enumerate(cfg.tasselli):
        if not t.attivo:
            continue
        copie = max(1, int(t.copie))
        for _ in range(copie):
            piazza(t, i)
        base = _base_da_incollare(t)
        if base is not None:
            for _ in range(copie):
                piazza(base, i)
    return fuori


def _disponi_pura(cfg: Config) -> list[tuple[Tassello, float, float, int]]:
    """Come _disponi_singola, ma ignora le posizioni manuali dei singoli
    tasselli e li dispone tutti in automatico. Serve solo come riferimento
    stabile per calcolare la posizione di default delle serie 2, 3, 4: cosi'
    non dipende da come e' stata sistemata a mano la serie 1."""
    pw, ph = cfg.pagina_pt()
    mar = cfg.margine_mm * mm
    gap = gap_effettivo_mm(cfg) * mm
    fuori = []
    stato = {"x": mar, "y_top": ph - mar, "riga_h": 0.0}

    def piazza(t, origine):
        w, h = t.larghezza_mm * mm, t.altezza_mm * mm
        if stato["x"] + w > pw - mar + 1e-6 and stato["x"] > mar:
            stato["x"] = mar
            stato["y_top"] -= stato["riga_h"] + gap
            stato["riga_h"] = 0.0
        fuori.append((t, stato["x"], stato["y_top"] - h, origine))
        stato["x"] += w + gap
        stato["riga_h"] = max(stato["riga_h"], h)

    for i, t in enumerate(cfg.tasselli):
        if not t.attivo:
            continue
        copie = max(1, int(t.copie))
        for _ in range(copie):
            piazza(t, i)
        base = _base_da_incollare(t)
        if base is not None:
            for _ in range(copie):
                piazza(base, i)
    return fuori


def disponi(cfg: Config) -> list[tuple[Tassello, float, float, int, int]]:
    """[(tassello, x, y_bottom, indice_serie, indice_tassello_origine)].

    Con 'serie' a 1 e' identico a prima (indice_serie sempre 1, rispetta le
    posizioni manuali gia' impostate). Con piu' serie, ogni tassello di ogni
    serie ha una propria posizione assoluta indipendente (stessa logica di
    auto/x_mm/y_mm), calcolata di default da un layout automatico di
    riferimento che non dipende da come e' messa la serie 1: percio'
    spostare un pezzo di una serie non sposta mai quello di un'altra."""
    template = _disponi_singola(cfg)
    fuori = [(t, x, y, 1, origine) for t, x, y, origine in template]
    n = max(1, min(int(cfg.serie), 4))
    if n <= 1 or not template:
        return fuori

    riferimento = _disponi_pura(cfg)
    if not riferimento:
        return fuori
    pw, ph = cfg.pagina_pt()
    top = max(y + t.altezza_mm * mm for t, x, y, _ in riferimento)
    bottom = min(y for _, _, y, _ in riferimento)
    altezza_serie_mm = max((top - bottom) / mm, 1.0)

    for k in range(2, n + 1):
        dy_shift = (k - 1) * (altezza_serie_mm + serie_gap_effettivo_mm(cfg)) * mm
        for t, x, y, origine in riferimento:
            h = t.altezza_mm * mm
            sorgente = cfg.tasselli[origine] if 0 <= origine < len(cfg.tasselli) else None
            auto_k = getattr(sorgente, "serie%d_auto" % k, True) if sorgente else True
            if cfg.serie_modo.startswith("manuale") and sorgente is not None and not auto_k:
                x_mm = getattr(sorgente, "serie%d_x_mm" % k)
                y_mm = getattr(sorgente, "serie%d_y_mm" % k)
                xp, yp = x_mm * mm, ph - y_mm * mm - h
            else:
                xp, yp = x, y - dy_shift
            fuori.append((replace(t, nome="%s #%d" % (t.nome, k)), xp, yp, k, origine))
    return fuori


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

def _penna_bordo(c, cfg: Config):
    """Colore e spessore delle linee di ritaglio (contorno, crocini, linee estese)."""
    grigio = 0.0 if (cfg.solo_nero and not cfg.bordo_pagina_separata) \
        else max(0.0, min(1.0, cfg.bordo_grigio))
    c.setStrokeGray(grigio)
    c.setLineWidth(max(cfg.bordo_spessore_mm, 0.01) * mm)


def segmenti_crocini(x, y, w, h, cfg: Config) -> list[tuple[float, float, float, float]]:
    """I crocini agli angoli di un pezzo: [(x1, y1, x2, y2)] in punti."""
    off = cfg.crocini_offset_mm * mm
    ln = max(cfg.crocini_lung_mm, 0.5) * mm
    segmenti = []
    for px, sx in ((x, -1), (x + w, 1)):
        for py, sy in ((y, -1), (y + h, 1)):
            segmenti.append((px + sx * off, py, px + sx * (off + ln), py))
            segmenti.append((px, py + sy * off, px, py + sy * (off + ln)))
    return segmenti


def _bordo(c, x, y, w, h, raggio_mm, cfg: Config):
    stile = cfg.bordo_stile
    if stile == "nessuno":
        return
    c.saveState()
    _penna_bordo(c, cfg)
    if "contorno" in stile:
        if "tratteggiato" in stile:
            d = max(cfg.bordo_tratto_mm, 0.2) * mm
            c.setDash([d, d], 0)
        r = max(0.0, min(raggio_mm * mm, min(w, h) / 2.0 - 0.01))
        if r > 0.05:
            c.roundRect(x, y, w, h, r, stroke=1, fill=0)
        else:
            c.rect(x, y, w, h, stroke=1, fill=0)
        c.setDash([], 0)
    if "crocini" in stile:
        for x1, y1, x2, y2 in segmenti_crocini(x, y, w, h, cfg):
            c.line(x1, y1, x2, y2)
    c.restoreState()


# --------------------------------------------------------------------------
# Linee estese: i bordi di ogni pezzo prolungati fuori dagli angoli
# --------------------------------------------------------------------------
#
# Servono per allinearlo alla lama di una taglierina: si ritaglia il pezzo
# grossolanamente, poi si appoggia la linea che resta sul margine di carta al
# bordo della lama, e si taglia.  Perche' funzionino ogni linea deve:
#   * stare sul margine del PROPRIO pezzo, non su quello di un altro: dopo il
#     ritaglio grossolano una linea del pezzo A finita sul margine del pezzo B
#     sembrerebbe il bordo di B.  Per questo ogni punto della linea deve essere
#     piu' vicino al proprio pezzo che a qualunque altro;
#   * non arrivare a meno di LINEE_LIBERO_MM da un altro pezzo;
#   * fermarsi a MARGINE_LINEE_MM dal bordo del foglio, dove molte stampanti
#     non stampano.

MARGINE_LINEE_MM = 3.0     # distanza minima dal bordo del foglio
LINEE_LIBERO_MM = 1.0      # distanza minima da un altro pezzo
LINEE_MIN_MM = 1.0         # sotto questa lunghezza una linea non si disegna
LINEE_PASSO_MM = 0.25      # passo di verifica lungo la linea
LINEE_TOLLERANZA_MM = 0.3  # accorciamenti minori di cosi' non si segnalano


@dataclass
class LineeEstese:
    segmenti: list          # [(x1, y1, x2, y2)] in punti
    proprietari: list       # per ogni segmento, l'indice del pezzo (in piazzati) a cui appartiene
    vicine_ad_altri_pezzi: list   # nomi dei pezzi con linee accorciate per i vicini
    vicine_al_bordo: list         # ... per il bordo del foglio


def _dist_punto_rett(px, py, rett) -> float:
    x, y, w, h = rett
    dx = max(x - px, 0.0, px - (x + w))
    dy = max(y - py, 0.0, py - (y + h))
    return math.hypot(dx, dy)


def _dist_rett_rett(a, b) -> float:
    dx = max(b[0] - (a[0] + a[2]), a[0] - (b[0] + b[2]), 0.0)
    dy = max(b[1] - (a[1] + a[3]), a[1] - (b[1] + b[3]), 0.0)
    return math.hypot(dx, dy)


def _fine_linea(px, py, dx, dy, inizio, lung, altri, pw, ph):
    """Fino a dove (in mm dal punto di partenza) arriva una linea.

    Restituisce (fine, motivo): motivo e' None se arriva alla lunghezza
    richiesta, altrimenti "pezzo" o "foglio" (cosa l'ha fermata).
    """
    def fermata(t):
        x, y = px + dx * t, py + dy * t
        if (x < MARGINE_LINEE_MM or y < MARGINE_LINEE_MM
                or x > pw - MARGINE_LINEE_MM or y > ph - MARGINE_LINEE_MM):
            return "foglio"
        for r in altri:
            if _dist_punto_rett(x, y, r) < max(t, LINEE_LIBERO_MM):
                return "pezzo"
        return None

    richiesta = inizio + lung
    ultimo_buono, t = None, inizio
    while t <= richiesta + 1e-9:
        motivo = fermata(t)
        if motivo:
            if ultimo_buono is None:
                return inizio, motivo
            lo, hi = ultimo_buono, t              # affino il punto di arresto
            for _ in range(14):
                medio = (lo + hi) / 2.0
                if fermata(medio) is None:
                    lo = medio
                else:
                    hi = medio
            return lo, motivo
        ultimo_buono = t
        t += LINEE_PASSO_MM
    if ultimo_buono is not None and richiesta - ultimo_buono > 1e-9:
        motivo = fermata(richiesta)
        if motivo:
            return ultimo_buono, motivo
    return richiesta, None


def segmenti_linee_estese(cfg: Config, piazzati) -> LineeEstese:
    """Le linee estese di tutti i pezzi di una pagina.

    piazzati e' il risultato di disponi().  Ogni pezzo ha otto linee, due per
    bordo (una per lato), che partono a linee_offset_mm dall'angolo e sono
    lunghe linee_lung_mm (dal punto di partenza), accorciate dove servirebbe
    spazio che non c'e' (vedi il commento sopra).  Un pezzo si segnala solo se una linea risulta
    piu' corta di LINEE_TOLLERANZA_MM rispetto a quella richiesta.
    """
    if not linee_estese_attive(cfg):
        return LineeEstese([], [], [], [])
    pw, ph = cfg.pagina_pt()
    pw, ph = pw / mm, ph / mm
    inizio = max(cfg.linee_offset_mm, 0.0)
    lung = max(cfg.linee_lung_mm, 0.0)
    # Un altro pezzo puo' fermare una linea anche se dista dal proprio pezzo fino
    # a due volte la sua lunghezza: un punto a distanza t dal proprio pezzo e'
    # fermato da un pezzo che gli sta a meno di t.  Serve questa portata per
    # scartare i pezzi davvero lontani senza ignorare quelli a meta' strada.
    portata = 2.0 * (inizio + lung) + LINEE_LIBERO_MM
    pezzi = [(t.nome, (x / mm, y / mm, t.larghezza_mm, t.altezza_mm))
             for t, x, y, _serie, _origine in piazzati]

    segmenti, proprietari, per_pezzi, per_bordo = [], [], [], []
    for i, (nome, r) in enumerate(pezzi):
        x, y, w, h = r
        altri = [q for j, (_n, q) in enumerate(pezzi)
                 if j != i and _dist_rett_rett(r, q) <= portata]
        # (punto di partenza, direzione): due linee per ciascuno dei quattro bordi
        partenze = [((x + w, y + h), (1, 0)), ((x, y + h), (-1, 0)),     # bordo alto
                    ((x + w, y), (1, 0)), ((x, y), (-1, 0)),             # bordo basso
                    ((x, y + h), (0, 1)), ((x, y), (0, -1)),             # bordo sinistro
                    ((x + w, y + h), (0, 1)), ((x + w, y), (0, -1))]     # bordo destro
        for (px, py), (dx, dy) in partenze:
            fine, motivo = _fine_linea(px, py, dx, dy, inizio, lung, altri, pw, ph)
            if lung - (fine - inizio) > LINEE_TOLLERANZA_MM:
                elenco = per_pezzi if motivo == "pezzo" else per_bordo
                if nome not in elenco:
                    elenco.append(nome)
            if fine - inizio >= LINEE_MIN_MM:
                segmenti.append(((px + dx * inizio) * mm, (py + dy * inizio) * mm,
                                 (px + dx * fine) * mm, (py + dy * fine) * mm))
                proprietari.append(i)
    return LineeEstese(segmenti, proprietari, per_pezzi, per_bordo)


def avvisi_linee(cfg: Config, linee: LineeEstese) -> list[str]:
    """Le frasi da mostrare all'utente quando qualche linea e' stata accorciata."""
    frasi = []
    if linee.vicine_ad_altri_pezzi:
        frasi.append("Linee di taglio accorciate, pezzi troppo vicini (servono almeno "
                     "%d mm fra i pezzi) in: %s"
                     % (math.ceil(distanza_minima_linee_mm(cfg)),
                        ", ".join(linee.vicine_ad_altri_pezzi)))
    if linee.vicine_al_bordo:
        frasi.append("Linee di taglio accorciate, troppo vicine al bordo del foglio in: "
                     + ", ".join(linee.vicine_al_bordo))
    return frasi


def avvisi_doratura(cfg: Config) -> list[str]:
    """Le frasi da mostrare quando un tratto che verra' dorato e' piu' sottile del
    minimo raccomandato (SPESSORE_DORATURA_MIN_MM): il foil rischia di non
    trasferirsi in modo continuo, specie su un tratto stampato con toner da
    ufficio.  Controlla solo i tratti che finiscono davvero sul tassello: la
    cornice stampata (decoro) e il filetto fra autore e titolo.  Non e' un
    limite imposto, solo un avviso: gli spessori restano liberi.
    """
    soglia = SPESSORE_DORATURA_MIN_MM
    frasi = avvisi_bitmap(cfg)
    if cfg.decoro_modello not in ("nessuno", DECORO_BITMAP):
        sottili = [s for s in (cfg.decoro_spessore_mm,) if 0 < s < soglia]
        if "doppio" in cfg.decoro_modello and 0 < cfg.decoro_spessore2_mm < soglia:
            sottili.append(cfg.decoro_spessore2_mm)
        if sottili:
            frasi.append("Cornice (decoro) piu' sottile di %.1f mm (%s): per la doratura "
                         "col foil rischia di non venire." % (soglia, ", ".join(
                             "%.2f mm" % s for s in sottili)))
    if cfg.filetto and 0 < cfg.filetto_spessore_mm < soglia:
        frasi.append("Filetto fra autore e titolo a %.2f mm: sotto %.1f mm rischia di non "
                     "venire con la doratura col foil." % (cfg.filetto_spessore_mm, soglia))
    return frasi


def _disegna_linee_estese(c, linee: LineeEstese, cfg: Config):
    if not linee.segmenti:
        return
    c.saveState()
    _penna_bordo(c, cfg)
    for x1, y1, x2, y2 in linee.segmenti:
        c.line(x1, y1, x2, y2)
    c.restoreState()


# --------------------------------------------------------------------------
# Allineamento nell'anteprima: la calamita
# --------------------------------------------------------------------------

def _agganci(x, dim, bersagli, soglia):
    """Il miglior spostamento su un asse, o None.

    x e dim sono la posizione e la misura del pezzo su quell'asse; il pezzo ha
    tre punti utili (inizio, meta', fine).  bersagli e' l'elenco delle
    coordinate a cui allinearsi.  Vince lo spostamento piu' piccolo, purche' non
    superi la soglia; a parita' vince il primo bersaglio dell'elenco.
    """
    migliore = None
    for t in bersagli:
        for f in (0.0, dim, dim / 2.0):            # prima i bordi, poi il centro
            delta = t - (x + f)
            if abs(delta) <= soglia and (migliore is None or abs(delta) < abs(migliore) - 1e-12):
                migliore = delta
    return migliore


def _guide(x, dim, bersagli):
    """Le coordinate dei bersagli con cui il pezzo, dov'e', e' allineato."""
    return sorted({round(t, 6) for t in bersagli
                   for f in (0.0, dim / 2.0, dim) if abs(t - (x + f)) < 1e-6})


def calamita(x, y, w, h, altri, soglia, pagina_w, pagina_h, margine=0.0):
    """Aggancia un pezzo che si sta trascinando ai bordi e ai centri degli altri.

    Tutto in millimetri, con y misurata dal basso (come nel PDF).  (x, y, w, h) e'
    il pezzo, altri sono i rettangoli (x, y, w, h) degli altri pezzi.  Bordo
    sinistro, centro e bordo destro del pezzo si allineano a quelli degli altri
    pezzi, ai due margini e al centro del foglio; lo stesso in verticale.  I due
    assi sono indipendenti e su ciascuno si sposta al piu' di soglia mm, verso il
    bersaglio piu' vicino.

    Restituisce (x, y, guide_x, guide_y): la nuova posizione e le coordinate
    delle linee guida da mostrare (vuote su un asse dove non c'e' stato aggancio).
    """
    soglia = max(soglia, 0.0)
    bx = [ox + k for ox, _oy, ow, _oh in altri for k in (0.0, ow, ow / 2.0)]
    bx += [margine, pagina_w - margine, pagina_w / 2.0]
    by = [oy + k for _ox, oy, _ow, oh_ in altri for k in (0.0, oh_, oh_ / 2.0)]
    by += [margine, pagina_h - margine, pagina_h / 2.0]
    dx = _agganci(x, w, bx, soglia)
    dy = _agganci(y, h, by, soglia)
    nx = x + dx if dx is not None else x
    ny = y + dy if dy is not None else y
    return (nx, ny,
            _guide(nx, w, bx) if dx is not None else [],
            _guide(ny, h, by) if dy is not None else [])


def padding_utile(cfg: Config, t: Tassello) -> float:
    """Margine interno effettivo: se c'e' una cornice stampata continua,
    il testo si scosta per non finirci addosso."""
    pad = t.margine_interno_mm * mm
    if not (cfg.decoro_modello != "nessuno" and getattr(t, "decoro", True) and cfg.decoro_rispetta):
        return pad
    if cfg.decoro_modello == DECORO_BITMAP:
        try:
            occupato = cfg.decoro_rientro_mm + spessore_bitmap_mm(cfg) * scala_bitmap(
                cfg, t.larghezza_mm * mm, t.altezza_mm * mm)
        except ValueError:
            return pad                          # file mancanti: l'errore esce altrove
        return max(pad, (occupato + 1.2) * mm)
    if cfg.decoro_modello in DECORI_CONTINUI:
        # ogni stile occupa uno spessore diverso oltre il rientro: la fascia
        # della greca, il diametro dei semicerchi del festone (che sporgono
        # verso l'interno per un raggio intero), l'altezza dei dentelli
        occupato = cfg.decoro_continuo_rientro_mm
        if cfg.decoro_modello == "greca continua":
            occupato += cfg.decoro_continuo_fascia_mm
        elif cfg.decoro_modello == "festone continuo":
            occupato += 2 * max(cfg.decoro_continuo_raggio_mm, 0.5)
        elif cfg.decoro_modello == "dentelli continui":
            occupato += cfg.decoro_continuo_altezza_mm
        return max(pad, (occupato + 1.2) * mm)
    if "cantonali" not in cfg.decoro_modello and "fleuron" not in cfg.decoro_modello:
        occupato = cfg.decoro_rientro_mm + cfg.decoro_spessore_mm
        if "doppio" in cfg.decoro_modello:
            occupato += cfg.decoro_distanza_mm + cfg.decoro_spessore2_mm
        pad = max(pad, (occupato + 1.2) * mm)
    return pad


def _curve_foglia(lunghezza, larghezza):
    """Il profilo di una fogliolina a mandorla, radicata in (0, 0), che punta
    lungo l'asse X positivo: due curve di Bezier (il profilo) piu' tre segmenti
    (la nervatura centrale e due venature laterali), come tuple (x0, y0, cx1,
    cy1, cx2, cy2, x1, y1) -- un segmento ha i due punti di controllo uguali
    ai suoi estremi, cosi' la stessa struttura serve per curve e rette.

    Tutto in "unita' foglia": va scalato e ruotato da chi chiama.
    """
    L, W = lunghezza, larghezza

    def retta(x0, y0, x1, y1):
        return (x0, y0, x0, y0, x1, y1, x1, y1)

    return [
        (0, 0, L * 0.25, W * 0.55, L * 0.7, W * 0.35, L, 0),
        (L, 0, L * 0.7, -W * 0.35, L * 0.25, -W * 0.55, 0, 0),
        retta(L * 0.08, 0, L * 0.92, 0),
        retta(L * 0.35, 0, L * 0.5, W * 0.18),
        retta(L * 0.55, 0, L * 0.68, W * 0.14),
        retta(L * 0.35, 0, L * 0.5, -W * 0.18),
        retta(L * 0.55, 0, L * 0.68, -W * 0.14),
    ]


def _curve_ricciolo(lunghezza):
    """Un piccolo tralcio arricciato, radicato in (0, 0), che si sviluppa lungo Y
    positivo e si arriccia su se stesso (la punta rientra verso la base)."""
    L = lunghezza
    return [
        (0, 0, L * 0.55, L * 0.05, L * 0.75, L * 0.35, L * 0.55, L * 0.55),
        (L * 0.55, L * 0.55, L * 0.4, L * 0.7, L * 0.2, L * 0.62, L * 0.28, L * 0.45),
        (L * 0.28, L * 0.45, L * 0.33, L * 0.35, L * 0.42, L * 0.36, L * 0.4, L * 0.46),
    ]


def _trasforma(curve, dx, dy, angolo_gradi, scala=1.0):
    """Trasla, ruota (attorno all'origine, poi trasla) e scala un elenco di curve."""
    a = math.radians(angolo_gradi)
    ca, sa = math.cos(a), math.sin(a)

    def punto(x, y):
        x, y = x * scala, y * scala
        return (dx + x * ca - y * sa, dy + x * sa + y * ca)

    out = []
    for x0, y0, cx1, cy1, cx2, cy2, x1, y1 in curve:
        out.append((*punto(x0, y0), *punto(cx1, cy1), *punto(cx2, cy2), *punto(x1, y1)))
    return out


def ruota_curva(curva, angolo_gradi):
    """Ruota una curva (vedi _curve_foglia) attorno all'origine."""
    return _trasforma([curva], 0, 0, angolo_gradi)[0]


def campiona_curva(curva, passi=10):
    """Punti (x, y) lungo una curva di Bezier cubica (vedi _curve_foglia), inclusi
    gli estremi.  Serve a chi non sa disegnare curve di Bezier native (Tk) e deve
    approssimarle con una polilinea."""
    x0, y0, cx1, cy1, cx2, cy2, x1, y1 = curva
    punti = []
    for i in range(passi + 1):
        t = i / passi
        mt = 1 - t
        x = mt**3 * x0 + 3 * mt**2 * t * cx1 + 3 * mt * t**2 * cx2 + t**3 * x1
        y = mt**3 * y0 + 3 * mt**2 * t * cy1 + 3 * mt * t**2 * cy2 + t**3 * y1
        punti.append((x, y))
    return punti


def curve_fleuron_angolo(dim_mm, con_ricciolo=True):
    """Le curve di un fleuron d'angolo (due foglie a ventaglio, piu' un ricciolo
    facoltativo), radicato nell'origine e rivolto lungo la bisettrice del primo
    quadrante (cioe' verso in alto a destra): chi chiama ruota e posiziona.

    dim_mm e' la lunghezza delle due foglie; le altre proporzioni (larghezza
    delle foglie, lunghezza del ricciolo) sono fisse rispetto a quella.
    """
    foglia = _curve_foglia(dim_mm, dim_mm * 0.38)
    curve = _trasforma(foglia, 0, 0, 30) + _trasforma(foglia, 0, 0, -30)
    if con_ricciolo:
        curve += _trasforma(_curve_ricciolo(dim_mm * 0.59), 0, 0, 6 + 90)
    return curve


def curve_fleuron_centrale(dim_mm):
    """Le curve di un piccolo motivo centrale (due foglioline che si aprono da un
    punto), radicato nell'origine e rivolto lungo l'asse Y positivo: pensato per
    il centro dei lati lunghi di un tassello, piu' piccolo del fleuron d'angolo.
    """
    foglia = _curve_foglia(dim_mm * 0.64, dim_mm * 0.64 * 0.4)
    return _trasforma(foglia, 0, 0, 90 - 55) + _trasforma(foglia, 0, 0, 90 + 55)


# --------------------------------------------------------------------------
# Bordi decorativi continui: greca, festone, dentelli
# --------------------------------------------------------------------------
#
# A differenza del fleuron (motivo isolato agli angoli), questi corrono lungo
# tutto il perimetro del tassello, a moduli ripetuti.  Ogni funzione "_lato_..."
# genera i punti (assoluti, in punti PDF) di UN lato, da un angolo al successivo
# in senso orario, partendo e arrivando esattamente sull'angolo: cosi' i quattro
# lati si concatenano in un'unica polilinea chiusa, senza segmenti scoperti.
#
# Ogni funzione riceve: (x0, y0) il punto di partenza, (dx, dy) la direzione
# unitaria del lato, "lunghezza" la misura del lato.  Il numero di moduli si
# adatta sempre per farne stare un numero intero: un lato quasi mai e' un
# multiplo esatto del modulo scelto, quindi il modulo reale si allarga o si
# stringe leggermente per chiudere in modo pulito, invece di lasciare un pezzo
# di modulo tagliato a meta' in un angolo.

def _lato_greca(x0, y0, dx, dy, lunghezza, larghezza_fascia):
    """I punti di un lato a chiave greca (meandro), a moduli di 4 unita' di
    base ciascuno (vedi il disegno: entra ed esce a meta' altezza fascia)."""
    h = larghezza_fascia
    m = h * 0.5
    u_base = h / 3.0
    modulo_locale = [(0, m), (u_base, m), (u_base, m - u_base), (2 * u_base, m - u_base),
                     (2 * u_base, m + u_base), (3 * u_base, m + u_base), (3 * u_base, m),
                     (4 * u_base, m)]
    passo_unitario = 4 * u_base
    n = max(1, round(lunghezza / passo_unitario))
    scala = lunghezza / (n * passo_unitario)
    px, py = -dy, dx
    pts = []
    for i in range(n):
        base = i * passo_unitario * scala
        for lx, ly in modulo_locale:
            lx, ly = lx * scala, ly * scala
            pts.append((x0 + dx * (base + lx) + px * ly, y0 + dy * (base + lx) + py * ly))
    return pts


def _lato_festone(x0, y0, dx, dy, lunghezza, raggio, campioni=16):
    """I punti di un lato a festone: una fila di semicerchi concatenati, la
    pancia rivolta verso l'interno del tassello."""
    n = max(1, round(lunghezza / (2 * raggio)))
    passo = lunghezza / n
    r = passo / 2.0
    px, py = -dy, dx
    pts = []
    for i in range(n):
        cx = x0 + dx * (i + 0.5) * passo
        cy = y0 + dy * (i + 0.5) * passo
        for k in range(campioni + 1):
            if i > 0 and k == 0:
                continue                          # non duplicare il punto di giunzione
            t = math.pi * k / campioni
            x = cx + r * (-math.cos(t) * dx + math.sin(t) * px)
            y = cy + r * (-math.cos(t) * dy + math.sin(t) * py)
            pts.append((x, y))
    return pts


def _lato_dentelli(x0, y0, dx, dy, lunghezza, passo_target, altezza):
    """I punti di un lato a dentelli: denti triangolari, la punta rivolta verso
    l'interno del tassello."""
    n = max(2, round(lunghezza / passo_target))
    passo = lunghezza / n
    px, py = -dy, dx
    pts = [(x0, y0)]
    for i in range(n):
        apice_x = x0 + dx * (i + 0.5) * passo + px * altezza
        apice_y = y0 + dy * (i + 0.5) * passo + py * altezza
        fine_x = x0 + dx * (i + 1) * passo
        fine_y = y0 + dy * (i + 1) * passo
        pts.append((apice_x, apice_y))
        pts.append((fine_x, fine_y))
    return pts


_LATO_PER_STILE = {
    "greca continua": lambda x0, y0, dx, dy, l, cfg: _lato_greca(
        x0, y0, dx, dy, l, cfg.decoro_continuo_fascia_mm * mm),
    "festone continuo": lambda x0, y0, dx, dy, l, cfg: _lato_festone(
        x0, y0, dx, dy, l, max(cfg.decoro_continuo_raggio_mm, 0.5) * mm),
    "dentelli continui": lambda x0, y0, dx, dy, l, cfg: _lato_dentelli(
        x0, y0, dx, dy, l, max(cfg.decoro_continuo_modulo_mm, 1.0) * mm,
        cfg.decoro_continuo_altezza_mm * mm),
}


def punti_bordo_continuo(cfg: Config, x, y, w, h):
    """I punti (assoluti, in punti PDF) del bordo continuo scelto in
    cfg.decoro_modello, lungo il perimetro del rettangolo (x, y, w, h) --
    gia' rientrato di decoro_continuo_rientro_mm rispetto al tassello.

    Restituisce una lista di punti che forma un contorno CHIUSO (l'ultimo punto
    non ripete il primo: chi disegna deve chiudere il path).  Lista vuota se lo
    stile non e' uno di quelli continui.
    """
    funzione = _LATO_PER_STILE.get(cfg.decoro_modello)
    if funzione is None:
        return []
    d = max(cfg.decoro_continuo_rientro_mm, 0.0) * mm
    X, Y, W, H = x + d, y + d, w - 2 * d, h - 2 * d
    if W <= 0.5 or H <= 0.5:
        return []
    lati = ((X, Y + H, 1, 0, W), (X + W, Y + H, 0, -1, H),
           (X + W, Y, -1, 0, W), (X, Y, 0, 1, H))
    pts = []
    for x0, y0, dx, dy, lunghezza in lati:
        segmento = funzione(x0, y0, dx, dy, lunghezza, cfg)
        pts.extend(segmento[:-1] if segmento and segmento[-1] == segmento[0] else segmento)
    return pts


def _disegna_curve(c, curve, dx, dy):
    """Disegna su un canvas ReportLab un elenco di curve (vedi _curve_foglia):
    ogni curva e' un path a se', cosi' resta aperta (non un contorno chiuso)."""
    for x0, y0, cx1, cy1, cx2, cy2, x1, y1 in curve:
        p = c.beginPath()
        p.moveTo(dx + x0, dy + y0)
        p.curveTo(dx + cx1, dy + cy1, dx + cx2, dy + cy2, dx + x1, dy + y1)
        c.drawPath(p, stroke=1, fill=0)


def dim_fleuron(cfg: Config, w, h):
    """La lunghezza delle foglie d'angolo, in punti: quella impostata, ma limitata
    perche' le foglie di due angoli opposti lungo lo stesso lato non si tocchino.

    Ogni foglia e' ruotata di 30 gradi rispetto al lato, quindi si estende lungo
    il lato per circa lunghezza * cos(30 gradi) = lunghezza * 0.866, non per
    tutta la sua lunghezza nominale.  Perche' le due foglie di angoli opposti
    (ciascuna lunga "dim") non si tocchino lungo un lato di misura L serve
    2 * dim * 0.866 < L, cioe' dim < L / 1.73.  0.52 lascia un margine visivo
    oltre la soglia esatta (0.577), invece di farle sfiorarsi appena.
    """
    return min(max(cfg.decoro_fleuron_dim_mm, 1.0) * mm, min(w, h) * 0.52)


def _fleuron_pdf(c, x, y, w, h, cfg: Config):
    d = dim_fleuron(cfg, w, h)
    c.setLineWidth(max(cfg.decoro_spessore_mm, 0.05) * mm)
    for (cx, cy), rot in (((x, y), 45), ((x + w, y), 135),
                          ((x + w, y + h), 225), ((x, y + h), 315)):
        curve = curve_fleuron_angolo(d / mm, cfg.decoro_fleuron_ricciolo)
        _disegna_curve(c, _trasforma(curve, 0, 0, rot), cx, cy)
    if cfg.decoro_fleuron_centrale:
        dc = d * 0.64
        for cx, cy, rot in ((x + w / 2.0, y, 90), (x + w / 2.0, y + h, 270)):
            curve = curve_fleuron_centrale(dc / mm)
            _disegna_curve(c, _trasforma(curve, 0, 0, rot - 90), cx, cy)


# --------------------------------------------------------------------------
# Cornice bitmap: composizione con blocchetti PNG
# --------------------------------------------------------------------------

_CACHE_BITMAP: dict = {}


def percorso_blocchetto(prefisso: str, ruolo: str) -> str:
    return "%s%s.png" % (prefisso, ruolo)


def ruoli_presenti(prefisso: str) -> list[str]:
    """I ruoli (fra tutti i 16 possibili) di cui esiste il file PNG."""
    return [r for r in BITMAP_RUOLI_TUTTI if os.path.isfile(percorso_blocchetto(prefisso, r))]


def carica_blocchetti(cfg: Config, nero_puro: bool | None = None) -> dict:
    """I blocchetti della cornice bitmap (8, o 16 se ci sono i tratti 1 e 2), come
    immagini RGBA di Pillow.

    Restituisce {ruolo: (immagine, larghezza_pt, altezza_pt)}.  La misura in
    punti viene dai pixel e dalla risoluzione (decoro_bitmap_dpi, oppure quella
    scritta nel PNG, oppure 96): i blocchetti non vengono mai scalati, cambiare
    i dpi ne cambia solo la dimensione stampata.  Con nero_puro (di default
    cfg.solo_nero) la trasparenza parziale dei bordi diventa tutto o niente,
    cosi' il toner non fa grigi.  Solleva ValueError se manca un file.
    """
    try:
        from PIL import Image
    except ImportError:
        raise ValueError("La cornice bitmap richiede la libreria Pillow (pip install pillow).")
    if not cfg.decoro_bitmap_prefisso:
        raise ValueError("Cornice bitmap: scegli i file dei blocchetti.")
    if nero_puro is None:
        nero_puro = cfg.solo_nero
    pre = cfg.decoro_bitmap_prefisso
    mancanti = [os.path.basename(percorso_blocchetto(pre, r)) for r in BITMAP_RUOLI
                if not os.path.isfile(percorso_blocchetto(pre, r))]
    if mancanti:
        raise ValueError("Cornice bitmap: file mancanti: %s" % ", ".join(mancanti))
    extra = [r for r in BITMAP_RUOLI_EXTRA if os.path.isfile(percorso_blocchetto(pre, r))]
    for lato in ("hu", "hl", "vl", "vr"):
        if (lato + "1" in extra) != (lato + "2" in extra):
            manca = lato + ("2" if lato + "1" in extra else "1")
            raise ValueError("Cornice bitmap: file mancanti: %s (i tratti 1 e 2 del lato "
                             "vanno insieme)" % os.path.basename(percorso_blocchetto(pre, manca)))
    ruoli = BITMAP_RUOLI + tuple(extra)
    percorsi = {r: percorso_blocchetto(pre, r) for r in ruoli}
    chiave = (pre, float(cfg.decoro_bitmap_dpi), bool(nero_puro),
              tuple(os.path.getmtime(percorsi[r]) for r in ruoli))
    if chiave in _CACHE_BITMAP:
        return _CACHE_BITMAP[chiave]
    blocchi = {}
    for r in ruoli:
        try:
            im = Image.open(percorsi[r])
            im.load()
        except Exception as e:
            raise ValueError("Cornice bitmap: %s non si apre (%s)."
                             % (os.path.basename(percorsi[r]), e))
        dpi = cfg.decoro_bitmap_dpi
        if dpi <= 0:
            dpi = float(im.info.get("dpi", (96.0, 96.0))[0] or 96.0)
        im = im.convert("RGBA")
        if nero_puro:
            a = im.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
            im = Image.merge("RGBA", (*Image.new("RGB", im.size, (0, 0, 0)).split(), a))
        blocchi[r] = (im, im.width * 72.0 / dpi, im.height * 72.0 / dpi)
    _CACHE_BITMAP.clear()           # una sola cornice alla volta in memoria
    _CACHE_BITMAP[chiave] = blocchi
    return blocchi


def spessore_bitmap_mm(cfg: Config) -> float:
    """Quanto la cornice bitmap entra nel tassello dal bordo, in mm: il piu'
    profondo dei quattro tratti, contando solo i pixel non trasparenti."""
    blocchi = carica_blocchetti(cfg)
    prof = []
    for r in blocchi:
        if r[0] not in "hv":
            continue
        im, wp, hp = blocchi[r]
        bb = im.getchannel("A").getbbox()
        if not bb:
            continue
        x0, y0, x1, y1 = bb
        if r[:2] == "hu":
            prof.append(y1 * hp / im.height)
        elif r[:2] == "hl":
            prof.append((im.height - y0) * hp / im.height)
        elif r[:2] == "vl":
            prof.append(x1 * wp / im.width)
        else:
            prof.append((im.width - x0) * wp / im.width)
    return max(prof, default=0.0) / mm


def fattore_angoli(dim, W, H):
    """Di quanto vanno accorciati gli angoli perche' stiano nel riquadro W x H:
    (kx, ky), 1 = entrano interi."""
    larg = max(dim["ul"][0] + dim["ur"][0], dim["ll"][0] + dim["lr"][0])
    alt = max(dim["ul"][1] + dim["ll"][1], dim["ur"][1] + dim["lr"][1])
    return (min(1.0, max(W, 0) / larg) if larg > 0 else 1.0,
            min(1.0, max(H, 0) / alt) if alt > 0 else 1.0)


def scala_bitmap(cfg: Config, w, h) -> float:
    """Fattore (<= 1) con cui rimpicciolire tutti i blocchetti in un tassello w x h
    (punti) perche' i quattro angoli ci stiano; 1 se entrano o se la riduzione e'
    spenta.  E' l'unico caso in cui i blocchetti vengono scalati."""
    if not cfg.decoro_bitmap_riduci:
        return 1.0
    blocchi = carica_blocchetti(cfg)
    d = 2 * max(cfg.decoro_rientro_mm, 0.0) * mm
    kx, ky = fattore_angoli({r: (blocchi[r][1], blocchi[r][2]) for r in BITMAP_RUOLI},
                            w - d, h - d)
    return min(kx, ky, 1.0)


def pezzi_bitmap(cfg: Config, x, y, w, h):
    """Dove mettere i blocchetti per una cornice nel rettangolo (x, y, w, h).

    Coordinate in punti, origine in basso a sinistra.  Restituisce
    (pezzi, motivo): pezzi e' una lista di (ruolo, x, y, larghezza, altezza,
    ritaglio), con ritaglio = None oppure (x, y, w, h) fuori dal quale il
    pezzo va tagliato; motivo e' None se tutto entra, altrimenti la frase che
    spiega perche' gli angoli non stanno nel tassello (e pezzi e' vuota).

    I quattro angoli vanno agli angoli, i tratti si ripetono nel vuoto che
    resta fra due angoli.  Se il vuoto non e' un multiplo intero del blocchetto
    i tratti interi sono centrati e ai capi resta un po' di spazio; con
    decoro_bitmap_taglio, invece, se ne mette uno in piu' e i due capi
    vengono tagliati in modo uguale: niente vuoti.  Sempre con il taglio
    attivo, se i quattro angoli sono troppo grandi per il tassello vengono
    tagliati dal lato verso il centro, fin dove serve a farli incontrare.
    Se invece decoro_bitmap_riduci e' attivo (di default) si rimpiccioliscono
    tutti i blocchetti dello stesso fattore fino a farli stare, senza tagli.
    """
    blocchi = carica_blocchetti(cfg)
    d = max(cfg.decoro_rientro_mm, 0.0) * mm
    X, Y, W, H = x + d, y + d, w - 2 * d, h - 2 * d
    sc = scala_bitmap(cfg, w, h)
    dim = {r: (blocchi[r][1] * sc, blocchi[r][2] * sc) for r in blocchi}
    kx, ky = fattore_angoli(dim, W, H)
    if (kx < 1 or ky < 1) and not cfg.decoro_bitmap_taglio:
        return [], ("i quattro angoli (%.0f x %.0f mm ciascuno) non stanno nel riquadro %.0f x %.0f mm: "
                    "attiva il taglio per tagliarli a meta', oppure usa blocchetti piu' piccoli"
                    % (dim["ul"][0] / mm, dim["ul"][1] / mm, max(W, 0) / mm, max(H, 0) / mm))
    if W <= 0 or H <= 0:
        return [], "il riquadro e' vuoto"
    # parte visibile di ogni angolo (kx, ky < 1: angoli troppo grandi, tagliati
    # dal lato verso il centro; il bordo esterno resta intero)
    vis = {r: (dim[r][0] * kx, dim[r][1] * ky) for r in ("ul", "ur", "ll", "lr")}
    origine = {"ul": (X, Y + H - dim["ul"][1]), "ur": (X + W - dim["ur"][0], Y + H - dim["ur"][1]),
           "ll": (X, Y), "lr": (X + W - dim["lr"][0], Y)}
    pezzi = []
    for r in ("ul", "ur", "ll", "lr"):
        px, py = origine[r]
        vw, vh = vis[r]
        ritaglio = None
        if kx < 1 or ky < 1:
            ritaglio = (px if r in ("ul", "ll") else px + dim[r][0] - vw,
                        py if r in ("ll", "lr") else py + dim[r][1] - vh, vw, vh)
        pezzi.append((r, px, py, *dim[r], ritaglio))

    def ripeti(a, b, passo):
        """Posizioni di partenza dei blocchetti lungo il tratto da a a b."""
        lung = b - a
        if lung <= 1e-6 or passo <= 0:
            return [], False
        n = math.ceil(lung / passo - 1e-6) if cfg.decoro_bitmap_taglio else int(lung / passo + 1e-6)
        inizio = a + (lung - n * passo) / 2.0
        return [inizio + i * passo for i in range(n)], n * passo > lung + 1e-6

    def meta(r, a, b, passo, lungo, fisso, ancora_a):
        """Una meta' di lato a 16: il tratto r ripetuto fra a e b.  Senza taglio i
        tratti interi partono dal capo a (quello dell'angolo) e l'avanzo resta
        accanto al centro; con il taglio partono dal centro e l'ultimo, quello
        dell'angolo, viene tagliato.  lungo = 'x' per i lati orizzontali."""
        lung = b - a
        if lung <= 1e-6 or passo <= 0:
            return
        n = math.ceil(lung / passo - 1e-6) if cfg.decoro_bitmap_taglio else int(lung / passo + 1e-6)
        taglia = n * passo > lung + 1e-6
        for i in range(n):
            pos = a + i * passo if ancora_a else b - (i + 1) * passo
            if lungo == "x":
                pezzi.append((r, pos, fisso, *dim[r],
                              (a, fisso, lung, dim[r][1]) if taglia else None))
            else:
                pezzi.append((r, fisso, pos, *dim[r],
                              (fisso, a, dim[r][0], lung) if taglia else None))

    def lato16(c, r_lo, r_hi, a, b, lungo, fisso):
        """Lato a 16: il pezzo di mezzo c al centro dello spazio a-b, r_lo nella
        meta' verso a e r_hi in quella verso b.  Se il centro non ci sta viene
        omesso e le due meta' si dividono tutto lo spazio."""
        k = 0 if lungo == "x" else 1
        cw = dim[c][k]
        mid = (a + b) / 2.0
        if cw <= b - a + 1e-6:
            m0, m1 = mid - cw / 2.0, mid + cw / 2.0
            if lungo == "x":
                pezzi.append((c, m0, fisso, *dim[c], None))
            else:
                pezzi.append((c, fisso, m0, *dim[c], None))
        else:
            m0 = m1 = mid
        taglio = cfg.decoro_bitmap_taglio
        # con il taglio si parte dal centro, senza dal capo dell'angolo
        meta(r_lo, a, m0, dim[r_lo][k], lungo, fisso, not taglio)
        meta(r_hi, m1, b, dim[r_hi][k], lungo, fisso, taglio)

    # orizzontali: alto (hu) e basso (hl), fra i due angoli di quel lato
    for r, yy, sx, dx in (("hu", Y + H - dim["hu"][1], "ul", "ur"),
                          ("hl", Y, "ll", "lr")):
        a, b = X + vis[sx][0], X + W - vis[dx][0]
        if r + "1" in dim:
            # hu: 1 a destra, 2 a sinistra; hl: 1 a sinistra, 2 a destra
            lo, hi = (("hu2", "hu1") if r == "hu" else ("hl1", "hl2"))
            lato16(r, lo, hi, a, b, "x", yy)
            continue
        pos, taglia = ripeti(a, b, dim[r][0])
        for px in pos:
            pezzi.append((r, px, yy, *dim[r], (a, yy, b - a, dim[r][1]) if taglia else None))
    # verticali: sinistro (vl) e destro (vr), fra i due angoli di quel lato
    for r, xx, sy, dy in (("vl", X, "ll", "ul"),
                          ("vr", X + W - dim["vr"][0], "lr", "ur")):
        a, b = Y + vis[sy][1], Y + H - vis[dy][1]
        if r + "1" in dim:
            # vl: 1 in alto, 2 in basso; vr: 1 in basso, 2 in alto (y cresce verso l'alto)
            lo, hi = (("vl2", "vl1") if r == "vl" else ("vr1", "vr2"))
            lato16(r, lo, hi, a, b, "y", xx)
            continue
        pos, taglia = ripeti(a, b, dim[r][1])
        for py in pos:
            pezzi.append((r, xx, py, *dim[r], (xx, a, dim[r][0], b - a) if taglia else None))
    return pezzi, None


def avvisi_bitmap(cfg: Config) -> list[str]:
    """Avvisi sulla cornice bitmap: file che mancano, angoli che non entrano in
    un tassello.  Vuoto se il modello scelto e' un altro."""
    if cfg.decoro_modello != DECORO_BITMAP:
        return []
    try:
        carica_blocchetti(cfg)
    except ValueError as e:
        return [str(e)]
    frasi = []
    for t in cfg.tasselli:
        if not (t.attivo and getattr(t, "decoro", True)):
            continue
        w, h = t.larghezza_mm * mm, t.altezza_mm * mm
        pezzi, motivo = pezzi_bitmap(cfg, 0, 0, w, h)
        if motivo:
            frasi.append("Cornice bitmap su '%s': %s; quindi non viene disegnata." % (t.nome, motivo))
            continue
        omessi = [r for r in ("hu", "hl", "vl", "vr")
                  if r + "1" in carica_blocchetti(cfg) and not any(p[0] == r for p in pezzi)]
        if omessi:
            frasi.append("Cornice bitmap su '%s': il pezzo di mezzo (%s) non sta fra gli angoli: "
                         "omesso." % (t.nome, ", ".join(omessi)))
        sc = scala_bitmap(cfg, w, h)
        if sc < 1:
            frasi.append("Cornice bitmap su '%s': blocchetti rimpiccioliti al %.0f%% per farli "
                         "stare (la qualita' dipende dai dpi originali)." % (t.nome, sc * 100))
            continue
        d = 2 * max(cfg.decoro_rientro_mm, 0.0) * mm
        blocchi = carica_blocchetti(cfg)
        kx, ky = fattore_angoli({r: (blocchi[r][1], blocchi[r][2]) for r in BITMAP_RUOLI},
                                w - d, h - d)
        if kx < 1 or ky < 1:
            frasi.append("Cornice bitmap su '%s': angoli troppo grandi, tagliati a meta' per "
                         "farli stare (blocchetti piu' piccoli li terrebbero interi)." % t.nome)
    return frasi


def _bitmap_pdf(c, x, y, w, h, cfg: Config):
    from reportlab.lib.utils import ImageReader
    pezzi, _motivo = pezzi_bitmap(cfg, x, y, w, h)
    blocchi = carica_blocchetti(cfg)
    for ruolo, px, py, pw_, ph_, ritaglio in pezzi:
        if ritaglio:
            c.saveState()
            p = c.beginPath()
            p.rect(*ritaglio)
            c.clipPath(p, stroke=0, fill=0)
        c.drawImage(ImageReader(blocchi[ruolo][0]), px, py, pw_, ph_, mask="auto")
        if ritaglio:
            c.restoreState()


def _decoro(c, x, y, w, h, raggio_mm: float, cfg: Config):
    """Cornice stampata dentro il tassello (stesso nero del testo)."""
    modello = cfg.decoro_modello
    if modello == "nessuno":
        return
    d = max(cfg.decoro_rientro_mm, 0.0) * mm
    sp = max(cfg.decoro_spessore_mm, 0.05) * mm
    sp2 = max(cfg.decoro_spessore2_mm, 0.05) * mm
    gap = max(cfg.decoro_distanza_mm, 0.0) * mm
    X, Y, W, H = x + d, y + d, w - 2 * d, h - 2 * d
    if W <= 0.5 or H <= 0.5:
        return
    rag = max(0.0, raggio_mm * mm - d)

    c.saveState()
    c.setStrokeGray(0)
    c.setFillGray(0)

    def rettangolo(X, Y, W, H, spess, rag):
        if W <= 0 or H <= 0:
            return
        c.setLineWidth(spess)
        r = max(0.0, min(rag, min(W, H) / 2.0 - 0.01))
        if r > 0.05:
            c.roundRect(X, Y, W, H, r, stroke=1, fill=0)
        else:
            c.rect(X, Y, W, H, stroke=1, fill=0)

    if modello == "filetto semplice":
        rettangolo(X, Y, W, H, sp, rag)

    elif modello == "doppio filetto":
        rettangolo(X, Y, W, H, sp, rag)
        k = gap + sp / 2.0 + sp2 / 2.0
        rettangolo(X + k, Y + k, W - 2 * k, H - 2 * k, sp2,
                   max(0.0, rag - k))

    elif modello == "filetto tratteggiato":
        tratto = max(cfg.decoro_spessore_mm * 3, 0.8) * mm
        c.setDash([tratto, tratto], 0)
        rettangolo(X, Y, W, H, sp, rag)
        c.setDash([], 0)

    elif modello == "angoli incrociati":
        s = max(cfg.decoro_sporgenza_mm, 0.0) * mm
        s = min(s, d - sp)                      # non uscire dal tassello
        c.setLineWidth(sp)
        for yy in (Y, Y + H):
            c.line(X - s, yy, X + W + s, yy)
        for xx in (X, X + W):
            c.line(xx, Y - s, xx, Y + H + s)

    elif modello == "cantonali (solo angoli)":
        a = max(cfg.decoro_angolo_mm, 1.0) * mm
        a = min(a, W / 2.2, H / 2.2)
        c.setLineWidth(sp)
        for xx, sx in ((X, 1), (X + W, -1)):
            for yy, sy in ((Y, 1), (Y + H, -1)):
                c.line(xx, yy, xx + sx * a, yy)
                c.line(xx, yy, xx, yy + sy * a)

    elif modello == "filetto con punti agli angoli":
        rettangolo(X, Y, W, H, sp, rag)
        r = max(cfg.decoro_punto_mm, 0.2) * mm / 2.0
        for xx in (X, X + W):
            for yy in (Y, Y + H):
                c.circle(xx, yy, r, stroke=0, fill=1)

    elif modello == "fleuron agli angoli":
        _fleuron_pdf(c, x, y, w, h, cfg)

    elif modello == DECORO_BITMAP:
        _bitmap_pdf(c, x, y, w, h, cfg)

    elif modello in DECORI_CONTINUI:
        pts = punti_bordo_continuo(cfg, x, y, w, h)
        if pts:
            c.setLineWidth(sp)
            c.setLineJoin(1)
            p = c.beginPath()
            p.moveTo(*pts[0])
            for px, py in pts[1:]:
                p.lineTo(px, py)
            p.close()
            c.drawPath(p, stroke=1, fill=0)

    c.restoreState()


def _registro(c, pw, ph, cfg: Config):
    m = max(cfg.margine_mm * 0.45, 5.0) * mm
    l = 4 * mm
    c.saveState()
    c.setStrokeGray(0)
    c.setLineWidth(0.15 * mm)
    for px, py in ((m, m), (pw - m, m), (m, ph - m), (pw - m, ph - m)):
        c.line(px - l, py, px + l, py)
        c.line(px, py - l, px, py + l)
        c.circle(px, py, l * 0.5, stroke=1, fill=0)
    c.restoreState()


def _testo(c, cx, cy, w, h, righe, filetti, rot, fontname, cfg: Config):
    c.saveState()
    c.translate(cx, cy)
    if rot:
        c.rotate(rot)
    c.setFillGray(0)
    c.setStrokeGray(0)
    if cfg.ingrosso_mm > 0:
        c.setLineWidth(cfg.ingrosso_mm * mm)
        c.setLineJoin(1)
    for r in righe:
        to = c.beginText()
        to.setFont(r.get("font") or fontname, r["size"])
        # Tc e Tr restano nello stato del testo: vanno riscritti a ogni riga,
        # altrimenti la spaziatura di una riga si trascina su quella dopo.
        to.setCharSpace(r["track"] or 0)
        to.setTextRenderMode(2 if cfg.ingrosso_mm > 0 else 0)
        to.setTextOrigin(r["x"], r["y"])
        to.textOut(r["testo"])
        c.drawText(to)
    for y, lw in filetti:
        c.setLineWidth(max(cfg.filetto_spessore_mm, 0.05) * mm)
        c.line(-lw / 2.0, y, lw / 2.0, y)
    c.restoreState()


def build_pdf(cfg: Config, out_path: str) -> dict:
    if not cfg.font_path or not os.path.isfile(cfg.font_path):
        raise ValueError("Nessun font valido selezionato.")
    for pth in [cfg.font_path] + [font_ruolo(cfg, r)[0] for r in RUOLI]:
        if os.path.splitext(pth)[1].lower() in (".otf", ".otc"):
            raise ValueError("reportlab non supporta i font OpenType/CFF (.otf).\n"
                             "Scegli un .ttf/.ttc o converti il font.")
    attivi = [t for t in cfg.tasselli if t.attivo]
    if not attivi:
        raise ValueError("Nessun tassello attivo.")
    if cfg.bordo_stile == "nessuno" and any(t.cornice_mm > 0 for t in attivi):
        raise ValueError("Le cornici sono riquadri vuoti: senza bordi di "
                         "ritaglio resterebbero invisibili.\nScegli uno stile "
                         "di bordo nella scheda Foglio e taglio.")

    if cfg.decoro_modello == DECORO_BITMAP:
        carica_blocchetti(cfg)              # ValueError se mancano file

    fonti = risolvi_fonti(cfg)
    fontname, ratio, met = fonti["_base"]
    pw, ph = cfg.pagina_pt()

    piazzati = disponi(cfg)
    linee = segmenti_linee_estese(cfg, piazzati)
    c = rl_canvas.Canvas(out_path, pagesize=(pw, ph))
    c.setTitle("%s - %s" % (cfg.autore, cfg.titolo.replace("\n", " ")))
    c.setAuthor(APP_NAME)
    c.setPageCompression(1)

    avvisi = []
    fuori_foglio = []

    def pagina_tasselli(testo=True, bordi=True):
        for t, x, y, _serie, _origine in piazzati:
            w, h = t.larghezza_mm * mm, t.altezza_mm * mm
            if bordi:
                _bordo(c, x, y, w, h, t.raggio_mm, cfg)
            if not testo:
                continue
            if getattr(t, "decoro", True):
                _decoro(c, x, y, w, h, t.raggio_mm, cfg)
            rot = int(t.rotazione) % 360
            bw, bh = (w, h) if rot in (0, 180) else (h, w)
            pad = padding_utile(cfg, t)
            aw, ah = max(bw - 2 * pad, 1.0), max(bh - 2 * pad, 1.0)
            righe, filetti, over = componi_blocco(
                cfg, t, righe_tassello(cfg, t), fonti, aw, ah)
            if over:
                avvisi.append(t.nome)
            _testo(c, x + w / 2.0, y + h / 2.0, w, h, righe, filetti, rot,
                   fontname, cfg)
        if bordi:
            _disegna_linee_estese(c, linee, cfg)

    for t, x, y, _serie, _origine in piazzati:
        w, h = t.larghezza_mm * mm, t.altezza_mm * mm
        if x < 0 or y < 0 or x + w > pw + 1e-6 or y + h > ph + 1e-6:
            if t.nome not in fuori_foglio:
                fuori_foglio.append(t.nome)

    pagine = 0
    if cfg.bordo_pagina_separata and cfg.bordo_stile != "nessuno":
        pagina_tasselli(testo=True, bordi=False)
        _registro(c, pw, ph, cfg)
        c.showPage()
        pagine += 1
        pagina_tasselli(testo=False, bordi=True)
        _registro(c, pw, ph, cfg)
        c.setFillGray(0.4)
        c.setFont("Helvetica", 7)
        c.drawString(cfg.margine_mm * mm, cfg.margine_mm * mm * 0.4,
                     "guide di taglio - non dorare")
        c.showPage()
        pagine += 1
    else:
        pagina_tasselli(testo=True, bordi=True)
        if cfg.crocini_registro:
            _registro(c, pw, ph, cfg)
        c.showPage()
        pagine += 1

    # ---- pagina di prova con corpi crescenti ----
    if cfg.prova:
        base = attivi[0]
        passo = max(cfg.prova_passo_mm, 0.05)
        n = int(math.floor((cfg.prova_a_mm - cfg.prova_da_mm) / passo + 1e-9)) + 1
        n = max(1, min(n, 200))
        w, h = base.larghezza_mm * mm, base.altezza_mm * mm
        mar = cfg.margine_mm * mm
        gap = 4 * mm
        et = 3.4 * mm
        cols = max(1, int((pw - 2 * mar + gap) // (w + gap)))
        y = ph - mar - h
        col = 0
        prova_cfg = replace(cfg, adatta=False)
        # celle troppo vicine per le linee estese: qui basta un contorno
        cfg_bordo = replace(cfg, bordo_stile="contorno") \
            if cfg.bordo_stile == "linee estese" else cfg
        for i in range(n):
            s = round(cfg.prova_da_mm + i * passo, 3)
            if y < mar:
                c.showPage()
                pagine += 1
                y = ph - mar - h
                col = 0
            x = mar + col * (w + gap)
            _bordo(c, x, y, w, h, base.raggio_mm, cfg_bordo)
            if getattr(base, "decoro", True):
                _decoro(c, x, y, w, h, base.raggio_mm, cfg)
            t2 = replace(base, scala=1.0)
            cfg2 = replace(prova_cfg, cap_titolo_mm=s,
                           cap_autore_mm=s * cfg.cap_autore_mm / max(cfg.cap_titolo_mm, 0.01),
                           cap_extra_mm=s * cfg.cap_extra_mm / max(cfg.cap_titolo_mm, 0.01))
            rot = int(base.rotazione) % 360
            bw, bh = (w, h) if rot in (0, 180) else (h, w)
            pad = padding_utile(cfg, base)
            righe, filetti, _ = componi_blocco(
                cfg2, t2, righe_tassello(cfg2, t2), fonti,
                max(bw - 2 * pad, 1), max(bh - 2 * pad, 1))
            _testo(c, x + w / 2.0, y + h / 2.0, w, h, righe, filetti, rot,
                   fontname, cfg2)
            c.setFillGray(0 if cfg.solo_nero else 0.35)
            c.setFont("Helvetica", 6.5)
            c.drawString(x, y - 2.7 * mm, ("%.2f mm" % s).replace(".", ","))
            col += 1
            if col >= cols:
                col = 0
                y -= h + et + gap
        c.showPage()
        pagine += 1

    c.save()
    return {
        "pagine": pagine,
        "tasselli": len(piazzati),
        "cap_ratio": ratio,
        "overflow": avvisi,
        "fuori_foglio": fuori_foglio,
        "linee_accorciate": linee.vicine_ad_altri_pezzi + [
            n for n in linee.vicine_al_bordo if n not in linee.vicine_ad_altri_pezzi],
        "avvisi_linee": avvisi_linee(cfg, linee),
        "avvisi_doratura": avvisi_doratura(cfg),
    }


def apri_file(path: str):
    try:
        if platform.system() == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


# --------------------------------------------------------------------------
# Interfaccia
# --------------------------------------------------------------------------
