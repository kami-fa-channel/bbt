"""Colori e piccoli aiuti condivisi dalle schede."""

import json
import os
import tkinter as tk
from tkinter import ttk

# le impostazioni delle schede Imposizione e Copertina, nella stessa cartella
# dell'ultimo libro di Tasselli
IMPOSTAZIONI = os.path.join(os.path.expanduser("~"), ".tasselli_legatoria",
                            "impostazioni.json")


def leggi_impostazioni():
    """Le impostazioni salvate all'ultima chiusura, o {} se mancano o sono illeggibili."""
    try:
        with open(IMPOSTAZIONI, encoding="utf-8") as fh:
            dati = json.load(fh)
        return dati if isinstance(dati, dict) else {}
    except (OSError, ValueError):
        return {}


def scrivi_impostazioni(dati):
    os.makedirs(os.path.dirname(IMPOSTAZIONI), exist_ok=True)
    temporaneo = IMPOSTAZIONI + ".tmp"
    with open(temporaneo, "w", encoding="utf-8") as fh:
        json.dump(dati, fh, indent=1, ensure_ascii=False)
    os.replace(temporaneo, IMPOSTAZIONI)      # un file a meta' non resta mai


def leggi_variabili(variabili):
    """{nome: valore} delle variabili tk di `variabili` ({nome: variabile})."""
    return {nome: var.get() for nome, var in variabili.items()}


def applica_variabili(variabili, dati, scelte=None):
    """Rimette in `variabili` i valori di `dati`, saltando quelli del tipo sbagliato.

    `scelte` ({nome: valori ammessi}) limita i campi a un elenco fisso."""
    for nome, var in variabili.items():
        valore = dati.get(nome)
        if isinstance(var, tk.BooleanVar):
            if isinstance(valore, bool):
                var.set(valore)
        elif isinstance(valore, str) and valore in (scelte or {}).get(nome, [valore]):
            var.set(valore)

C_FOGLIO = "#d8d8d0"
C_PAGINA = "#4a4a8a"
C_BIANCA = "#b8b8b0"
C_PIEGA = "#1d7a5a"
C_SEGNO = "#a04020"
C_FONDO = "#fbfbf9"


def testo_scrollabile(parent, sfondo):
    """Area di testo con barre di scorrimento verticale e orizzontale."""
    testo = tk.Text(parent, font=("monospace", 9), wrap="none", bg=sfondo,
                    relief="flat", height=8)
    vsb = ttk.Scrollbar(parent, orient="vertical", command=testo.yview)
    hsb = ttk.Scrollbar(parent, orient="horizontal", command=testo.xview)
    testo.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    testo.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    return testo


class Suggerimento:
    """Un tooltip: un piccolo riquadro di testo che appare tenendo il mouse fermo
    su un widget per un momento, e sparisce muovendo il mouse o cliccando.

    Esempio:  Suggerimento(pulsante, "spiegazione del pulsante")
    """

    RITARDO_MS = 500
    LARGHEZZA_MAX = 320

    def __init__(self, widget, testo):
        self.widget = widget
        self.testo = testo
        self.finestra = None
        self._id_dopo = None
        widget.bind("<Enter>", self._programma, add="+")
        widget.bind("<Leave>", self._nascondi, add="+")
        widget.bind("<ButtonPress>", self._nascondi, add="+")
        # Il metodo bound passato a bind() referenzia self: l'istanza resta viva
        # anche senza assegnarla a una variabile, finche' il widget esiste.

    def _programma(self, evento=None):
        self._annulla()
        self._id_dopo = self.widget.after(self.RITARDO_MS, self._mostra)

    def _annulla(self):
        if self._id_dopo is not None:
            self.widget.after_cancel(self._id_dopo)
            self._id_dopo = None

    def _mostra(self):
        if self.finestra is not None or not self.widget.winfo_viewable():
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.finestra = tk.Toplevel(self.widget)
        self.finestra.wm_overrideredirect(True)          # niente bordo ne' barra del titolo
        self.finestra.wm_geometry(f"+{x}+{y}")
        try:
            self.finestra.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        ttk.Label(self.finestra, text=self.testo, justify="left", padding=(8, 5),
                  background="#ffffe0", relief="solid", borderwidth=1,
                  wraplength=self.LARGHEZZA_MAX).pack()

    def _nascondi(self, evento=None):
        self._annulla()
        if self.finestra is not None:
            self.finestra.destroy()
            self.finestra = None


def campo(parent, etichetta, valore, callback, larghezza=9):
    f = ttk.Frame(parent)
    f.pack(fill="x", pady=1)
    ttk.Label(f, text=etichetta, width=22).pack(side="left")
    var = tk.StringVar(value=valore)
    var.trace_add("write", lambda *_: callback())
    voce = ttk.Entry(f, textvariable=var, width=larghezza)
    voce.pack(side="left")
    var.segnaposto = segnaposto_in(voce, var)
    return var


def segnaposto_in(voce, var):
    """Un testo grigio dentro `voce` finche' `var` e' vuota, senza metterci niente.

    Restituisce la funzione che lo cambia: f("3") lo mostra, f("") lo toglie."""
    etichetta = tk.Label(voce, foreground="#999", background="white", borderwidth=0,
                         cursor="xterm")
    etichetta.bind("<Button-1>", lambda e: voce.focus_set())

    def aggiorna(testo=None, *_):
        if testo is not None:
            etichetta.testo = testo
        testo = getattr(etichetta, "testo", "")
        if testo and not var.get():
            etichetta.configure(text=testo)
            etichetta.place(x=3, rely=0.5, anchor="w")
        else:
            etichetta.place_forget()

    var.trace_add("write", lambda *_: aggiorna())
    return aggiorna


def numero(var, default=0.0):
    try:
        return float(var.get().strip().replace(",", "."))
    except (ValueError, AttributeError):
        return default


def intero(var, default=0):
    try:
        return int(float(var.get().strip()))
    except (ValueError, AttributeError):
        return default
