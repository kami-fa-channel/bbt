"""Scheda Tasselli: interfaccia grafica del motore in legatoria/tasselli.py."""

from __future__ import annotations

import json
import math
import os
import tempfile
import threading
import tkinter as tk
from dataclasses import asdict, fields, replace
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from ..tasselli import (
    APP_NAME, apri_file, CARTELLA_CORNICI, avvisi_doratura, avvisi_linee, BORDER_STYLES, build_pdf, calamita,
    campiona_curva, componi_blocco, curve_fleuron_angolo, curve_fleuron_centrale,
    dim_fleuron, ruota_curva, BITMAP_RUOLI, BITMAP_RUOLI_TUTTI, ruoli_presenti, carica_blocchetti, DECORO_BITMAP, pezzi_bitmap,
    COMPOSIZIONI, Config, config_da_dict, DECORI, DECORI_CONTINUI, disponi,
    distanza_minima_linee_mm, FontEntry, linee_estese_attive, mm, padding_utile,
    PAGE_SIZES, punti_bordo_continuo, RIF_VERTICALI,
    righe_tassello, risolvi_fonti, ROTAZIONI, scan_fonts, segmenti_crocini,
    segmenti_linee_estese, SPAZI, ULTIMO, VUOTO,
)
from .comuni import Suggerimento

# Zoom dell'anteprima: 1 = il foglio intero nella finestra.  Non si ingrandisce
# oltre PX_PER_MM_MAX pixel per millimetro, dove un pixel vale ben meno di un decimo
# di millimetro e i caratteri ingranditi diventerebbero lenti da disegnare.
PX_PER_MM_MAX = 60.0
FATTORE_ZOOM = 1.25            # per uno scatto di rotella
FATTORE_ZOOM_PULSANTI = 1.5    # per un clic su + o -
MARGINE_VISTA_PX = 8           # tra il foglio e il bordo dell'anteprima
SOGLIA_CALAMITA_PX = 6         # entro quanti pixel dello schermo un pezzo si aggancia
COLORE_GUIDA = "#d4359a"       # le linee guida della calamita


class SchedaTasselli(ttk.Frame):
    """La scheda Tasselli: va inserita in un ttk.Notebook.

    Titolo e chiusura della finestra sono affare di chi la ospita, che prima di
    uscire deve chiamare chiudi() per fermare i lavori in corso e salvare
    l'ultimo libro.
    """

    def __init__(self, master):
        super().__init__(master, padding=8)
        self.cfg = Config()
        self.fonts: list[FontEntry] = []
        self.fam_map: dict[str, list[FontEntry]] = {}
        self.vars: dict[str, tk.Variable] = {}
        self._blocca = False
        self._drag = None
        self._rect_map: list[tuple[int, float, float, float, float]] = []
        self._zoom = 1.0                    # 1 = foglio intero; vedi PX_PER_MM_MAX
        self._pan = [0.0, 0.0]              # spostamento della vista, in pixel
        self._pan_da = None                 # (x, y, pan_x, pan_y) mentre si sposta la vista
        self._drag_rett = -1                # posizione in _rect_map del pezzo trascinato
        self._guide = None                  # ([x mm], [y mm]) delle linee guida della calamita
        self._calamita = tk.BooleanVar(master=self, value=True)
        self._build()
        self._carica(ULTIMO, silenzioso=True)
        self._job = self.after(120, lambda: self._avvia_scansione())

    # ---------- helper widget ----------
    def _v(self, key, default):
        if isinstance(default, bool):
            var = tk.BooleanVar(value=default)
        elif isinstance(default, int):
            var = tk.IntVar(value=default)
        elif isinstance(default, float):
            var = tk.DoubleVar(value=default)
        else:
            var = tk.StringVar(value=default)
        var.trace_add("write", lambda *_: self._preview())
        self.vars[key] = var
        return var

    @staticmethod
    def _rotella_sul_campo(e):
        """Sopra un campo la rotella scorre il pannello e basta.

        Di suo Tk la usa per cambiare il valore del campo: un numero sale di un
        passo, una tendina passa alla scelta successiva.  Dato che il pannello e'
        scorrevole, chi lo scorre con il puntatore sopra un campo ne cambierebbe il
        valore senza accorgersene (per esempio una base da incollare che compare da
        sola).
        """
        giu = getattr(e, "num", 0) == 5 or getattr(e, "delta", 0) < 0
        w = e.widget
        while w is not None and not isinstance(w, tk.Canvas):
            w = w.master
        if w is not None:
            regione = w.bbox("all")
            if regione and regione[3] > w.winfo_height():
                w.yview_scroll(1 if giu else -1, "units")
        return "break"

    def _senza_rotella(self, campo):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            campo.bind(seq, self._rotella_sul_campo)
        return campo

    def _num(self, parent, label, key, default, riga, incr=0.5, width=7, col=0):
        ttk.Label(parent, text=label).grid(row=riga, column=col, sticky="w",
                                           padx=(0, 6), pady=2)
        self._senza_rotella(
            ttk.Spinbox(parent, textvariable=self._v(key, default), width=width,
                        from_=-9999, to=9999, increment=incr, justify="right")
        ).grid(row=riga, column=col + 1, sticky="w", pady=2)

    def _chk(self, parent, label, key, default, riga, span=2, col=0):
        ttk.Checkbutton(parent, text=label, variable=self._v(key, default)
                        ).grid(row=riga, column=col, columnspan=span,
                               sticky="w", pady=2)

    def _combo(self, parent, label, key, default, valori, riga, width=20, col=0):
        ttk.Label(parent, text=label).grid(row=riga, column=col, sticky="w",
                                           padx=(0, 6), pady=2)
        cb = self._senza_rotella(
            ttk.Combobox(parent, textvariable=self._v(key, default),
                         values=valori, width=width, state="readonly"))
        cb.grid(row=riga, column=col + 1, columnspan=3, sticky="w", pady=2)
        return cb

    def _entry(self, parent, label, key, default, riga, width=26):
        ttk.Label(parent, text=label).grid(row=riga, column=0, sticky="w",
                                           padx=(0, 6), pady=2)
        ttk.Entry(parent, textvariable=self._v(key, default), width=width
                  ).grid(row=riga, column=1, columnspan=3, sticky="we", pady=2)

    # ---------- costruzione ----------
    def _scheda(self, nb, titolo, padding=8):
        """Scheda con barra di scorrimento: utile su schermi bassi."""
        cont = ttk.Frame(nb)
        nb.add(cont, text=titolo)
        cv = tk.Canvas(cont, highlightthickness=0, borderwidth=0, width=320)
        sb = ttk.Scrollbar(cont, orient="vertical", command=cv.yview)
        interno = ttk.Frame(cv, padding=padding)
        fin = cv.create_window((0, 0), window=interno, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        def su_interno(_e=None):
            cv.configure(scrollregion=cv.bbox("all"))
            cv.configure(width=max(interno.winfo_reqwidth(), 260))

        interno.bind("<Configure>", su_interno)
        cv.bind("<Configure>", lambda e: cv.itemconfigure(fin, width=e.width))

        def rotella(e):
            giu = getattr(e, "num", 0) == 5 or getattr(e, "delta", 0) < 0
            if cv.bbox("all") and cv.bbox("all")[3] > cv.winfo_height():
                cv.yview_scroll(1 if giu else -1, "units")

        def attiva(_e=None):
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                cv.bind_all(seq, rotella)

        def disattiva(_e=None):
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                cv.unbind_all(seq)

        cv.bind("<Enter>", attiva)
        cv.bind("<Leave>", disattiva)
        return interno

    def _build(self):
        left = ttk.Frame(self)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        nb = ttk.Notebook(left)
        nb.pack(fill="both", expand=True)
        t_cont = self._scheda(nb, "Libro")
        t_font = self._scheda(nb, "Font")
        t_tas = self._scheda(nb, "Tasselli", padding=6)
        t_dec = self._scheda(nb, "Decoro")
        t_fog = self._scheda(nb, "Foglio e taglio")
        t_dor = self._scheda(nb, "Doratura e prove")

        # ---- Libro ----
        r = 0
        self._entry(t_cont, "Autore:", "autore", self.cfg.autore, r); r += 1
        ttk.Label(t_cont, text="Titolo (una riga per rigo):").grid(
            row=r, column=0, columnspan=4, sticky="w", pady=(6, 0)); r += 1
        self.txt = tk.Text(t_cont, width=32, height=4, undo=True, wrap="none")
        self.txt.grid(row=r, column=0, columnspan=4, sticky="we")
        self.txt.insert("1.0", self.cfg.titolo)
        self.txt.bind("<<Modified>>", self._on_text)
        r += 1
        self._entry(t_cont, "Riga extra:", "extra", self.cfg.extra, r); r += 1

        ttk.Separator(t_cont).grid(row=r, column=0, columnspan=4, sticky="we",
                                   pady=8); r += 1
        ttk.Label(t_cont, text="Corpi (altezza maiuscole)",
                  font=("TkDefaultFont", 9, "bold")).grid(
            row=r, column=0, columnspan=4, sticky="w"); r += 1
        self._num(t_cont, "Titolo (mm):", "cap_titolo_mm",
                  self.cfg.cap_titolo_mm, r, incr=0.25); r += 1
        self._num(t_cont, "Autore (mm):", "cap_autore_mm",
                  self.cfg.cap_autore_mm, r, incr=0.25); r += 1
        self._num(t_cont, "Extra (mm):", "cap_extra_mm",
                  self.cfg.cap_extra_mm, r, incr=0.25); r += 1
        self._num(t_cont, "Interlinea (x maiusc.):", "interlinea",
                  self.cfg.interlinea, r, incr=0.1); r += 1
        self._num(t_cont, "Spazio fra blocchi (mm):", "spazio_blocchi_mm",
                  self.cfg.spazio_blocchi_mm, r, incr=0.5); r += 1
        self._num(t_cont, "Spaz. lettere titolo (mm):", "tracking_titolo_mm",
                  self.cfg.tracking_titolo_mm, r, incr=0.05); r += 1
        self._num(t_cont, "Spaz. lettere autore (mm):", "tracking_autore_mm",
                  self.cfg.tracking_autore_mm, r, incr=0.05); r += 1
        self._chk(t_cont, "titolo tutto maiuscolo", "maiusc_titolo",
                  self.cfg.maiusc_titolo, r, span=4); r += 1
        self._chk(t_cont, "autore tutto maiuscolo", "maiusc_autore",
                  self.cfg.maiusc_autore, r, span=4); r += 1
        self._combo(t_cont, "Allineamento:", "allineamento",
                    self.cfg.allineamento, ["sinistra", "centro", "destra"],
                    r, width=12); r += 1
        self._combo(t_cont, "Riferimento verticale:", "rif_verticale",
                    self.cfg.rif_verticale, RIF_VERTICALI, r, width=18); r += 1
        self._chk(t_cont, "centratura ottica orizzontale", "centratura_ottica",
                  self.cfg.centratura_ottica, r, span=4); r += 1
        self._chk(t_cont, "riduci il corpo se il testo non entra", "adatta",
                  self.cfg.adatta, r, span=4); r += 1
        self._chk(t_cont, "filetto fra autore e titolo", "filetto",
                  self.cfg.filetto, r, span=4); r += 1
        self._num(t_cont, "Filetto: spessore (mm):", "filetto_spessore_mm",
                  self.cfg.filetto_spessore_mm, r, incr=0.05); r += 1
        self._num(t_cont, "Filetto: larghezza (%):", "filetto_larghezza_perc",
                  self.cfg.filetto_larghezza_perc, r, incr=5); r += 1



        # ---- Font ----
        r = 0
        ttk.Label(t_font, text="Il font vale per tutti i tasselli; i tagli\n"
                               "per ruolo si applicano dentro la famiglia\n"
                               "scelta qui.", foreground="#555").grid(
            row=r, column=0, columnspan=4, sticky="w", pady=(0, 8)); r += 1
        ttk.Label(t_font, text="Filtro font:").grid(row=r, column=0, sticky="w")
        self.var_filtro = tk.StringVar()
        self.var_filtro.trace_add("write", lambda *_: self._filtra())
        ttk.Entry(t_font, textvariable=self.var_filtro, width=18).grid(
            row=r, column=1, columnspan=3, sticky="we"); r += 1
        ttk.Label(t_font, text="Famiglia:").grid(row=r, column=0, sticky="w")
        self.cb_fam = self._senza_rotella(ttk.Combobox(t_font, width=24, state="readonly"))
        self.cb_fam.grid(row=r, column=1, columnspan=3, sticky="we", pady=2)
        self.cb_fam.bind("<<ComboboxSelected>>", lambda e: self._stili()); r += 1
        ttk.Label(t_font, text="Stile:").grid(row=r, column=0, sticky="w")
        self.cb_sty = self._senza_rotella(ttk.Combobox(t_font, width=24, state="readonly"))
        self.cb_sty.grid(row=r, column=1, columnspan=3, sticky="we", pady=2)
        self.cb_sty.bind("<<ComboboxSelected>>", lambda e: self._stili_ruolo()); r += 1
        self.cb_ruolo = {}
        for ruolo, etich in (("titolo", "Taglio titolo:"),
                             ("autore", "Taglio autore:"),
                             ("extra", "Taglio extra:")):
            ttk.Label(t_font, text=etich).grid(row=r, column=0, sticky="w")
            cb = self._senza_rotella(ttk.Combobox(t_font, width=24, state="readonly"))
            cb.grid(row=r, column=1, columnspan=3, sticky="we", pady=2)
            cb.bind("<<ComboboxSelected>>",
                    lambda e, ru=ruolo: self._usa_taglio(ru))
            self.cb_ruolo[ruolo] = cb
            r += 1
        self.var_otf = tk.BooleanVar(value=False)
        ttk.Checkbutton(t_font, text="mostra .otf (non supportati)",
                        variable=self.var_otf, command=self._filtra).grid(
            row=r, column=0, columnspan=2, sticky="w")
        ttk.Button(t_font, text="File font...", command=self._file_font).grid(
            row=r, column=2, columnspan=2, sticky="w"); r += 1
        self.lbl_font = ttk.Label(t_font, text="(lettura font...)", wraplength=280,
                                  foreground="#555")
        self.lbl_font.grid(row=r, column=0, columnspan=4, sticky="w", pady=(4, 0))

        # ---- Tasselli ----
        inner = ttk.Notebook(t_tas)
        inner.pack(fill="both", expand=True)
        for i, t in enumerate(self.cfg.tasselli):
            f = ttk.Frame(inner, padding=8)
            inner.add(f, text=t.nome)
            p = "t%d_" % i
            rr = 0
            self._chk(f, "usa questo tassello", p + "attivo", t.attivo, rr, span=4)
            rr += 1
            self._num(f, "Larghezza (mm):", p + "larghezza_mm", t.larghezza_mm, rr)
            rr += 1
            self._num(f, "Altezza (mm):", p + "altezza_mm", t.altezza_mm, rr)
            rr += 1
            self._num(f, "Raggio angoli (mm):", p + "raggio_mm", t.raggio_mm, rr,
                      incr=0.25); rr += 1
            self._num(f, "Margine interno (mm):", p + "margine_interno_mm",
                      t.margine_interno_mm, rr, incr=0.25); rr += 1
            etichetta = next(k for k, v in ROTAZIONI.items() if v == t.rotazione)
            self._combo(f, "Rotazione:", p + "rotazione", etichetta,
                        list(ROTAZIONI.keys()), rr, width=20); rr += 1
            self._combo(f, "Contenuto:", p + "composizione", t.composizione,
                        list(COMPOSIZIONI.keys()), rr, width=20); rr += 1
            self._num(f, "Scala corpi (x):", p + "scala", t.scala, rr, incr=0.05)
            rr += 1
            self._combo(f, "Spazio autore/titolo:", p + "spazio_modo",
                        t.spazio_modo, SPAZI, rr, width=20); rr += 1
            self._num(f, "   quantita' (mm):", p + "spazio_mm", t.spazio_mm, rr,
                      incr=0.5); rr += 1
            self._num(f, "Copie:", p + "copie", t.copie, rr, incr=1); rr += 1
            self._chk(f, "cornice stampata su questo tassello", p + "decoro",
                      t.decoro, rr, span=4); rr += 1
            self._num(f, "Base da incollare: sporgenza (mm):", p + "cornice_mm",
                      t.cornice_mm, rr, incr=0.5); rr += 1
            self._num(f, "Ritocco testo X (mm):", p + "dx_mm", t.dx_mm, rr,
                      incr=0.1); rr += 1
            self._num(f, "Ritocco testo Y (mm):", p + "dy_mm", t.dy_mm, rr,
                      incr=0.1); rr += 1
            ttk.Separator(f).grid(row=rr, column=0, columnspan=4, sticky="we",
                                  pady=6); rr += 1
            self._chk(f, "posizione automatica", p + "auto", t.auto, rr, span=4)
            rr += 1
            self._num(f, "X da sinistra (mm):", p + "x_mm", t.x_mm, rr, incr=1)
            rr += 1
            self._num(f, "Y dall'alto (mm):", p + "y_mm", t.y_mm, rr, incr=1)
            rr += 1
            ttk.Label(f, text="Con la posizione libera puoi trascinare\n"
                              "il tassello nell'anteprima.",
                      foreground="#555").grid(row=rr, column=0, columnspan=4,
                                              sticky="w", pady=(6, 0)); rr += 1
            ttk.Separator(f).grid(row=rr, column=0, columnspan=4, sticky="we",
                                  pady=6); rr += 1
            ttk.Label(f, text="Posizione nelle serie ripetute",
                      font=("TkDefaultFont", 9, "bold")).grid(
                row=rr, column=0, columnspan=4, sticky="w"); rr += 1
            ttk.Label(f, text="Indipendente per ogni serie: lasciando\n"
                             "'automatica' segue il layout di riferimento;\n"
                             "trascinando questo pezzo in una serie (2, 3\n"
                             "o 4) nell'anteprima si sposta solo lui, senza\n"
                             "toccare le altre serie ne' gli altri tasselli.",
                      foreground="#555").grid(row=rr, column=0, columnspan=4,
                                              sticky="w", pady=(0, 4)); rr += 1
            for k in (2, 3, 4):
                self._chk(f, "Serie %d: posizione automatica" % k,
                          p + "serie%d_auto" % k, getattr(t, "serie%d_auto" % k),
                          rr, span=4); rr += 1
                self._num(f, "   X da sinistra (mm):", p + "serie%d_x_mm" % k,
                          getattr(t, "serie%d_x_mm" % k), rr, incr=1); rr += 1
                self._num(f, "   Y dall'alto (mm):", p + "serie%d_y_mm" % k,
                          getattr(t, "serie%d_y_mm" % k), rr, incr=1); rr += 1

        # ---- Decoro ----
        r = 0
        ttk.Label(t_dec, text="Cornice stampata",
                  font=("TkDefaultFont", 9, "bold")).grid(
            row=r, column=0, columnspan=4, sticky="w"); r += 1
        ttk.Label(t_dec, text="Viene stampata in nero insieme al testo,\n"
                              "quindi in doratura diventa oro anche lei.",
                  foreground="#555").grid(row=r, column=0, columnspan=4,
                                          sticky="w", pady=(0, 6)); r += 1
        self._combo(t_dec, "Modello:", "decoro_modello", self.cfg.decoro_modello,
                    DECORI, r, width=24); r += 1
        self._num(t_dec, "Rientro dal bordo (mm):", "decoro_rientro_mm",
                  self.cfg.decoro_rientro_mm, r, incr=0.25); r += 1
        self._num(t_dec, "Spessore filetto (mm):", "decoro_spessore_mm",
                  self.cfg.decoro_spessore_mm, r, incr=0.05); r += 1
        self._num(t_dec, "Spessore secondario (mm):", "decoro_spessore2_mm",
                  self.cfg.decoro_spessore2_mm, r, incr=0.05); r += 1
        self._num(t_dec, "Distanza fra i filetti (mm):", "decoro_distanza_mm",
                  self.cfg.decoro_distanza_mm, r, incr=0.1); r += 1
        self._num(t_dec, "Sporgenza agli incroci (mm):", "decoro_sporgenza_mm",
                  self.cfg.decoro_sporgenza_mm, r, incr=0.25); r += 1
        self._num(t_dec, "Lunghezza cantonali (mm):", "decoro_angolo_mm",
                  self.cfg.decoro_angolo_mm, r, incr=0.5); r += 1
        self._num(t_dec, "Diametro punti (mm):", "decoro_punto_mm",
                  self.cfg.decoro_punto_mm, r, incr=0.1); r += 1
        self._num(t_dec, "Fleuron: dimensione foglie (mm):", "decoro_fleuron_dim_mm",
                  self.cfg.decoro_fleuron_dim_mm, r, incr=0.5); r += 1
        self._chk(t_dec, "fleuron: con il ricciolo", "decoro_fleuron_ricciolo",
                  self.cfg.decoro_fleuron_ricciolo, r, span=4); r += 1
        self._chk(t_dec, "fleuron: anche al centro dei lati lunghi", "decoro_fleuron_centrale",
                  self.cfg.decoro_fleuron_centrale, r, span=4); r += 1
        # cornice bitmap: file dei blocchetti
        ttk.Label(t_dec, text="Cornice bitmap: file dei blocchetti").grid(
            row=r, column=0, sticky="w", padx=(0, 6), pady=2)
        ttk.Button(t_dec, text="Scegli...", command=self._file_bitmap).grid(
            row=r, column=1, sticky="w", pady=2); r += 1
        self._entry(t_dec, "   Nome comune:", "decoro_bitmap_prefisso",
                    self.cfg.decoro_bitmap_prefisso, r, width=30); r += 1
        self._num(t_dec, "   Risoluzione PNG (dpi, 0 = dal file):", "decoro_bitmap_dpi",
                  self.cfg.decoro_bitmap_dpi, r, incr=50); r += 1
        self._chk(t_dec, "   se gli angoli non stanno, rimpicciolisci i blocchetti",
                  "decoro_bitmap_riduci", self.cfg.decoro_bitmap_riduci, r, span=4); r += 1
        self._chk(t_dec, "   completa con porzioni di blocchetto (niente vuoti)",
                  "decoro_bitmap_taglio", self.cfg.decoro_bitmap_taglio, r, span=4); r += 1
        self.lbl_bitmap = ttk.Label(t_dec, text="", foreground="#555", justify="left")
        self.lbl_bitmap.grid(row=r, column=0, columnspan=4, sticky="w"); r += 1
        ttk.Label(t_dec, text="Scegli UNO qualsiasi dei PNG: gli altri si trovano da\n"
                              "soli (stesso nome, suffisso ul ur ll lr = angoli; hu hl =\n"
                              "tratti alto/basso; vl vr = tratti sinistro/destro).\n"
                              "Se ci sono anche hu1 hu2 hl1 hl2 vl1 vl2 vr1 vr2 (16\n"
                              "blocchetti) hu hl vl vr stanno al centro del lato e i\n"
                              "tratti 1 e 2 riempiono le due meta'.\n"
                              "I blocchetti non si scalano: la misura stampata dipende\n"
                              "dai dpi, salvo la riduzione (solo in rimpicciolimento) che\n"
                              "scatta nei tasselli dove gli angoli non stanno. Senza\n"
                              "riduzione gli angoli vengono tagliati.",
                  foreground="#555").grid(row=r, column=0, columnspan=4,
                                          sticky="w", pady=(0, 4)); r += 1
        self._num(t_dec, "Bordo continuo: rientro (mm):", "decoro_continuo_rientro_mm",
                  self.cfg.decoro_continuo_rientro_mm, r, incr=0.5); r += 1
        self._num(t_dec, "Greca: larghezza fascia (mm):", "decoro_continuo_fascia_mm",
                  self.cfg.decoro_continuo_fascia_mm, r, incr=0.5); r += 1
        self._num(t_dec, "Greca/dentelli: modulo (mm):", "decoro_continuo_modulo_mm",
                  self.cfg.decoro_continuo_modulo_mm, r, incr=0.5); r += 1
        self._num(t_dec, "Festone: raggio archi (mm):", "decoro_continuo_raggio_mm",
                  self.cfg.decoro_continuo_raggio_mm, r, incr=0.5); r += 1
        self._num(t_dec, "Dentelli: altezza denti (mm):", "decoro_continuo_altezza_mm",
                  self.cfg.decoro_continuo_altezza_mm, r, incr=0.5); r += 1
        ttk.Label(t_dec, text="Greca, festone e dentelli corrono lungo tutto il\n"
                              "perimetro, non solo agli angoli: usano lo stesso\n"
                              "campo Spessore filetto e lo stesso avviso di doratura\n"
                              "degli altri modelli.",
                  foreground="#555").grid(row=r, column=0, columnspan=4,
                                          sticky="w", pady=(0, 4)); r += 1
        self._chk(t_dec, "il testo si scosta dalla cornice", "decoro_rispetta",
                  self.cfg.decoro_rispetta, r, span=4); r += 1
        ttk.Label(t_dec, text="Ogni tassello puo' escluderla dalla propria\n"
                              "scheda. Le basi da incollare non la ricevono.",
                  foreground="#555").grid(row=r, column=0, columnspan=4,
                                          sticky="w", pady=(8, 0))

        # ---- Foglio e taglio ----
        r = 0
        self._combo(t_fog, "Formato:", "formato", self.cfg.formato,
                    list(PAGE_SIZES.keys()), r, width=20); r += 1
        self.vars["formato"].trace_add("write", lambda *_: self._formato())
        self._num(t_fog, "Larghezza foglio (mm):", "pagina_w_mm",
                  self.cfg.pagina_w_mm, r); r += 1
        self._num(t_fog, "Altezza foglio (mm):", "pagina_h_mm",
                  self.cfg.pagina_h_mm, r); r += 1
        self._chk(t_fog, "orizzontale", "orizzontale", self.cfg.orizzontale, r)
        r += 1
        self._num(t_fog, "Margine (mm):", "margine_mm", self.cfg.margine_mm, r)
        r += 1
        self._num(t_fog, "Distanza fra tasselli (mm):", "gap_mm",
                  self.cfg.gap_mm, r); r += 1
        ttk.Separator(t_fog).grid(row=r, column=0, columnspan=4, sticky="we",
                                  pady=8); r += 1
        ttk.Label(t_fog, text="Serie multiple sul foglio",
                  font=("TkDefaultFont", 9, "bold")).grid(
            row=r, column=0, columnspan=4, sticky="w"); r += 1
        ttk.Label(t_fog, text="Ripete l'intero set di tasselli attivi piu'\n"
                             "volte sullo stesso foglio: pezzi di scorta e\n"
                             "prove, senza sprecare altri fogli.",
                  foreground="#555").grid(row=r, column=0, columnspan=4,
                                          sticky="w", pady=(0, 6)); r += 1
        self._num(t_fog, "Numero di serie (1-4):", "serie", self.cfg.serie, r,
                  incr=1); r += 1
        self._combo(t_fog, "Disposizione:", "serie_modo", self.cfg.serie_modo,
                    ["automatica", "manuale"], r, width=16); r += 1
        self._num(t_fog, "Distanza fra le serie (mm):", "serie_gap_mm",
                  self.cfg.serie_gap_mm, r, incr=1); r += 1
        ttk.Label(t_fog, text="Automatica: le serie si impilano da sole.\n"
                             "Manuale: nella scheda Tasselli, ogni pezzo di\n"
                             "ogni serie si trascina uno alla volta in\n"
                             "anteprima (o si indica uno scostamento preciso).",
                  foreground="#555").grid(row=r, column=0, columnspan=4,
                                          sticky="w", pady=(0, 4)); r += 1
        ttk.Separator(t_fog).grid(row=r, column=0, columnspan=4, sticky="we",
                                  pady=8); r += 1
        ttk.Label(t_fog, text="Bordi di ritaglio",
                  font=("TkDefaultFont", 9, "bold")).grid(
            row=r, column=0, columnspan=4, sticky="w"); r += 1
        self._combo(t_fog, "Stile:", "bordo_stile", self.cfg.bordo_stile,
                    BORDER_STYLES, r); r += 1
        self._num(t_fog, "Spessore linea (mm):", "bordo_spessore_mm",
                  self.cfg.bordo_spessore_mm, r, incr=0.05); r += 1
        self._num(t_fog, "Grigio (0=nero,1=bianco):", "bordo_grigio",
                  self.cfg.bordo_grigio, r, incr=0.05); r += 1
        self._num(t_fog, "Tratto (mm):", "bordo_tratto_mm",
                  self.cfg.bordo_tratto_mm, r, incr=0.2); r += 1
        self._num(t_fog, "Crocini: distanza (mm):", "crocini_offset_mm",
                  self.cfg.crocini_offset_mm, r, incr=0.25); r += 1
        self._num(t_fog, "Crocini: lunghezza (mm):", "crocini_lung_mm",
                  self.cfg.crocini_lung_mm, r, incr=0.5); r += 1
        self._num(t_fog, "Linee estese: distanza (mm):", "linee_offset_mm",
                  self.cfg.linee_offset_mm, r, incr=0.25); r += 1
        self._num(t_fog, "Linee estese: lunghezza (mm):", "linee_lung_mm",
                  self.cfg.linee_lung_mm, r, incr=1.0); r += 1
        ttk.Label(t_fog, text="Le linee estese prolungano i bordi di ogni pezzo fuori dagli\n"
                              "angoli, per allinearlo alla lama di una taglierina. Con lo\n"
                              "stile \"linee estese\" si stampano da sole, senza il contorno\n"
                              "del pezzo. Restano sempre sul margine del proprio pezzo: la\n"
                              "distanza fra i pezzi sale da sola se serve (2 x (distanza +\n"
                              "lunghezza)).",
                  foreground="#555").grid(row=r, column=0, columnspan=4,
                                          sticky="w", pady=(0, 4)); r += 1
        self._chk(t_fog, "guide su una seconda pagina registrata",
                  "bordo_pagina_separata", self.cfg.bordo_pagina_separata, r,
                  span=4); r += 1
        self._chk(t_fog, "crocini di registro agli angoli", "crocini_registro",
                  self.cfg.crocini_registro, r, span=4); r += 1

        # ---- Doratura e prove ----
        r = 0
        ttk.Label(t_dor, text="Doratura da toner",
                  font=("TkDefaultFont", 9, "bold")).grid(
            row=r, column=0, columnspan=4, sticky="w"); r += 1
        self._chk(t_dor, "solo nero pieno (niente grigi)", "solo_nero",
                  self.cfg.solo_nero, r, span=4); r += 1
        self._num(t_dor, "Ingrossamento testo (mm):", "ingrosso_mm",
                  self.cfg.ingrosso_mm, r, incr=0.02); r += 1
        ttk.Label(t_dor, text="0,02-0,08 mm depositano piu' toner e aiutano\n"
                             "la presa della foglia sui corpi piccoli.",
                  foreground="#555").grid(row=r, column=0, columnspan=4,
                                          sticky="w", pady=(0, 8)); r += 1
        ttk.Separator(t_dor).grid(row=r, column=0, columnspan=4, sticky="we",
                                  pady=6); r += 1
        ttk.Label(t_dor, text="Pagina di prova",
                  font=("TkDefaultFont", 9, "bold")).grid(
            row=r, column=0, columnspan=4, sticky="w"); r += 1
        self._chk(t_dor, "aggiungi pagina con corpi crescenti", "prova",
                  self.cfg.prova, r, span=4); r += 1
        self._num(t_dor, "Da (mm):", "prova_da_mm", self.cfg.prova_da_mm, r,
                  incr=0.25); r += 1
        self._num(t_dor, "A (mm):", "prova_a_mm", self.cfg.prova_a_mm, r,
                  incr=0.25); r += 1
        self._num(t_dor, "Passo (mm):", "prova_passo_mm",
                  self.cfg.prova_passo_mm, r, incr=0.05); r += 1
        ttk.Label(t_dor, text="La prova usa il primo tassello attivo e fa\n"
                             "variare il corpo del titolo (gli altri corpi\n"
                             "seguono in proporzione).",
                  foreground="#555").grid(row=r, column=0, columnspan=4,
                                          sticky="w", pady=(6, 0))

        # ---- pulsanti ----
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Anteprima PDF", command=self.anteprima).pack(side="left")
        ttk.Button(bar, text="Genera PDF...", command=self.genera).pack(
            side="left", padx=4)
        ttk.Button(bar, text="Salva libro...", command=self.salva_progetto).pack(
            side="left")
        ttk.Button(bar, text="Apri...", command=self.apri_progetto).pack(
            side="left", padx=4)

        # ---- anteprima ----
        ttk.Label(right, text="Anteprima del foglio "
                              "(trascina i tasselli a posizione libera)").pack(
            anchor="w")
        barra = ttk.Frame(right)
        barra.pack(fill="x", pady=(2, 0))
        b_meno = ttk.Button(barra, text="\u2212", width=3,
                            command=lambda: self._zoom_intorno(1 / FATTORE_ZOOM_PULSANTI))
        b_piu = ttk.Button(barra, text="+", width=3,
                           command=lambda: self._zoom_intorno(FATTORE_ZOOM_PULSANTI))
        b_adatta = ttk.Button(barra, text="Adatta", command=self._zoom_adatta)
        for b in (b_meno, b_piu, b_adatta):
            b.pack(side="left", padx=(0, 3))
        self.lbl_zoom = ttk.Label(barra, text="Zoom \u00d71", width=11)
        self.lbl_zoom.pack(side="left", padx=(6, 0))
        chk_calamita = ttk.Checkbutton(barra, text="Calamita ai bordi",
                                       variable=self._calamita)
        chk_calamita.pack(side="right")
        Suggerimento(b_piu, "Ingrandisci. Con la rotella del mouse sull'anteprima "
                            "ingrandisci o riduci attorno al puntatore.")
        Suggerimento(b_meno, "Riduci.")
        Suggerimento(b_adatta, "Mostra il foglio intero.")
        Suggerimento(self.lbl_zoom, "Ingrandimento rispetto al foglio intero. Da "
                                    "ingrandita, la vista si sposta trascinando lo "
                                    "sfondo (o con il tasto destro o centrale).")
        Suggerimento(chk_calamita,
                     "Mentre trascini un pezzo, bordi e centro si agganciano ai bordi e "
                     "ai centri degli altri pezzi e ai margini, con una linea guida. "
                     "Ingrandendo l'aggancio si fa piu' fine. Tieni premuto Ctrl per "
                     "escluderlo al volo.")
        self.canvas = tk.Canvas(right, bg="#e9e9e9", width=420, height=420,
                                highlightthickness=1, highlightbackground="#bbb")
        self.canvas.pack(fill="both", expand=True, pady=(2, 4))
        self.canvas.bind("<Configure>", lambda e: self._preview())
        self.canvas.bind("<Button-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_fine)
        # rotella: zoom.  Linux con Tk 8.6 manda Button-4/5, gli altri MouseWheel.
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind(seq, self._zoom_rotella)
        # tasto centrale e destro: sposta la vista
        for tasto in (2, 3):
            self.canvas.bind("<ButtonPress-%d>" % tasto, self._pan_start)
            self.canvas.bind("<B%d-Motion>" % tasto, self._pan_move)
            self.canvas.bind("<ButtonRelease-%d>" % tasto, self._drag_fine)
        self.lbl_info = ttk.Label(right, text="", wraplength=430, justify="left")
        self.lbl_info.pack(anchor="w")

    # ---------- font ----------
    def _avvia_scansione(self, force=False):
        self.lbl_font.config(text="Lettura dei font di sistema...")

        def worker():
            try:
                f = scan_fonts(use_cache=not force)
            except Exception:
                f = []
            self.after(0, lambda: self._fine_scansione(f))
        threading.Thread(target=worker, daemon=True).start()

    def _fine_scansione(self, fonts):
        self.fonts = fonts
        target = (self.cfg.font_path, self.cfg.font_index)
        self._filtra()
        self._seleziona(target)

    def _filtra(self):
        f = self.var_filtro.get().strip().lower()
        self.fam_map = {}
        for e in self.fonts:
            if not self.var_otf.get() and not e.supported:
                continue
            if f and f not in e.family.lower():
                continue
            self.fam_map.setdefault(e.family, []).append(e)
        fam = sorted(self.fam_map, key=str.lower)
        self.cb_fam["values"] = fam
        if fam:
            if self.cb_fam.get() not in fam:
                pref = [x for x in ("Times New Roman", "EB Garamond", "Garamond",
                                    "Liberation Serif", "DejaVu Serif", "Georgia")
                        if x in fam]
                self.cb_fam.set(pref[0] if pref else fam[0])
            self._stili()

    def _stili(self):
        voci = self.fam_map.get(self.cb_fam.get(), [])
        stili = [e.style for e in voci]
        self.cb_sty["values"] = stili
        if stili:
            if self.cb_sty.get() not in stili:
                pref = [s for s in stili if s.lower() in ("regular", "book", "roman")]
                self.cb_sty.set(pref[0] if pref else stili[0])
            self._usa_font()
            self._riallinea_tagli()

    def _stili_ruolo(self):
        """Dopo il cambio di stile principale: riallinea i tagli per ruolo."""
        self._usa_font()
        self._riallinea_tagli()

    def _riallinea_tagli(self):
        voci = self.fam_map.get(self.cb_fam.get(), [])
        stili = [e.style for e in voci]
        for ruolo, cb in getattr(self, "cb_ruolo", {}).items():
            cb["values"] = ["come principale"] + stili
            etich = getattr(self.cfg, "font_%s_label" % ruolo, "")
            cb.set(etich if etich and etich in stili else "come principale")
            self._usa_taglio(ruolo, aggiorna=False)
        self._preview()

    def _usa_taglio(self, ruolo, aggiorna=True):
        scelta = self.cb_ruolo[ruolo].get()
        voce = next((e for e in self.fam_map.get(self.cb_fam.get(), [])
                     if e.style == scelta), None)
        setattr(self.cfg, "font_%s_path" % ruolo, voce.path if voce else "")
        setattr(self.cfg, "font_%s_index" % ruolo, voce.index if voce else 0)
        setattr(self.cfg, "font_%s_label" % ruolo, voce.style if voce else "")
        if voce and not voce.supported:
            self.lbl_font.config(text="%s   [.otf NON supportato]" % voce.path)
        if aggiorna:
            self._preview()

    def _usa_font(self):
        for e in self.fam_map.get(self.cb_fam.get(), []):
            if e.style == self.cb_sty.get():
                self.cfg.font_path, self.cfg.font_index = e.path, e.index
                self.cfg.font_label = "%s %s" % (e.family, e.style)
                nota = "" if e.supported else "   [.otf NON supportato]"
                self.lbl_font.config(text="%s%s" % (e.path, nota))
                break
        self._preview()

    def _seleziona(self, target):
        path, index = target
        if not path:
            return
        rp = os.path.realpath(path)
        voce = next((e for e in self.fonts
                     if os.path.realpath(e.path) == rp and e.index == index), None)
        if voce is None:
            self.cfg.font_path, self.cfg.font_index = path, index
            self.lbl_font.config(text=path)
            return
        if voce.family not in self.fam_map:
            self.var_filtro.set("")
            if not voce.supported:
                self.var_otf.set(True)
            self._filtra()
        if voce.family in self.fam_map:
            self.cb_fam.set(voce.family)
            self._stili()
            if voce.style in tuple(self.cb_sty["values"]):
                self.cb_sty.set(voce.style)
                self._usa_font()

    def _file_font(self):
        p = filedialog.askopenfilename(
            title="Scegli un file font",
            filetypes=[("Font TrueType", "*.ttf *.ttc"), ("Tutti", "*.*")])
        if p:
            self.cfg.font_path, self.cfg.font_index = p, 0
            self.cfg.font_label = os.path.basename(p)
            self.lbl_font.config(text=p)
            self._preview()

    # ---------- configurazione ----------
    def _on_text(self, _e=None):
        if self.txt.edit_modified():
            self.txt.edit_modified(False)
            self._preview()

    def _leggi_in(self, obj, prefisso=""):
        for f in fields(obj):
            key = prefisso + f.name
            if key not in self.vars:
                continue
            try:
                val = self.vars[key].get()
            except tk.TclError:
                continue
            cur = getattr(obj, f.name)
            try:
                if f.name == "rotazione":
                    val = ROTAZIONI.get(str(val), 0)
                elif isinstance(cur, bool):
                    val = bool(val)
                elif isinstance(cur, int):
                    val = int(float(val))
                elif isinstance(cur, float):
                    val = float(str(val).replace(",", "."))
            except (TypeError, ValueError):
                continue
            setattr(obj, f.name, val)

    def leggi_config(self) -> Config:
        car = {f.name: getattr(self.cfg, f.name) for f in fields(Config)
               if f.name.startswith("font_")}
        cfg = Config(tasselli=[replace(t) for t in self.cfg.tasselli], **car)
        self._leggi_in(cfg)
        cfg.titolo = self.txt.get("1.0", "end-1c")
        for i, t in enumerate(cfg.tasselli):
            self._leggi_in(t, "t%d_" % i)
        return cfg

    def _formato(self):
        dim = PAGE_SIZES.get(self.vars["formato"].get())
        if dim:
            self.vars["pagina_w_mm"].set(dim[0])
            self.vars["pagina_h_mm"].set(dim[1])

    # ---------- anteprima ----------
    def _preview(self):
        if self._blocca or not hasattr(self, "canvas"):
            return
        try:
            cfg = self.leggi_config()
        except Exception:
            return
        cv = self.canvas
        cv.delete("all")
        pw, ph = cfg.pagina_pt()
        if pw <= 0 or ph <= 0:
            return
        s, ox, oy, pw, ph = self._canvas_scale(cfg)
        self.lbl_zoom.config(text=("Zoom \u00d7%.1f" % self._zoom).replace(".", ",")
                             if self._zoom > 1.0 else "Zoom \u00d71")

        def X(x): return ox + x * s

        def Y(y): return oy + (ph - y) * s

        cv.create_rectangle(X(0), Y(ph), X(pw), Y(0), fill="white", outline="#999")
        mar = cfg.margine_mm * mm
        cv.create_rectangle(X(mar), Y(ph - mar), X(pw - mar), Y(mar),
                            outline="#ddd", dash=(3, 3))

        fam = self.cb_fam.get() or "Times"
        try:
            fonti = risolvi_fonti(cfg) if cfg.font_path and \
                os.path.isfile(cfg.font_path) else {"_base": ("Helvetica", 0.72, None)}
            ratio = fonti["_base"][1]
        except Exception:
            fonti, ratio = {"_base": ("Helvetica", 0.72, None)}, 0.72

        self._rect_map = []
        avvisi = []
        piazzati = disponi(cfg)
        # Blu = si stampa.  Il rettangolo di ogni pezzo e' blu solo se lo stile ha il
        # contorno: altrimenti e' un semplice ingombro grigio (per vedere e trascinare
        # i pezzi), e in blu restano solo le linee che il PDF disegna davvero.
        colore_bordo = "#3a6ea5" if cfg.bordo_stile != "nessuno" else "#c8c8c8"
        colore_rett = "#3a6ea5" if "contorno" in cfg.bordo_stile else "#c8c8c8"
        for t, x, y, serie_idx, origine in piazzati:
            w, h = t.larghezza_mm * mm, t.altezza_mm * mm
            idx = cfg.tasselli.index(t) if (serie_idx == 1 and t in cfg.tasselli) else -1
            if "crocini" in cfg.bordo_stile:
                for x1, y1, x2, y2 in segmenti_crocini(x, y, w, h, cfg):
                    cv.create_line(X(x1), Y(y1), X(x2), Y(y2), fill=colore_bordo)
            cv.create_rectangle(X(x), Y(y + h), X(x + w), Y(y), outline=colore_rett,
                                width=1)
            self._rect_map.append((idx, x, y, w, h, serie_idx, origine))
            if t.composizione == VUOTO:
                cv.create_text(X(x + w / 2), Y(y + h / 2), text=t.nome,
                               fill="#9a9a9a", font=("TkDefaultFont", 7))
            if getattr(t, "decoro", True):
                self._decoro_preview(cv, X, Y, x, y, w, h, t, cfg)
            rot = int(t.rotazione) % 360
            bw, bh = (w, h) if rot in (0, 180) else (h, w)
            pad = padding_utile(cfg, t)
            righe, filetti, over = componi_blocco(
                cfg, t, righe_tassello(cfg, t), fonti,
                max(bw - 2 * pad, 1), max(bh - 2 * pad, 1))
            if over:
                avvisi.append(t.nome)
            cx, cy = x + w / 2.0, y + h / 2.0
            a = math.radians(rot)
            for rg in righe:
                lx = rg["x"] + rg["w"] / 2.0
                ly = rg["y"] + rg["cap"] / 2.0
                gx = cx + lx * math.cos(a) - ly * math.sin(a)
                gy = cy + lx * math.sin(a) + ly * math.cos(a)
                px = max(int(rg["size"] * s), 2)
                st = (getattr(cfg, "font_%s_label" % rg["ruolo"], "")
                      or self.cb_sty.get() or "").lower()
                peso = "bold" if any(k in st for k in ("bold", "black", "heavy",
                                                       "semibold")) else "normal"
                incl = "italic" if ("italic" in st or "oblique" in st) else "roman"
                try:
                    f = tkfont.Font(family=fam, size=-px, weight=peso, slant=incl)
                except tk.TclError:
                    f = tkfont.Font(size=-px)
                cv.create_text(X(gx), Y(gy), text=rg["testo"], font=f, angle=rot,
                               fill="black")
            for fy, flw in filetti:
                gx1 = cx + (-flw / 2) * math.cos(a) - fy * math.sin(a)
                gy1 = cy + (-flw / 2) * math.sin(a) + fy * math.cos(a)
                gx2 = cx + (flw / 2) * math.cos(a) - fy * math.sin(a)
                gy2 = cy + (flw / 2) * math.sin(a) + fy * math.cos(a)
                cv.create_line(X(gx1), Y(gy1), X(gx2), Y(gy2), fill="black")

        linee = segmenti_linee_estese(cfg, piazzati)
        for x1, y1, x2, y2 in linee.segmenti:
            cv.create_line(X(x1), Y(y1), X(x2), Y(y2), fill=colore_bordo)

        # linee guida della calamita, solo mentre si trascina
        if self._guide:
            guide_x, guide_y = self._guide
            for g in guide_x:
                cv.create_line(X(g * mm), Y(0), X(g * mm), Y(ph), fill=COLORE_GUIDA,
                               dash=(4, 3))
            for g in guide_y:
                cv.create_line(X(0), Y(g * mm), X(pw), Y(g * mm), fill=COLORE_GUIDA,
                               dash=(4, 3))

        note = []
        if cfg.font_path:
            note.append("Font: %s - cap height %.0f%% del corpo; "
                        "titolo %.2f mm = %.1f pt"
                        % (self.cfg.font_label or "?", ratio * 100,
                           cfg.cap_titolo_mm,
                           cfg.cap_titolo_mm * mm / max(ratio, 0.1)))
        if avvisi:
            note.append("Testo troppo grande in: " + ", ".join(sorted(set(avvisi))))
        if cfg.bordo_stile != "nessuno" and "contorno" not in cfg.bordo_stile:
            note.append("Senza contorno: il rettangolo grigio e' solo l'ingombro del "
                        "pezzo, non si stampa.")
        if linee_estese_attive(cfg) and cfg.gap_mm < distanza_minima_linee_mm(cfg):
            note.append("Linee estese: distanza fra i pezzi portata a %.1f mm."
                        % distanza_minima_linee_mm(cfg))
        note += avvisi_linee(cfg, linee)
        note += avvisi_doratura(cfg)
        self._stato_bitmap(cfg)
        self.lbl_info.config(text="\n".join(note))

    def _stato_bitmap(self, cfg):
        """Sotto il pulsante della cornice bitmap: cosa e' stato trovato e la misura."""
        if not hasattr(self, "lbl_bitmap"):
            return
        if cfg.decoro_modello != DECORO_BITMAP:
            self.lbl_bitmap.config(text="")
            return
        try:
            blocchi = carica_blocchetti(cfg)
            ul = blocchi["ul"]
            self.lbl_bitmap.config(
                text="OK, %d blocchetti di %s*.png\nAngoli %.1f x %.1f mm (%d px)"
                % (len(blocchi), os.path.basename(cfg.decoro_bitmap_prefisso), ul[1] / mm, ul[2] / mm,
                   ul[0].width),
                foreground="#2a7a2a")
        except ValueError as e:
            self.lbl_bitmap.config(text=str(e), foreground="#b03030")

    def _file_bitmap(self):
        """Sceglie uno qualsiasi degli otto PNG: il nome comune si ricava togliendo
        il suffisso del ruolo (ul, ur, ...) e l'estensione."""
        # si parte dalla libreria "cornici" (se c'e'), altrimenti da dove era la cornice in uso
        iniziale = CARTELLA_CORNICI
        if not os.path.isdir(iniziale):
            attuale = os.path.dirname(self.vars["decoro_bitmap_prefisso"].get())
            iniziale = attuale if os.path.isdir(attuale) else os.path.expanduser("~")
        p = filedialog.askopenfilename(
            title="Scegli UNO qualsiasi degli 8 PNG della cornice (es. cornice1_ul.png)",
            initialdir=iniziale,
            filetypes=[("Immagini PNG", "*.png"), ("Tutti", "*.*")])
        if not p:
            return
        base = os.path.splitext(p)[0]
        suffisso = next((r for r in sorted(BITMAP_RUOLI_TUTTI, key=len, reverse=True)
                         if base.lower().endswith(r)), None)
        if suffisso is None:
            messagebox.showwarning(
                APP_NAME, "Il nome del file deve finire con uno di questi suffissi: "
                + ", ".join(BITMAP_RUOLI_TUTTI) + ".")
            return
        prefisso = base[:-len(suffisso)]
        mancanti = [r for r in BITMAP_RUOLI if not os.path.isfile(prefisso + r + ".png")]
        if mancanti:
            messagebox.showwarning(
                APP_NAME, "Mancano questi file accanto a quello scelto:\n"
                + "\n".join(os.path.basename(prefisso) + r + ".png" for r in mancanti))
            return
        self.vars["decoro_bitmap_prefisso"].set(prefisso)
        self.vars["decoro_modello"].set(DECORO_BITMAP)
        messagebox.showinfo(APP_NAME, "Trovati %d blocchetti:\n%s*.png"
                            % (len(ruoli_presenti(prefisso)), os.path.basename(prefisso)))

    def _bitmap_preview(self, cv, X, Y, x, y, w, h, cfg):
        """La cornice bitmap vera: ogni blocchetto ridimensionato alla scala
        dell'anteprima (solo qui, nel PDF restano com'erano)."""
        try:
            from PIL import ImageTk
            from PIL import Image
            blocchi = carica_blocchetti(cfg)
            pezzi, _motivo = pezzi_bitmap(cfg, x, y, w, h)
        except (ImportError, ValueError):
            return
        cache = self.__dict__.setdefault("_cache_bitmap_tk", {})
        if len(cache) > 300 or self.__dict__.get("_blocchi_tk") is not blocchi:
            cache.clear()                       # cambiati i file o i dpi
        self._blocchi_tk = blocchi
        for ruolo, px, py, pw_, ph_, rit in pezzi:
            im = blocchi[ruolo][0]
            x0, y0, x1, y1 = px, py, px + pw_, py + ph_
            box = (0, 0, im.width, im.height)
            if rit:                             # parte visibile, in pixel dell'immagine
                cx0, cy0 = max(x0, rit[0]), max(y0, rit[1])
                cx1, cy1 = min(x1, rit[0] + rit[2]), min(y1, rit[1] + rit[3])
                if cx1 <= cx0 or cy1 <= cy0:
                    continue
                fx, fy = im.width / pw_, im.height / ph_
                box = (round((cx0 - x0) * fx), round((y1 - cy1) * fy),
                       round((cx1 - x0) * fx), round((y1 - cy0) * fy))
                x0, y0, x1, y1 = cx0, cy0, cx1, cy1
            larg = max(int(round(abs(X(x1) - X(x0)))), 1)
            alt = max(int(round(abs(Y(y0) - Y(y1)))), 1)
            chiave = (id(im), box, larg, alt)
            if chiave not in cache:
                ritagliata = im.crop(box) if box != (0, 0, im.width, im.height) else im
                cache[chiave] = ImageTk.PhotoImage(
                    ritagliata.resize((larg, alt), Image.LANCZOS), master=cv)
            cv.create_image(X(x0), Y(y1), image=cache[chiave], anchor="nw")

    def _decoro_preview(self, cv, X, Y, x, y, w, h, t, cfg):
        """Versione schematica della cornice stampata nell'anteprima."""
        m = cfg.decoro_modello
        if m == "nessuno":
            return
        d = max(cfg.decoro_rientro_mm, 0.0) * mm
        A, B, W, H = x + d, y + d, w - 2 * d, h - 2 * d
        if W <= 0.5 or H <= 0.5:
            return
        col = "#222222"

        def rett(A, B, W, H, dash=None):
            cv.create_rectangle(X(A), Y(B + H), X(A + W), Y(B),
                                outline=col, dash=dash)
        if m == "filetto semplice":
            rett(A, B, W, H)
        elif m == "doppio filetto":
            rett(A, B, W, H)
            k = (cfg.decoro_distanza_mm + cfg.decoro_spessore_mm) * mm
            if W - 2 * k > 0 and H - 2 * k > 0:
                rett(A + k, B + k, W - 2 * k, H - 2 * k)
        elif m == "filetto tratteggiato":
            rett(A, B, W, H, dash=(3, 2))
        elif m == "angoli incrociati":
            s = min(max(cfg.decoro_sporgenza_mm, 0.0) * mm, d)
            for yy in (B, B + H):
                cv.create_line(X(A - s), Y(yy), X(A + W + s), Y(yy), fill=col)
            for xx in (A, A + W):
                cv.create_line(X(xx), Y(B - s), X(xx), Y(B + H + s), fill=col)
        elif m.startswith("cantonali"):
            a = min(max(cfg.decoro_angolo_mm, 1.0) * mm, W / 2.2, H / 2.2)
            for xx, sx in ((A, 1), (A + W, -1)):
                for yy, sy in ((B, 1), (B + H, -1)):
                    cv.create_line(X(xx), Y(yy), X(xx + sx * a), Y(yy), fill=col)
                    cv.create_line(X(xx), Y(yy), X(xx), Y(yy + sy * a), fill=col)
        elif m.startswith("filetto con punti"):
            rett(A, B, W, H)
            r = max(cfg.decoro_punto_mm * mm / 2.0, 0.3)
            for xx in (A, A + W):
                for yy in (B, B + H):
                    cv.create_oval(X(xx - r), Y(yy + r), X(xx + r), Y(yy - r),
                                   fill=col, outline=col)
        elif m == "fleuron agli angoli":
            self._fleuron_preview(cv, X, Y, x, y, w, h, cfg, col)

        elif m == DECORO_BITMAP:
            self._bitmap_preview(cv, X, Y, x, y, w, h, cfg)

        elif m in DECORI_CONTINUI:
            self._bordo_continuo_preview(cv, X, Y, x, y, w, h, cfg, col)

    def _bordo_continuo_preview(self, cv, X, Y, x, y, w, h, cfg, col):
        """Come il ramo DECORI_CONTINUI di _decoro nel motore, ma disegnato come
        un'unica polilinea chiusa sul Canvas di Tk."""
        pts = punti_bordo_continuo(cfg, x, y, w, h)
        if len(pts) < 2:
            return
        chiusi = pts + [pts[0]]
        xy = [c for px, py in chiusi for c in (X(px), Y(py))]
        cv.create_line(*xy, fill=col, smooth=False)

    def _fleuron_preview(self, cv, X, Y, x, y, w, h, cfg, col):
        """Come _fleuron_pdf ma disegnato come polilinee sul Canvas di Tk: ogni
        curva del motore e' campionata in punti (campiona_curva) e collegata con
        create_line, che non fa curve di Bezier vere."""
        d = dim_fleuron(cfg, w, h)

        def curva(punti, dx, dy):
            xy = [c for px, py in punti for c in (X(dx + px), Y(dy + py))]
            if len(xy) >= 4:
                cv.create_line(*xy, fill=col, smooth=False)

        for (cx, cy), rot in (((x, y), 45), ((x + w, y), 135),
                              ((x + w, y + h), 225), ((x, y + h), 315)):
            for tratto in curve_fleuron_angolo(d / mm, cfg.decoro_fleuron_ricciolo):
                curva(campiona_curva(ruota_curva(tratto, rot)), cx, cy)
        if cfg.decoro_fleuron_centrale:
            dc = d * 0.64
            for cx, cy, rot in ((x + w / 2.0, y, 90), (x + w / 2.0, y + h, 270)):
                for tratto in curve_fleuron_centrale(dc / mm):
                    curva(campiona_curva(ruota_curva(tratto, rot - 90)), cx, cy)

    # ---------- trascinamento ----------
    def _canvas_scale(self, cfg):
        """(scala, x e y dell'angolo alto a sinistra del foglio, larghezza e altezza).

        La scala e' in pixel per punto.  E' la scala che adatta il foglio alla finestra,
        moltiplicata per lo zoom; la vista si puo' spostare (self._pan) ma sempre in
        modo che il foglio riempia la finestra senza lasciare vuoti oltre un bordo.
        Anche il trascinamento dei pezzi passa da qui, quindi funziona a qualsiasi zoom.
        """
        W = self.canvas.winfo_width() or 430
        H = self.canvas.winfo_height() or 580
        pw, ph = cfg.pagina_pt()
        adatta = min((W - 2 * MARGINE_VISTA_PX) / pw, (H - 2 * MARGINE_VISTA_PX) / ph)
        s = adatta * self._zoom

        def limita(pan, dim_finestra, dim_foglio):
            if dim_foglio <= dim_finestra - 2 * MARGINE_VISTA_PX + 1e-6:
                return 0.0                                  # sta tutto: resta al centro
            centro = (dim_finestra - dim_foglio) / 2.0
            return min(max(pan, dim_finestra - MARGINE_VISTA_PX - dim_foglio - centro),
                       MARGINE_VISTA_PX - centro)
        self._pan = [limita(self._pan[0], W, pw * s), limita(self._pan[1], H, ph * s)]
        return (s, (W - pw * s) / 2.0 + self._pan[0], (H - ph * s) / 2.0 + self._pan[1],
                pw, ph)

    def _zoom_intorno(self, fattore, mx=None, my=None):
        """Ingrandisce (fattore > 1) o riduce, tenendo fermo il punto (mx, my) della finestra
        (di default il centro): il punto del foglio che sta sotto il puntatore ci resta."""
        cfg = self.leggi_config()
        s, ox, oy, pw, ph = self._canvas_scale(cfg)
        W = self.canvas.winfo_width() or 430
        H = self.canvas.winfo_height() or 580
        adatta = s / self._zoom
        massimo = max(1.0, PX_PER_MM_MAX / (adatta * mm))
        nuovo = min(max(self._zoom * fattore, 1.0), massimo)
        if abs(nuovo - self._zoom) < 1e-9:
            return
        mx = W / 2.0 if mx is None else mx
        my = H / 2.0 if my is None else my
        dx, dy = (mx - ox) / s, (my - oy) / s            # il punto del foglio sotto il puntatore
        s2 = adatta * nuovo
        self._zoom = nuovo
        self._pan = [mx - dx * s2 - (W - pw * s2) / 2.0, my - dy * s2 - (H - ph * s2) / 2.0]
        self._preview()

    def _zoom_rotella(self, ev):
        su = getattr(ev, "num", 0) == 4 or (isinstance(ev.delta, int) and ev.delta > 0)
        self._zoom_intorno(FATTORE_ZOOM if su else 1 / FATTORE_ZOOM, ev.x, ev.y)
        return "break"

    def _zoom_adatta(self):
        self._zoom, self._pan = 1.0, [0.0, 0.0]
        self._preview()

    def _pan_start(self, ev):
        self._pan_da = (ev.x, ev.y, self._pan[0], self._pan[1])

    def _pan_move(self, ev):
        if self._pan_da:
            x0, y0, px, py = self._pan_da
            self._pan = [px + ev.x - x0, py + ev.y - y0]
            self._preview()

    def _congela_posizioni_correnti(self, ph, tranne_idx):
        """Al primo trascinamento, blocca sul posto tutti gli altri tasselli
        ancora in automatico (solo serie 1). Altrimenti, tolto di mezzo il
        pezzo che si sta spostando, gli altri 'scivolerebbero' nel flusso per
        richiudere lo spazio lasciato libero, dando l'impressione di
        muoversi insieme."""
        for idx, x, y, w, h, serie_idx, _origine in self._rect_map:
            if serie_idx != 1 or idx < 0 or idx == tranne_idx:
                continue
            var_auto = self.vars.get("t%d_auto" % idx)
            if var_auto is None or not var_auto.get():
                continue
            # al millesimo, non al decimo: arrotondando a 0,1 mm gli altri pezzi
            # scivolerebbero di fino a 0,05 mm, e a un allineamento serve la precisione
            self.vars["t%d_x_mm" % idx].set(round(x / mm, 3))
            self.vars["t%d_y_mm" % idx].set(round((ph - y - h) / mm, 3))
            var_auto.set(False)

    def _parti_da_qui(self, prefisso, x, y, h, ph):
        """Se il pezzo era in posizione automatica, scrive nei suoi campi X e Y la
        posizione in cui si trova, prima di passarlo a manuale.  Senza, i campi
        avrebbero ancora il valore di partenza (20; 20) e il pezzo, al semplice
        clic, salterebbe li'."""
        var_auto = self.vars.get(prefisso + "auto")
        if var_auto is None or not var_auto.get():
            return
        self._blocca = True
        self.vars[prefisso + "x_mm"].set(round(x / mm, 3))
        self.vars[prefisso + "y_mm"].set(round((ph - y - h) / mm, 3))
        self._blocca = False

    def _drag_start(self, ev):
        cfg = self.leggi_config()
        s, ox, oy, pw, ph = self._canvas_scale(cfg)
        px = (ev.x - ox) / s
        py = ph - (ev.y - oy) / s
        self._pan_da = None
        for posizione, (idx, x, y, w, h, serie_idx, origine) in reversed(
                list(enumerate(self._rect_map))):
            if not (x <= px <= x + w and y <= py <= y + h):
                continue
            self._drag_rett = posizione
            if serie_idx > 1:
                # ogni tassello di ogni serie ha una posizione assoluta
                # propria, indipendente dalle altre serie
                if origine < 0:
                    self._drag = None
                    return
                self._drag = ("serie", serie_idx, origine, px - x, (y + h) - py)
                self.vars["serie_modo"].set("manuale")
                nome = "t%d_serie%d_" % (origine, serie_idx)
                self._parti_da_qui(nome, x, y, h, ph)
                self.vars[nome + "auto"].set(False)
            elif idx >= 0:
                self._congela_posizioni_correnti(ph, tranne_idx=idx)
                self._drag = ("tassello", idx, px - x, (y + h) - py)
                self._parti_da_qui("t%d_" % idx, x, y, h, ph)
                self.vars["t%d_auto" % idx].set(False)
            else:
                self._drag = None
            return
        # sullo sfondo: trascinando si sposta la vista (solo se e' ingrandita)
        self._drag = None
        self._pan_da = (ev.x, ev.y, self._pan[0], self._pan[1])

    def _drag_move(self, ev):
        if self._pan_da and not self._drag:
            self._pan_move(ev)
            return
        if not self._drag:
            return
        cfg = self.leggi_config()
        s, ox, oy, pw, ph = self._canvas_scale(cfg)
        px = (ev.x - ox) / s
        py = ph - (ev.y - oy) / s
        # dove finirebbe il pezzo, in mm dall'angolo alto a sinistra del foglio
        if self._drag[0] == "tassello":
            _, idx, dx, dy = self._drag
        else:
            _, _k, _origine, dx, dy = self._drag
        x_mm = (px - dx) / mm
        y_mm = (ph - (py + dy)) / mm
        x_mm, y_mm, guide = self._calamita_su(cfg, ev, s, x_mm, y_mm, ph / mm)
        self._guide = guide
        self._blocca = True
        if self._drag[0] == "tassello":
            self.vars["t%d_x_mm" % idx].set(x_mm)
            self.vars["t%d_y_mm" % idx].set(y_mm)
        else:  # "serie": posizione assoluta di quel solo tassello, quella serie
            _, k, origine, dx, dy = self._drag
            self.vars["t%d_serie%d_x_mm" % (origine, k)].set(x_mm)
            self.vars["t%d_serie%d_y_mm" % (origine, k)].set(y_mm)
        self._blocca = False
        self._preview()

    def _calamita_su(self, cfg, ev, s, x_mm, y_mm, ph_mm):
        """Applica la calamita alla posizione di un pezzo trascinato.

        x_mm e y_mm sono dall'angolo alto a sinistra, come i campi del pezzo.
        Restituisce (x_mm, y_mm, guide): senza calamita le posizioni sono arrotondate al
        decimo di millimetro; con l'aggancio, sull'asse agganciato restano esatte
        (arrotondate solo al millesimo, per il rumore dei decimali).
        """
        stato = ev.state if isinstance(getattr(ev, "state", 0), int) else 0
        i = self._drag_rett
        if not (0 <= i < len(self._rect_map)) or not self._calamita.get() or stato & 0x4:
            return round(x_mm, 1), round(y_mm, 1), None
        _idx, _x, _y, w, h, _serie, _origine = self._rect_map[i]
        w_mm, h_mm = w / mm, h / mm
        altri = [(rx / mm, ry / mm, rw / mm, rh / mm)
                 for j, (_i, rx, ry, rw, rh, _s, _o) in enumerate(self._rect_map) if j != i]
        # posizione con y dal basso, come vuole calamita()
        nx, ny, guide_x, guide_y = calamita(
            x_mm, ph_mm - y_mm - h_mm, w_mm, h_mm, altri,
            SOGLIA_CALAMITA_PX / (s * mm), cfg.pagina_pt()[0] / mm, ph_mm, cfg.margine_mm)
        x_finale = round(nx, 3) if guide_x else round(x_mm, 1)
        y_finale = round(ph_mm - ny - h_mm, 3) if guide_y else round(y_mm, 1)
        return x_finale, y_finale, ((guide_x, guide_y) if (guide_x or guide_y) else None)

    def _drag_fine(self, ev=None):
        self._drag = None
        self._pan_da = None
        self._drag_rett = -1
        if self._guide:
            self._guide = None
            self._preview()

    # ---------- azioni ----------
    def _genera(self, path) -> bool:
        cfg = self.leggi_config()
        try:
            info = build_pdf(cfg, path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return False
        msg = "%d tasselli, %d %s." % (info["tasselli"], info["pagine"],
                                       "pagina" if info["pagine"] == 1 else "pagine")
        if info["overflow"]:
            msg += "  Testo troppo grande in: " + ", ".join(sorted(set(info["overflow"])))
        if info["fuori_foglio"]:
            msg += "  Fuori dal foglio: " + ", ".join(info["fuori_foglio"])
        if info["avvisi_linee"]:
            msg += "  " + "  ".join(info["avvisi_linee"])
        if info["avvisi_doratura"]:
            msg += "  " + "  ".join(info["avvisi_doratura"])
        self.lbl_info.config(text=msg)
        return True

    def anteprima(self):
        p = os.path.join(tempfile.gettempdir(), "tasselli_anteprima.pdf")
        if self._genera(p):
            apri_file(p)

    def genera(self):
        cfg = self.leggi_config()
        nome = "".join(ch for ch in cfg.titolo.split("\n")[0]
                       if ch.isalnum() or ch in " -_").strip() or "tasselli"
        p = filedialog.asksaveasfilename(title="Salva il PDF",
                                         defaultextension=".pdf",
                                         initialfile=nome + ".pdf",
                                         filetypes=[("PDF", "*.pdf")])
        if p and self._genera(p):
            messagebox.showinfo(APP_NAME, "PDF salvato in:\n%s" % p)

    # ---------- progetti ----------
    def _scrivi(self, path):
        cfg = self.leggi_config()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(cfg), fh, indent=1, ensure_ascii=False)

    def salva_progetto(self):
        p = filedialog.asksaveasfilename(title="Salva le impostazioni del libro",
                                         defaultextension=".json",
                                         initialfile="libro.json",
                                         filetypes=[("Progetto", "*.json")])
        if not p:
            return
        try:
            self._scrivi(p)
            messagebox.showinfo(APP_NAME, "Salvato:\n%s" % p)
        except OSError as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def apri_progetto(self):
        p = filedialog.askopenfilename(title="Apri un libro",
                                       filetypes=[("Progetto", "*.json"),
                                                  ("Tutti", "*.*")])
        if p:
            self._carica(p)

    def _carica(self, path, silenzioso=False):
        if not os.path.isfile(path):
            if not silenzioso:
                messagebox.showinfo(APP_NAME, "File non trovato.")
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                cfg = config_da_dict(json.load(fh))
        except Exception as exc:
            if not silenzioso:
                messagebox.showerror(APP_NAME, str(exc))
            return
        self._blocca = True
        for f in fields(Config):
            if f.name.startswith("font_"):
                setattr(self.cfg, f.name, getattr(cfg, f.name))
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", cfg.titolo)
        for f in fields(cfg):
            if f.name in self.vars:
                try:
                    self.vars[f.name].set(getattr(cfg, f.name))
                except tk.TclError:
                    pass
        for i, t in enumerate(cfg.tasselli[:len(self.cfg.tasselli)]):
            for f in fields(t):
                key = "t%d_%s" % (i, f.name)
                if key not in self.vars:
                    continue
                val = getattr(t, f.name)
                if f.name == "rotazione":
                    val = next((k for k, v in ROTAZIONI.items()
                                if v == int(val)), "0 (orizzontale)")
                try:
                    self.vars[key].set(val)
                except tk.TclError:
                    pass
        self._blocca = False
        if self.fonts:
            self._seleziona((cfg.font_path, cfg.font_index))
        self._preview()

    def chiudi(self):
        """Ferma i job pendenti e salva l'ultimo libro.  Non distrugge nulla."""
        job = getattr(self, "_job", None)
        if job:
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        try:
            self._scrivi(ULTIMO)
        except Exception:
            pass
