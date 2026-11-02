"""Scheda Preparazione: divide il PDF in volumi e aggiunge le pagine per gli appunti,
prima dell'imposizione."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import imposizione as imp
from .. import volumi as vol
from ..errori import ErroreLegatoria
from .comuni import C_FONDO, applica_variabili, campo, intero, numero, testo_scrollabile


LATI = ("a sinistra", "a destra")
NESSUNA = "nessuna"


class SchedaVolumi(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.pdf = None
        self.n_pagine = 0
        self.scritti = []           # i volumi appena scritti

        sinistra = ttk.Frame(self)
        sinistra.pack(side="left", fill="y", padx=(0, 10))
        destra = ttk.Frame(self)
        destra.pack(side="right", fill="both", expand=True)

        ttk.Button(sinistra, text="Apri PDF...", command=self.apri).pack(fill="x")
        self.et_file = ttk.Label(sinistra, text="nessun file", foreground="#777",
                                 wraplength=210)
        self.et_file.pack(anchor="w", pady=(4, 8))

        ttk.Label(sinistra, text="Punti di taglio", font=("", 10, "bold")).pack(anchor="w")
        self.v_tagli = tk.StringVar()
        self.v_tagli.trace_add("write", lambda *_: self.aggiorna())
        ttk.Entry(sinistra, textvariable=self.v_tagli, width=24).pack(fill="x", pady=(2, 0))
        ttk.Label(sinistra, foreground="#777", wraplength=210, justify="left",
                  text="Ultima pagina di ogni volume tranne l'ultimo, contata sul PDF "
                       "originale, separate da virgole: 240 dà 1-240 e 241-fine.").pack(anchor="w")

        f = ttk.Frame(sinistra)
        f.pack(fill="x", pady=(8, 0))
        ttk.Label(f, text="Oppure in").pack(side="left")
        self.v_parti = tk.StringVar(value="2")
        ttk.Spinbox(f, from_=2, to=99, width=4, textvariable=self.v_parti).pack(side="left", padx=4)
        ttk.Button(f, text="parti uguali", command=self.parti_uguali).pack(side="left")

        ttk.Separator(sinistra).pack(fill="x", pady=8)
        ttk.Label(sinistra, text="Pagine per appunti", font=("", 10, "bold")).pack(anchor="w")
        self.v_lato = tk.StringVar(value=NESSUNA)
        self.v_tipo = tk.StringVar(value="quadretti")
        self.v_lato.trace_add("write", lambda *_: self.aggiorna())
        f = ttk.Frame(sinistra)
        f.pack(fill="x", pady=1)
        ttk.Label(f, text="Pagina accanto", width=22).pack(side="left")
        ttk.Combobox(f, textvariable=self.v_lato, width=9, state="readonly",
                     values=(NESSUNA, *LATI)).pack(side="left")
        f = ttk.Frame(sinistra)
        f.pack(fill="x", pady=1)
        ttk.Label(f, text="Tipo", width=22).pack(side="left")
        cb = ttk.Combobox(f, textvariable=self.v_tipo, width=9, state="readonly",
                          values=vol.TIPI)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", self.cambia_tipo)
        self.v_passo = campo(sinistra, "Passo (mm)", "5", self.aggiorna)
        self.v_spessore = campo(sinistra, "Spessore linee (mm)", "0.1", self.aggiorna)
        self.v_margine = campo(sinistra, "Margine (mm)", "10", self.aggiorna)
        ttk.Label(sinistra, foreground="#777", wraplength=210, justify="left",
                  text="Una pagina per appunti accanto a ogni pagina del libro, e una "
                       "bianca all'inizio perche' restino affiancate a libro aperto. "
                       "Il volume raddoppia.").pack(anchor="w")

        ttk.Separator(sinistra).pack(fill="x", pady=8)
        self.b_dividi = ttk.Button(sinistra, text="Prepara", command=self.dividi, state="disabled")
        self.b_dividi.pack(fill="x")
        ttk.Label(sinistra, foreground="#777", wraplength=210, justify="left",
                  text="I file si salvano accanto all'originale: nome_vol1.pdf, "
                       "nome_vol2.pdf, ... (con gli appunti: nome_vol1_appunti.pdf).").pack(
                           anchor="w", pady=(4, 0))

        ttk.Separator(sinistra).pack(fill="x", pady=8)
        ttk.Label(sinistra, text="Poi, imponi il file", font=("", 10, "bold")).pack(anchor="w")
        self.v_volume = tk.StringVar()
        self.cb_volume = ttk.Combobox(sinistra, textvariable=self.v_volume, state="readonly",
                                      width=24)
        self.cb_volume.pack(fill="x", pady=2)
        self.b_imponi = ttk.Button(sinistra, text="Apri nell'Imposizione",
                                   command=self.apri_in_imposizione, state="disabled")
        self.b_imponi.pack(fill="x")

        self.stato = ttk.Label(destra, text="", foreground="#777")
        self.stato.pack(anchor="w")
        cornice = ttk.Frame(destra)
        cornice.pack(fill="both", expand=True, pady=6)
        self.testo = testo_scrollabile(cornice, C_FONDO)
        self.aggiorna()

    # -- ricordare e ripristinare ------------------------------------------

    def impostazioni(self):
        return {"pdf": self.pdf, "tagli": self.v_tagli.get(), "lato": self.v_lato.get(),
                "tipo": self.v_tipo.get(), "passo": self.v_passo.get(),
                "spessore": self.v_spessore.get(), "margine": self.v_margine.get()}

    def applica(self, dati):
        applica_variabili({"lato": self.v_lato, "tipo": self.v_tipo, "passo": self.v_passo,
                           "spessore": self.v_spessore,
                           "margine": self.v_margine}, dati,
                          {"lato": (NESSUNA, *LATI), "tipo": vol.TIPI})
        pdf = dati.get("pdf")
        if isinstance(pdf, str) and os.path.isfile(pdf):
            self.carica(pdf, avvisa=False)
            tagli = dati.get("tagli")
            if isinstance(tagli, str):
                self.v_tagli.set(tagli)

    # -- il PDF ---------------------------------------------------------------

    def apri(self):
        percorso = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if percorso:
            self.carica(percorso)

    def carica(self, percorso, avvisa=True):
        try:
            n = len(imp.apri_pdf(percorso).pages)
        except Exception as e:
            if avvisa:
                messagebox.showerror("Errore", f"Non riesco a leggere il PDF:\n{e}")
            return
        self.pdf, self.n_pagine = percorso, n
        self.v_tagli.set("")
        self.scritti = []
        self.cb_volume.config(values=())
        self.v_volume.set("")
        self.b_imponi.config(state="disabled")
        self.et_file.config(text=f"{os.path.basename(percorso)} ({n} pagine)")
        self.aggiorna()

    # -- i volumi -------------------------------------------------------------

    def parti_uguali(self):
        if not self.pdf:
            return
        try:
            self.v_tagli.set(", ".join(map(str, vol.tagli_uguali(self.n_pagine,
                                                                 intero(self.v_parti, 2)))))
        except ErroreLegatoria as e:
            messagebox.showerror("Errore", str(e))

    def cambia_tipo(self, evento=None):
        self.v_passo.set(f"{vol.PASSO_DEFAULT[self.v_tipo.get()]:g}")

    def appunti(self):
        """Gli appunti scelti, o None se non se ne vogliono."""
        lato = self.v_lato.get()
        if lato not in LATI:
            return None
        return vol.Appunti(lato.split()[-1], self.v_tipo.get(), numero(self.v_passo, 5.0),
                           numero(self.v_margine, 10.0), numero(self.v_spessore, 0.1))

    def piano(self):
        """([(prima, ultima)] dei volumi, errore): uno solo dei due e' None."""
        try:
            appunti = self.appunti()
            if appunti:
                appunti.controlla()
            return vol.intervalli(self.n_pagine, vol.leggi_tagli(self.v_tagli.get())), None
        except ErroreLegatoria as e:
            return None, str(e)

    def aggiorna(self):
        self.testo.config(state="normal")
        self.testo.delete("1.0", "end")
        piano, errore = self.piano() if self.pdf else (None, None)
        if not self.pdf:
            self.stato.config(text="Apri un PDF per dividerlo in volumi.", foreground="#777")
        elif errore:
            self.stato.config(text=errore, foreground="#a04020")
        elif len(piano) == 1 and not self.appunti():
            self.stato.config(text="Scrivi almeno un punto di taglio o scegli le pagine "
                                   "per appunti.", foreground="#777")
        else:
            appunti = self.appunti() is not None
            self.stato.config(text=f"{len(piano)} volum{'e' if len(piano) == 1 else 'i'}",
                              foreground="#1d7a5a")
            nomi = vol.percorsi_volumi(self.pdf, len(piano), None, appunti)
            self.testo.insert("end", "Volume  Pagine originali  Pagine"
                                     + ("  Con appunti" if appunti else "") + "\n")
            for i, ((a, b), nome) in enumerate(zip(piano, nomi), 1):
                n = b - a + 1
                self.testo.insert("end", f"{i:>6}  {f'{a}-{b}':>16}  {n:>7}"
                                         + (f"  {2 * n + 1:>11}" if appunti else "")
                                         + f"   {nome.name}\n")
        self.testo.config(state="disabled")
        pronto = bool(self.pdf and piano and (len(piano) > 1 or self.appunti()))
        self.b_dividi.config(state="normal" if pronto else "disabled")

    def dividi(self):
        piano, errore = self.piano()
        appunti = self.appunti()
        if not piano or (len(piano) < 2 and not appunti):
            return
        tagli = [b for _, b in piano[:-1]]
        esistenti = [u.name for u in vol.percorsi_volumi(self.pdf, len(piano), None,
                                                         appunti is not None) if u.exists()]
        if esistenti and not messagebox.askyesno(
                "Sovrascrivere?", "Esistono gia':\n" + "\n".join(esistenti) + "\n\nSovrascriverli?"):
            return
        try:
            self.scritti = vol.dividi(self.pdf, tagli, sovrascrivi=True, appunti=appunti)
        except Exception as e:
            messagebox.showerror("Errore", str(e))
            return
        nomi = [u.name for u in self.scritti]
        self.cb_volume.config(values=nomi)
        self.v_volume.set(nomi[0])
        self.b_imponi.config(state="normal")
        self.stato.config(text=f"Fatto: {len(nomi)} file in {self.scritti[0].parent}",
                          foreground="#1d7a5a")

    def apri_in_imposizione(self):
        scelto = self.v_volume.get()
        percorso = next((u for u in self.scritti if u.name == scelto), None)
        if percorso is None:
            return
        imposizione = self.app.scheda_imposizione
        imposizione.carica(str(percorso))
        self.app.note.select(imposizione)
