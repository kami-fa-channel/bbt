"""Scheda Imposizione: dal PDF ai fascicoli da stampare."""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from types import SimpleNamespace

from .. import imposizione as imp
from .comuni import (C_BIANCA, C_FONDO, C_FOGLIO, C_PAGINA, C_PIEGA, C_SEGNO, Suggerimento,
                     applica_variabili, campo, intero, leggi_variabili, numero,
                     testo_scrollabile)

from .miniature import Miniature, motore

# Rendering facoltativo del contenuto delle pagine: pypdfium2 o pdftoppm, piu'
# pillow (vedi miniature.py).  Senza, l'anteprima resta schematica.
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None
RENDERING = motore() is not None and ImageTk is not None

# ogni quanto si guarda se il thread delle miniature ha finito qualche pagina
ATTESA_MS = 60

# valori di partenza dell'impaginazione (mm, tranne la scala)
IMPAGINAZIONE = {"dorso": "15", "est": "10", "testa": "10", "piede": "10",
                 "scala": "1.0", "shing": "0"}


class SchedaImposizione(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.pdf = None
        self.reader = None
        self.piano = None
        self.pagine_orig = 0
        self.blocco = []
        self.fogli = 4
        self.signature = 16
        self.n_fascicoli = 0
        self.miniature = None
        self.cache_foto = {}        # (indice, larghezza, altezza) -> PhotoImage
        self.immagini = []          # le PhotoImage sul canvas: tkinter non le tiene vive
        self._attesa = None
        self._lavoro = None         # la generazione in corso: fatte, totale, errore, fine
        self._pronte_viste = -1
        self.apertura = 0           # nel menabo': l'apertura (doppia pagina) mostrata

        sinistra = ttk.Frame(self)
        sinistra.pack(side="left", fill="y", padx=(0, 10))
        destra = ttk.Frame(self)
        destra.pack(side="right", fill="both", expand=True)

        self.form(sinistra)

        nav = ttk.Frame(destra)
        nav.pack(fill="x")
        ttk.Label(nav, text="Fascicolo").pack(side="left")
        self.n_fasc = tk.IntVar(value=1)
        self.sp_fasc = ttk.Spinbox(nav, from_=1, to=1, width=6, textvariable=self.n_fasc,
                                   command=self.disegna)
        self.sp_fasc.pack(side="left", padx=(4, 12))
        ttk.Label(nav, text="Facciata").pack(side="left")
        self.n_facc = tk.IntVar(value=1)
        self.sp_facc = ttk.Spinbox(nav, from_=1, to=1, width=6, textvariable=self.n_facc,
                                   command=self.disegna)
        self.sp_facc.pack(side="left", padx=4)
        ttk.Label(nav, text="Vista").pack(side="left", padx=(12, 4))
        self.v_vista = tk.StringVar(value="fascicolo")
        for valore, etichetta in (("fascicolo", "Fascicolo intero"), ("foglio", "Foglio"),
                                ("menabo", "Menabò")):
            ttk.Radiobutton(nav, text=etichetta, value=valore, variable=self.v_vista,
                            command=self.disegna).pack(side="left", padx=2)
        self.et_facc = ttk.Label(nav, text="", foreground="#777")
        self.et_facc.pack(side="left", padx=10)

        # il pannello si puo' trascinare per dare piu' spazio al disegno o al testo
        divisore = ttk.PanedWindow(destra, orient="vertical")
        divisore.pack(fill="both", expand=True, pady=6)

        cornice_canvas = ttk.Frame(divisore)
        self.canvas = tk.Canvas(cornice_canvas, bg="white", highlightthickness=1,
                                highlightbackground="#d8d8d0")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.disegna())
        # rotella: avanti e indietro di una facciata (nella vista Foglio) o di un
        # fascicolo (nella vista Fascicolo intero)
        self.canvas.bind("<MouseWheel>", lambda e: self.scorri(-1 if e.delta > 0 else 1))
        self.canvas.bind("<Button-4>", lambda e: self.scorri(-1))
        self.canvas.bind("<Button-5>", lambda e: self.scorri(1))
        divisore.add(cornice_canvas, weight=3)

        cornice_testo = ttk.Frame(divisore)
        self.testo = testo_scrollabile(cornice_testo, C_FONDO)
        divisore.add(cornice_testo, weight=1)

    def form(self, p):
        ttk.Button(p, text="Apri PDF...", command=self.apri).pack(fill="x")
        self.et_file = ttk.Label(p, text="nessun file", foreground="#777", wraplength=210)
        self.et_file.pack(anchor="w", pady=(4, 8))

        ttk.Label(p, text="Fascicolatura", font=("", 10, "bold")).pack(anchor="w")
        self.v_fogli = campo(p, "Fogli per fascicolo", "4", self.ricalcola)
        self.v_gram = campo(p, "Grammatura (g/m²)", "80", self.ricalcola)
        self.v_guardie = campo(p, "Fogli di guardia", "0", self.ricalcola)
        self.v_pos = campo(p, "Bianche di correzione", "", self.ricalcola)
        ttk.Label(p, text="posizioni separate da virgola",
                  foreground="#777").pack(anchor="w")
        self.v_filo = campo(p, "Filo per fascicolo (mm)", "", self.ricalcola)
        self.et_filo = ttk.Label(p, foreground="#777", wraplength=210, text=self.testo_filo(None))
        self.et_filo.pack(anchor="w")

        f = ttk.Frame(p)
        f.pack(fill="x", pady=(6, 0))
        ttk.Label(f, text="Formato di stampa", width=22).pack(side="left")
        self.v_carta = tk.StringVar(value="a4")
        cb = ttk.Combobox(f, textvariable=self.v_carta, width=7, state="readonly",
                          values=sorted(imp.FORMATI))
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.disegna())
        self.v_tranche = campo(p, "Pagine per tranche", "50", self.ricalcola)

        ttk.Separator(p).pack(fill="x", pady=8)
        ttk.Label(p, text="Impaginazione (mm)", font=("", 10, "bold")).pack(anchor="w")
        self.v_dorso = campo(p, "Margine al dorso", IMPAGINAZIONE["dorso"], self.disegna)
        self.v_est = campo(p, "Margine esterno", IMPAGINAZIONE["est"], self.disegna)
        self.v_testa = campo(p, "Margine testa", IMPAGINAZIONE["testa"], self.disegna)
        self.v_piede = campo(p, "Margine piede", IMPAGINAZIONE["piede"], self.disegna)
        self.v_scala = campo(p, "Scala", IMPAGINAZIONE["scala"], self.disegna)
        self.v_shing = campo(p, "Shingling (mm/foglio)", IMPAGINAZIONE["shing"], self.disegna)

        self.v_segni = tk.BooleanVar(value=True)
        self.v_segni.trace_add("write", lambda *_: self.disegna())
        ttk.Checkbutton(p, text="Segni di piega e collazione",
                        variable=self.v_segni).pack(anchor="w", pady=4)
        ttk.Button(p, text="Ripristina impaginazione",
                   command=self.ripristina_impaginazione).pack(fill="x", pady=2)

        self.v_quote = tk.BooleanVar(value=True)
        self.v_quote.trace_add("write", lambda *_: self.disegna())
        ttk.Checkbutton(p, text="Misure in mm (vista Foglio)",
                        variable=self.v_quote).pack(anchor="w")

        f = ttk.Frame(p)
        f.pack(fill="x", pady=(0, 4))
        ttk.Label(f, text="Sigla Fx.y alla piega", width=22).pack(side="left")
        self.v_etichetta = tk.StringVar(value="orizzontale")
        cb_etichetta = ttk.Combobox(f, textvariable=self.v_etichetta, width=10,
                                    state="readonly", values=imp.ETICHETTE)
        cb_etichetta.pack(side="left")
        cb_etichetta.bind("<<ComboboxSelected>>", lambda e: self.disegna())

        self.v_render = tk.BooleanVar(value=RENDERING)
        self.v_render.trace_add("write", lambda *_: self.disegna())
        cb_render = ttk.Checkbutton(p, text="Mostra il contenuto delle pagine",
                                    variable=self.v_render)
        cb_render.pack(anchor="w")
        if not RENDERING:
            cb_render.state(["disabled"])
            ttk.Label(p, text="per vederlo: pip install pypdfium2 pillow "
                              "(oppure installa poppler-utils)",
                      foreground="#777", wraplength=210).pack(anchor="w")

        ttk.Separator(p).pack(fill="x", pady=8)
        ttk.Button(p, text="Shingling dalla grammatura",
                   command=self.shingling_auto).pack(fill="x", pady=2)
        self.v_per_tranche = tk.BooleanVar(value=False)
        ttk.Checkbutton(p, text="Un PDF per ogni tranche",
                        variable=self.v_per_tranche).pack(anchor="w")
        self.pulsante_genera = ttk.Button(p, text="Genera il PDF...", command=self.genera)
        self.pulsante_genera.pack(fill="x", pady=2)
        self.barra = ttk.Progressbar(p, mode="determinate", maximum=1)   # visibile solo mentre lavora

        ttk.Separator(p).pack(fill="x", pady=8)
        self.v_rifilo = campo(p, "Rifilo previsto (mm)", "3", lambda: None)
        pulsante_misure = ttk.Button(p, text="Porta le misure alla copertina",
                                     command=self.passa_misure)
        pulsante_misure.pack(fill="x", pady=2)
        Suggerimento(pulsante_misure,
                     "La stima è una corda (spessore della carta più il filo): se il "
                     "dorso viene arrotondato, l'arco reale sarà qualche millimetro più "
                     "lungo, quindi il campo va corretto a mano.")

        self.stato = ttk.Label(p, text="", foreground="#777", wraplength=210)
        self.stato.pack(anchor="w", pady=(8, 0))

    # ------------------------------------------------------------ dati
    def posizioni(self):
        validi, fuori = imp.leggi_posizioni([self.v_pos.get()], self.pagine_orig, rigido=False)
        if fuori:
            self.stato.config(text=f"Posizioni fuori intervallo, ignorate: {fuori}")
        return validi

    def args(self):
        return SimpleNamespace(
            carta=self.v_carta.get(),
            margine_dorso=numero(self.v_dorso, 15),
            margine_esterno=numero(self.v_est, 10),
            margine_testa=numero(self.v_testa, 10),
            margine_piede=numero(self.v_piede, 10),
            scala=numero(self.v_scala, 1.0) or 1.0,
            shingling=numero(self.v_shing, 0.0),
            segni=self.v_segni.get(),
            etichetta=self.v_etichetta.get(),
        )

    def variabili(self):
        return {"fogli": self.v_fogli, "grammatura": self.v_gram, "guardie": self.v_guardie,
                "bianche": self.v_pos, "filo": self.v_filo, "carta": self.v_carta,
                "tranche": self.v_tranche, "dorso": self.v_dorso, "esterno": self.v_est,
                "testa": self.v_testa, "piede": self.v_piede, "scala": self.v_scala,
                "shingling": self.v_shing, "segni": self.v_segni,
                "etichetta": self.v_etichetta, "quote": self.v_quote,
                "per_tranche": self.v_per_tranche, "rifilo": self.v_rifilo,
                "vista": self.v_vista}

    def impostazioni(self):
        """Quel che si ricorda alla chiusura: i campi e il PDF aperto."""
        dati = leggi_variabili(self.variabili())
        dati["pdf"] = self.pdf
        return dati

    def applica(self, dati):
        """Rimette i campi salvati e riapre il PDF, se c'e' ancora.

        Le bianche di correzione sono posizioni di quel PDF: senza di lui non
        hanno senso e si lasciano vuote."""
        pdf = dati.get("pdf")
        pdf = pdf if isinstance(pdf, str) and os.path.isfile(pdf) else None
        if pdf is None:
            dati = {**dati, "bianche": ""}
        applica_variabili(self.variabili(), dati, {
            "carta": imp.FORMATI, "etichetta": imp.ETICHETTE,
            "vista": ("fascicolo", "foglio", "menabo")})
        if pdf:
            self.carica(pdf, avvisa=False)

    def filo(self):
        """Il filo per fascicolo indicato dall'utente, o None se il campo e' vuoto."""
        valore = numero(self.v_filo, 0.0)
        return valore if valore > 0 else None

    @staticmethod
    def testo_filo(n_fascicoli):
        minimo, massimo = imp.FILO_MM_PER_FASCICOLO
        testo = f"vuoto = stima {minimo:g}-{massimo:g} mm."
        if n_fascicoli:
            testo += (f" Prova della penna: {n_fascicoli} giri di filo, misura le spire "
                      f"e dividi per {n_fascicoli}.")
        return testo

    def ripristina_impaginazione(self):
        """Riporta margini, scala, shingling e segni ai valori di partenza e ricalcola."""
        for nome, valore in IMPAGINAZIONE.items():
            getattr(self, f"v_{nome}").set(valore)
        self.v_segni.set(True)
        self.v_etichetta.set("orizzontale")
        self.ricalcola()

    def shingling_auto(self):
        self.v_shing.set(f"{imp.spessore_foglio_mm(intero(self.v_gram, 80)):.3f}")

    # ------------------------------------------------------------ apertura
    def apri(self):
        percorso = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if percorso:
            self.carica(percorso)

    def carica(self, percorso, avvisa=True):
        try:
            self.reader = imp.apri_pdf(percorso)
            self.pagine_orig = len(self.reader.pages)
        except Exception as e:
            if avvisa:
                messagebox.showerror("Errore", f"Non riesco a leggere il PDF:\n{e}")
            return
        self.pdf = percorso
        self.cache_foto.clear()
        if self.miniature is not None:
            self.miniature.chiudi()
        self.miniature = Miniature(percorso) if RENDERING else None
        self.et_file.config(text=f"{os.path.basename(percorso)} ({self.pagine_orig} pagine)")
        self.ricalcola()

    def ricalcola(self):
        if not self.reader:
            return
        self.fogli = max(1, intero(self.v_fogli, 4))
        self.piano = imp.piano(self.pagine_orig, self.posizioni(),
                               max(0, intero(self.v_guardie, 0)), self.fogli,
                               intero(self.v_gram, 80), self.filo())
        self.et_filo.config(text=self.testo_filo(self.piano.n_fascicoli))
        self.signature = self.piano.signature
        self.blocco = self.piano.blocco
        self.n_fascicoli = self.piano.n_fascicoli
        self.sp_fasc.config(to=self.n_fascicoli)
        self.sp_facc.config(to=self.fogli * 2)
        try:
            if self.n_fasc.get() > self.n_fascicoli:
                self.n_fasc.set(1)
            if self.n_facc.get() > self.fogli * 2:
                self.n_facc.set(1)
        except tk.TclError:
            self.n_fasc.set(1)
            self.n_facc.set(1)
        self.riepilogo()
        self.disegna()

    def riepilogo(self):
        g = intero(self.v_gram, 80)
        p = self.piano
        dorso = imp.misure_blocco_stimate(p, self.v_carta.get(), numero(self.v_rifilo, 3))
        righe = [
            f"Pagine originali:             {self.pagine_orig}",
            f"Pagine totali del blocco:     {p.pagine_blocco}",
            f"Pagine di riempimento finale: {p.riempimento}",
            f"Fascicoli: {p.n_fascicoli}    Fogli da stampare: {p.fogli_da_stampare} (fronte/retro)",
            f"Pagine del PDF finale:        {p.pagine_pdf}",
            f"Spessore del blocco (stima):  {p.spessore_carta_mm:.1f} mm di carta, più "
            + (f"{p.filo_mm[0]:.1f} mm di filo ({self.filo():g} mm per fascicolo, indicati da te)"
               if p.filo_indicato else f"{p.filo_mm[0]:.1f}-{p.filo_mm[1]:.1f} mm di filo"),
            f"Dorso stimato per la copertina: {dorso.dorso:.1f} mm "
            + ("(con il filo che hai indicato)" if p.filo_indicato
               else f"(fra {dorso.dorso_min:.1f} e {dorso.dorso_max:.1f})"),
            f"Consiglio per {g} g/m²: {imp.consiglio_fogli(g)} fogli per fascicolo",
            "",
        ]
        if imp.avviso_filo(self.filo()):
            righe[-1:] = ["", imp.avviso_filo(self.filo()), ""]
        target = max(1, intero(self.v_tranche, 50))
        righe.append(f"TRANCHE DI STAMPA (blocchi da circa {target} pagine)")
        for x in imp.tranche(target, self.fogli, p.n_fascicoli)["elenco"]:
            righe.append(f"  Tranche {x['n']}: {x['inizio']}-{x['fine']}   "
                         f"(fascicoli F{x['f1']}-F{x['f2']})")
        base = self.pagine_orig + len(self.posizioni()) + 4 * max(0, intero(self.v_guardie, 0))
        tab = imp.tabella_fascicolature(g, base)
        righe += ["", f"FASCICOLATURE POSSIBILI ({g} g/m², {base} pagine da impaginare)"]
        righe += imp.righe_tabella(tab, "{} fogli per fascicolo")
        self.testo.delete("1.0", "end")
        self.testo.insert("1.0", "\n".join(righe))

    # ------------------------------------------------------------ disegno
    def geometria(self, a):
        """Misure del foglio imposto in mm, o None se i margini non lasciano spazio."""
        larghezza_mm, altezza_mm = imp.FORMATI.get(a.carta, (210.0, 297.0))
        W_mm, H_mm = altezza_mm, larghezza_mm      # foglio in orizzontale
        meta = W_mm / 2
        cella_w = meta - a.margine_dorso - a.margine_esterno
        cella_h = H_mm - a.margine_testa - a.margine_piede
        if cella_w <= 0 or cella_h <= 0:
            return None
        return SimpleNamespace(W=W_mm, H=H_mm, meta=meta, cella_w=cella_w, cella_h=cella_h)

    def misure_pagina(self, indice):
        """Larghezza e altezza della pagina sorgente in punti, rotazione compresa.

        Per le bianche si usa la prima pagina: imponendo restano vuote, ma
        nell'anteprima serve comunque un riquadro dove si troverebbero."""
        pagina = self.reader.pages[0 if indice is None else indice]
        box = pagina.cropbox if pagina.cropbox else pagina.mediabox
        pw, ph = float(box.width), float(box.height)
        if pagina.rotation in (90, 270):
            pw, ph = ph, pw
        return pw, ph

    def facciata_corrente(self):
        """(fascicolo, facciata) mostrati, 0-based, o None se i contatori sono illeggibili."""
        try:
            return (max(1, min(self.n_fasc.get(), self.n_fascicoli)) - 1,
                    max(1, min(self.n_facc.get(), self.fogli * 2)) - 1)
        except tk.TclError:
            return None

    def disegna(self):
        c = self.canvas
        c.delete("all")
        self.immagini = []
        if not self.reader or not self.blocco:
            c.create_text(20, 20, anchor="nw", fill="#999",
                          text="Apri un PDF per vedere l'anteprima.")
            return
        a = self.args()
        g = self.geometria(a)
        corrente = self.facciata_corrente()
        if corrente is None:
            return
        i_fasc, i_facc = corrente
        if g is None:
            c.create_text(20, 20, anchor="nw", fill="#c00",
                          text="I margini non lasciano spazio alla pagina.")
            return
        mostra = self.v_render.get() and self.miniature is not None
        if mostra:
            # le pagine che servono adesso le richiede il disegno qui sotto:
            # quelle chieste per il fascicolo di prima non servono piu'
            self.miniature.dimentica_coda()
            self._pronte_viste = self.miniature.pronte()
        W = c.winfo_width() or 700
        H = c.winfo_height() or 360

        if self.v_vista.get() == "foglio":
            self.vista_foglio(a, g, i_fasc, i_facc, W, H, mostra)
        elif self.v_vista.get() == "menabo":
            self.vista_menabo(W, H, mostra)
        else:
            self.vista_fascicolo(a, g, i_fasc, i_facc, W, H, mostra)

        aiuto = {"fascicolo": "clic su una facciata per ingrandirla",
                 "foglio": "clic per tornare al fascicolo",
                 "menabo": "clic sulla barra per saltare"}[self.v_vista.get()]
        c.create_text(10, 6, anchor="nw", fill="#999", font=("", 8),
                      text=("Anteprima: posizione e ordine delle pagine, con il contenuto "
                            "ridotto." if mostra else
                            "Anteprima schematica: posizione e ordine delle pagine, "
                            "non la resa del contenuto.")
                           + f"  ({aiuto}; rotella per sfogliare)")
        if mostra and self.miniature.in_attesa() and self._attesa is None:
            self._attesa = self.after(ATTESA_MS, self._controlla_miniature)

    def _controlla_miniature(self):
        self._attesa = None
        if self.miniature is None or not self.winfo_exists():
            return
        if self.miniature.pronte() != self._pronte_viste:
            self.disegna()                      # riprogramma lui il controllo
        elif self.miniature.in_attesa():
            self._attesa = self.after(ATTESA_MS, self._controlla_miniature)

    def vista_foglio(self, a, g, i_fasc, i_facc, W, H, mostra):
        """Una facciata sola, grande quanto il riquadro."""
        bordo = 50
        k = min((W - 2 * bordo) / g.W, (H - 2 * bordo) / g.H)
        if k <= 0:
            return
        x0 = (W - g.W * k) / 2
        y0 = (H - g.H * k) / 2
        self.disegna_facciata(a, g, i_fasc, i_facc, x0, y0, k, mostra, grande=True)
        self.canvas.tag_bind("facciata", "<Button-1>", lambda e: self.v_vista.set("fascicolo")
                             or self.disegna())

        foglio = i_facc // 2
        spinta = foglio * a.shingling
        self.et_facc.config(text=f"foglio {foglio + 1} di {self.fogli}, "
                                 f"{'fronte' if i_facc % 2 == 0 else 'retro'} · pagina "
                                 f"{i_fasc * self.fogli * 2 + i_facc + 1} del PDF finale")
        if spinta:
            self.canvas.create_text(x0, y0 + g.H * k + 16, anchor="nw", fill=C_SEGNO,
                                    font=("", 8),
                                    text=f"shingling: questo foglio è spostato di "
                                         f"{spinta:.2f} mm verso il dorso")

    def disposizione_fascicolo(self, g, W, H):
        """Sceglie fra una riga per foglio (fronte | retro) e due righe (fronti
        sopra, retri sotto) quella che fa le facciate piu' grandi.
        Restituisce (righe, colonne, scala in px/mm, spazio fra le facciate)."""
        spazio, titolo, alto = 14, 16, 24
        migliore = None
        for righe, colonne in ((self.fogli, 2), (2, self.fogli)):
            k = min((W - 20 - spazio * (colonne - 1)) / (colonne * g.W),
                    (H - alto - 10 - (spazio + titolo) * righe) / (righe * g.H))
            if migliore is None or k > migliore[2]:
                migliore = (righe, colonne, k)
        return migliore + (spazio, titolo, alto)

    def vista_fascicolo(self, a, g, i_fasc, i_facc, W, H, mostra):
        """Tutte le facciate del fascicolo, fronte e retro di ogni foglio."""
        c = self.canvas
        righe, colonne, k, spazio, titolo, alto = self.disposizione_fascicolo(g, W, H)
        if k <= 0:
            return
        largo = colonne * g.W * k + spazio * (colonne - 1)
        sx = (W - largo) / 2
        for j in range(self.fogli * 2):
            foglio, retro = divmod(j, 2)
            riga, colonna = (foglio, retro) if colonne == 2 else (retro, foglio)
            x0 = sx + colonna * (g.W * k + spazio)
            y0 = alto + titolo + riga * (g.H * k + spazio + titolo)
            scelta = j == i_facc
            c.create_text(x0, y0 - 3, anchor="sw", font=("", 8, "bold" if scelta else ""),
                          fill=C_PIEGA if scelta else "#777",
                          text=f"foglio {foglio + 1} · {'retro' if retro else 'fronte'}")
            self.disegna_facciata(a, g, i_fasc, j, x0, y0, k, mostra, grande=False,
                                  tag=f"facciata{j}")
            if scelta:
                c.create_rectangle(x0 - 3, y0 - 3, x0 + g.W * k + 3, y0 + g.H * k + 3,
                                   outline=C_PIEGA, width=2)
            c.tag_bind(f"facciata{j}", "<Button-1>",
                       lambda e, j=j: self.ingrandisci(j))

        base = i_fasc * self.signature
        pagine = [i for i in self.blocco[base:base + self.signature] if i is not None]
        dove = f"pagine {pagine[0] + 1}-{pagine[-1] + 1} del libro" if pagine else "solo bianche"
        self.et_facc.config(text=f"fascicolo {i_fasc + 1} di {self.n_fascicoli} · {dove}")

    # ------------------------------------------------------------ menabo'
    def n_aperture(self):
        """Doppie pagine del libro: la prima pagina da sola a destra, poi a coppie."""
        return len(self.blocco) // 2 + 1

    def pagine_apertura(self, s):
        """(posizione a sinistra, posizione a destra) nel blocco, None dove non c'e' pagina."""
        sx, dx = 2 * s - 1, 2 * s
        n = len(self.blocco)
        return (sx if 0 <= sx < n else None, dx if dx < n else None)

    def fascicolo_apertura(self, s):
        sx, dx = self.pagine_apertura(s)
        return (dx if dx is not None else sx) // self.signature

    def vista_menabo(self, W, H, mostra):
        """Il libro come verra': l'apertura corrente a doppia pagina e, sotto, la
        barra dei fascicoli con il punto in cui ci si trova."""
        c = self.canvas
        self.apertura = max(0, min(self.apertura, self.n_aperture() - 1))
        try:
            voluto = max(1, min(self.n_fasc.get(), self.n_fascicoli)) - 1
        except tk.TclError:
            return
        if self.fascicolo_apertura(self.apertura) != voluto:
            # e' cambiato il fascicolo dal contatore: si apre alla sua prima pagina
            self.apertura = (voluto * self.signature + 1) // 2
        corrente = self.fascicolo_apertura(self.apertura)
        coppia = self.pagine_apertura(self.apertura)

        barra, alto = 58, 24
        misure = [self.misure_pagina(self.blocco[x]) for x in coppia if x is not None]
        pw = max(m[0] for m in misure)
        ph = max(m[1] for m in misure)
        k = min((W - 40) / 2 / pw, (H - alto - barra - 50) / ph)
        if k <= 0:
            return
        centro = W / 2
        y0 = alto + (H - alto - barra - 40 - ph * k) / 2
        for lato, x in zip((-1, 1), coppia):
            if x is None:
                continue
            indice = self.blocco[x]
            w, h = self.misure_pagina(indice)
            w, h = w * k, h * k
            x0 = centro - w if lato < 0 else centro
            y = y0 + (ph * k - h) / 2
            mio = x // self.signature == corrente
            colore = C_BIANCA if indice is None else (C_PAGINA if mio else "#aaa")
            c.create_rectangle(x0, y, x0 + w, y + h, fill="white", outline=colore,
                               width=2 if mio else 1)
            foto = self.foto(indice, w, h) if mostra else None
            if foto is not None:
                self.immagini.append(foto)
                c.create_image(x0, y, anchor="nw", image=foto)
                c.create_rectangle(x0, y, x0 + w, y + h, outline=colore, width=2 if mio else 1)
            elif indice is None:
                c.create_text(x0 + w / 2, y + h / 2, text="bianca", fill=C_BIANCA)
            c.create_text(x0 + w / 2, y + h + 6, anchor="n", fill="#777", font=("", 8),
                          text=f"pagina {x + 1}" + ("  (bianca)" if indice is None else ""))
        c.create_line(centro, y0 - 4, centro, y0 + ph * k + 4, fill=C_PIEGA, dash=(6, 4))

        # barra dei fascicoli: un segmento ciascuno, largo come le sue pagine
        n = len(self.blocco)
        bx0, bx1 = 20, W - 20
        by0 = H - barra + 18
        c.create_rectangle(bx0, by0, bx1, by0 + 14, fill="#eee", outline="#bbb", tags="barra")
        for f in range(self.n_fascicoli):
            xa = bx0 + (bx1 - bx0) * f * self.signature / n
            xb = bx0 + (bx1 - bx0) * (f + 1) * self.signature / n
            if f == corrente:
                c.create_rectangle(xa, by0, xb, by0 + 14, fill=C_PIEGA, outline="", tags="barra")
            c.create_line(xa, by0, xa, by0 + 14, fill="#bbb", tags="barra")
        sx, dx = coppia
        pos = dx if dx is not None else sx
        xm = bx0 + (bx1 - bx0) * (pos + 0.5) / n
        c.create_line(xm, by0 - 3, xm, by0 + 17, fill="#333", width=2, tags="barra")

        # numero del fascicolo sopra e pagine che contiene sotto; se i segmenti sono
        # troppo stretti per le scritte se ne salta qualcuno, tenendo il corrente
        larghezza = (bx1 - bx0) * self.signature / n
        cifre = len(str(n)) * 2 + 1
        passo = max(1, int(-(-cifre * 6 // larghezza)))
        for f in range(self.n_fascicoli):
            if f % passo and f != corrente:
                continue
            if f != corrente and abs(f - corrente) < passo:
                continue
            xc = bx0 + (bx1 - bx0) * (f + 0.5) * self.signature / n
            ultima = min(n, (f + 1) * self.signature)
            peso = "bold" if f == corrente else ""
            c.create_text(xc, by0 - 4, anchor="s", font=("", 8, peso),
                          fill=C_PIEGA if f == corrente else "#777", text=f"F{f + 1}",
                          tags="barra")
            c.create_text(xc, by0 + 18, anchor="n", font=("", 7, peso), fill="#777",
                          text=f"{f * self.signature + 1}-{ultima}", tags="barra")
        c.tag_bind("barra", "<Button-1>", lambda e: self.salta_barra(e.x, bx0, bx1, n))

        visibili = [x + 1 for x in coppia if x is not None]
        self.et_facc.config(text=f"pagine {'-'.join(map(str, visibili))} di {n} · "
                                 f"fascicolo {corrente + 1} di {self.n_fascicoli}")

    def salta_barra(self, x, bx0, bx1, n):
        pos = max(0, min(n - 1, int((x - bx0) / max(1, bx1 - bx0) * n)))
        self.apertura = (pos + 1) // 2
        self.n_fasc.set(self.fascicolo_apertura(self.apertura) + 1)
        self.disegna()

    def ingrandisci(self, i_facc):
        self.n_facc.set(i_facc + 1)
        self.v_vista.set("foglio")
        self.disegna()

    def scorri(self, verso):
        """Rotella del mouse: facciata dopo facciata, o fascicolo dopo fascicolo."""
        corrente = self.facciata_corrente()
        if not self.blocco or corrente is None:
            return
        i_fasc, i_facc = corrente
        if self.v_vista.get() == "menabo":
            self.apertura = max(0, min(self.apertura + verso, self.n_aperture() - 1))
            self.n_fasc.set(self.fascicolo_apertura(self.apertura) + 1)
            self.disegna()
            return
        if self.v_vista.get() == "foglio":
            n = i_fasc * self.fogli * 2 + i_facc + verso
            n = max(0, min(n, self.n_fascicoli * self.fogli * 2 - 1))
            i_fasc, i_facc = divmod(n, self.fogli * 2)
        else:
            i_fasc = max(0, min(i_fasc + verso, self.n_fascicoli - 1))
        self.n_fasc.set(i_fasc + 1)
        self.n_facc.set(i_facc + 1)
        self.disegna()

    def disegna_facciata(self, a, g, i_fasc, i_facc, x0, y0, k, mostra, grande, tag="facciata"):
        """Una facciata del foglio imposto con l'angolo in alto a sinistra in
        (x0, y0) pixel e k pixel per millimetro, come la scrive imposizione.imponi."""
        c = self.canvas

        def px(mx, my):
            return x0 + mx * k, y0 + my * k

        c.create_rectangle(*px(0, 0), *px(g.W, g.H), fill=C_FOGLIO, outline="#aaa", tags=tag)
        c.create_line(*px(g.meta, 0), *px(g.meta, g.H), fill=C_PIEGA, dash=(6, 4), tags=tag)

        sinistra, destra = imp.ordine_fascicolo(self.signature)[i_facc]
        foglio = i_facc // 2
        fronte = i_facc % 2 == 0
        spinta = foglio * a.shingling
        piccolo = ("", 8 if grande else 7)
        quote_pagine = []
        for lato, num in (("sx", sinistra), ("dx", destra)):
            indice = self.blocco[i_fasc * self.signature + num - 1]
            pw, ph = self.misure_pagina(indice)
            s = min(g.cella_w / pw, g.cella_h / ph) * a.scala
            larg, alt = pw * s, ph * s
            cx = (a.margine_esterno + spinta) if lato == "sx" else (g.meta + a.margine_dorso - spinta)
            bx = cx + (g.cella_w - larg) / 2
            by = a.margine_testa + (g.cella_h - alt) / 2
            colore = C_BIANCA if indice is None else C_PAGINA
            nome = "bianca" if indice is None else f"pag. {indice + 1}"
            quote_pagine.append((lato, (bx, by, larg, alt)))
            c.create_rectangle(*px(bx, by), *px(bx + larg, by + alt),
                               outline=colore, width=2 if grande else 1, fill="white", tags=tag)
            foto = self.foto(indice, larg * k, alt * k) if mostra else None
            if foto is not None:
                self.immagini.append(foto)
                c.create_image(*px(bx, by), anchor="nw", image=foto, tags=tag)
                c.create_rectangle(*px(bx, by), *px(bx + larg, by + alt),
                                   outline=colore, width=2 if grande else 1, tags=tag)
                if grande:
                    c.create_text(*px(bx + larg / 2, by + alt + 4), fill="#999", font=piccolo,
                                  text=f"{nome} ({num} del fascicolo)", tags=tag)
                else:
                    # il numero in un cartellino sull'angolo in basso, verso il taglio
                    xa = bx + 1 if lato == "sx" else bx + larg - 1
                    t = c.create_text(*px(xa, by + alt - 1), anchor="sw" if lato == "sx" else "se",
                                      text=nome, font=piccolo, fill=colore, tags=tag)
                    sfondo = c.create_rectangle(*c.bbox(t), fill="white", outline="", tags=tag)
                    c.tag_lower(sfondo, t)
            else:
                c.create_text(*px(bx + larg / 2, by + alt / 2), text=nome, fill=colore,
                              font=("", 10 if grande else 8), tags=tag)
                if grande:
                    c.create_text(*px(bx + larg / 2, by + alt / 2), fill="#999", font=piccolo,
                                  text=f"\n\n({num} del fascicolo)", tags=tag)

        if grande and self.v_quote.get():
            for lato, rettangolo in quote_pagine:
                self.quote(g, lato, *rettangolo, px)

        if a.segni:
            for ya, yb in ((0, 6), (g.H - 6, g.H)):
                c.create_line(*px(g.meta, ya), *px(g.meta, yb), fill=C_SEGNO, width=2, tags=tag)
            if fronte:
                if grande and a.etichetta == "orizzontale":
                    c.create_text(*px(g.meta + 3, 12), anchor="sw", fill=C_SEGNO, font=piccolo,
                                  text=f"F{i_fasc + 1}.{foglio + 1}", tags=tag)
                elif grande and a.etichetta == "verticale":
                    c.create_text(*px(g.meta + 5, 8), anchor="ne", angle=90, fill=C_SEGNO,
                                  font=piccolo, text=f"F{i_fasc + 1}.{foglio + 1}", tags=tag)
                if foglio == 0:
                    # la stessa scaletta di imposizione.imponi
                    utile = g.H - 24
                    gradino = min(6.0, utile / max(1, self.n_fascicoli))
                    per_scaletta = max(1, int(utile / gradino + 1e-9))
                    y = 9 + (i_fasc % per_scaletta) * gradino
                    c.create_rectangle(*px(g.meta - 3, y), *px(g.meta + 3, y + 3),
                                       fill=C_SEGNO, outline="", tags=tag)

    def quote(self, g, lato, bx, by, larg, alt, px):
        """Le distanze in mm fra il contenuto di una pagina e i bordi del foglio
        (e la piega), con una linea di quota per ciascuna."""
        c = self.canvas
        colore = "#1f6fb5"
        cx, cy = bx + larg / 2, by + alt / 2
        if lato == "sx":
            orizzontali = ((0, bx), (bx + larg, g.meta))
        else:
            orizzontali = ((g.meta, bx), (bx + larg, g.W))
        verticali = ((0, by), (by + alt, g.H))

        def quota(x1, y1, x2, y2, valore):
            if valore <= 0.005:
                return
            c.create_line(*px(x1, y1), *px(x2, y2), fill=colore, arrow="both",
                          arrowshape=(5, 6, 2), tags="quote")
            t = c.create_text(*px((x1 + x2) / 2, (y1 + y2) / 2), text=f"{valore:.1f}",
                              fill=colore, font=("", 8), tags="quote")
            sfondo = c.create_rectangle(*c.bbox(t), fill="white", outline="", tags="quote")
            c.tag_lower(sfondo, t)

        for a, b in orizzontali:
            quota(a, cy, b, cy, b - a)
        for a, b in verticali:
            quota(cx, a, cx, b, b - a)

    def foto(self, indice, larghezza_px, altezza_px):
        """La pagina del PDF come PhotoImage della misura richiesta, o None se
        e' una bianca o se la miniatura non e' ancora pronta."""
        if indice is None or self.miniature is None or larghezza_px < 8 or altezza_px < 8:
            return None
        w, h = max(1, int(larghezza_px)), max(1, int(altezza_px))
        immagine = self.miniature.chiedi(indice, max(w, h))
        if immagine is None:
            return None
        chiave = (indice, w, h)
        gia = self.cache_foto.get(chiave)
        if gia is not None and gia[0] is immagine:
            return gia[1]
        foto = ImageTk.PhotoImage(immagine.resize((w, h), Image.LANCZOS))
        if len(self.cache_foto) > 80:
            self.cache_foto.clear()
        self.cache_foto[chiave] = (immagine, foto)
        return foto

    # ------------------------------------------------------------ azioni
    def genera(self):
        if self._lavoro:
            return
        if not self.reader:
            messagebox.showinfo("Nessun file", "Apri prima un PDF.")
            return
        predefinito = os.path.splitext(os.path.basename(self.pdf))[0] + "_booklet.pdf"
        percorso = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                initialfile=predefinito,
                                                filetypes=[("PDF", "*.pdf")])
        if not percorso:
            return
        try:
            args = self.args()
        except Exception as e:
            messagebox.showerror("Errore", str(e))
            return
        # copie: mentre il thread lavora si puo' aprire un altro PDF
        reader, blocco, fogli, pdf = self.reader, self.blocco, self.fogli, self.pdf
        elenco = (imp.tranche(max(1, intero(self.v_tranche, 50)), fogli,
                              self.n_fascicoli)["elenco"] if self.v_per_tranche.get() else None)
        lavoro = self._lavoro = {"fatte": 0, "totale": 1, "errore": None, "fine": False,
                                 "pdf": pdf, "pagine": self.n_fascicoli * fogli * 2}

        def avanzamento(fatte, totale):
            lavoro["fatte"], lavoro["totale"] = fatte, totale

        def lavora():
            try:
                imp.impagina(reader, blocco, args, fogli, percorso, avanzamento)
                if elenco:
                    lavoro["tranche"] = len(imp.esporta_tranche(percorso, elenco))
            except Exception as e:
                lavoro["errore"] = e
            finally:
                lavoro["fine"] = True

        self.stato.config(text="Imposizione in corso...")
        self.pulsante_genera.state(["disabled"])
        self.barra.config(value=0, maximum=1)
        self.barra.pack(fill="x", pady=2, after=self.pulsante_genera)
        threading.Thread(target=lavora, daemon=True).start()
        self.after(ATTESA_MS, self._controlla_lavoro, percorso)

    def _controlla_lavoro(self, percorso):
        """Aggiorna la barra; a lavoro finito mostra l'esito (gira nel thread della finestra)."""
        lavoro = self._lavoro
        fatte, totale = lavoro["fatte"], max(1, lavoro["totale"])
        self.barra.config(maximum=totale, value=fatte)
        if not lavoro["fine"]:
            if fatte >= totale:
                self.stato.config(text="Salvataggio...")
            else:
                self.stato.config(text=f"Imposizione in corso: facciata {fatte} di {totale}")
            self.after(ATTESA_MS, self._controlla_lavoro, percorso)
            return
        self._lavoro = None
        self.barra.pack_forget()
        self.pulsante_genera.state(["!disabled"])
        if lavoro["errore"]:
            self.stato.config(text="")
            messagebox.showerror("Errore", str(lavoro["errore"]))
            return
        esito = f"Fatto: {os.path.basename(percorso)} ({lavoro['pagine']} pagine)"
        if lavoro.get("tranche"):
            esito += f" e {lavoro['tranche']} file di tranche"
        self.stato.config(text=esito)
        if self.pdf == lavoro["pdf"]:
            self.reader = imp.apri_pdf(self.pdf)   # le rotazioni sono state consumate

    def passa_misure(self):
        if not self.blocco:
            messagebox.showinfo("Nessun file", "Apri prima un PDF.")
            return
        m = imp.misure_blocco_stimate(self.piano, self.v_carta.get(), numero(self.v_rifilo, 3))
        self.app.scheda_copertina.imposta(m.altezza, m.larghezza, m.dorso,
                                          (m.dorso_min, m.dorso_max))
        self.app.note.select(1)
