"""Colori e piccoli aiuti condivisi dalle schede."""

import tkinter as tk
from tkinter import ttk

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
    ttk.Entry(f, textvariable=var, width=larghezza).pack(side="left")
    return var


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
