"""Finestra principale: le tre schede in un'unica applicazione."""

import tkinter as tk
from tkinter import ttk

from .comuni import leggi_impostazioni, scrivi_impostazioni
from .scheda_copertina import SchedaCopertina
from .scheda_imposizione import SchedaImposizione

# La scheda Tasselli e' facoltativa: se mancano reportlab o fonttools la finestra
# parte lo stesso e al suo posto mostra come rimediare.
try:
    from .scheda_tasselli import SchedaTasselli
    ERRORE_TASSELLI = None
except ImportError as e:
    SchedaTasselli = None
    ERRORE_TASSELLI = str(e)


class App:
    def __init__(self, root):
        self.root = root
        root.title("bbt")
        root.minsize(1020, 680)
        self.note = ttk.Notebook(root)
        self.note.pack(fill="both", expand=True)
        self.scheda_imposizione = SchedaImposizione(self.note, self)
        self.scheda_copertina = SchedaCopertina(self.note, self)
        self.note.add(self.scheda_imposizione, text="  Imposizione  ")
        self.note.add(self.scheda_copertina, text="  Copertina  ")

        self.scheda_tasselli = None
        if SchedaTasselli is not None:
            self.scheda_tasselli = SchedaTasselli(self.note)
            self.note.add(self.scheda_tasselli, text="  Tasselli  ")
        else:
            segnaposto = ttk.Frame(self.note, padding=20)
            ttk.Label(segnaposto, justify="left", wraplength=560,
                      text="La scheda Tasselli non e' disponibile.\n\n"
                           f"{ERRORE_TASSELLI}\n\n"
                           "Installa le dipendenze:\n"
                           "    pip install reportlab fonttools"
                      ).pack(anchor="nw")
            self.note.add(segnaposto, text="  Tasselli  ")

        self.ripristina_impostazioni()
        root.protocol("WM_DELETE_WINDOW", self.chiudi)

    def ripristina_impostazioni(self):
        """Rimette le impostazioni dell'ultima volta; se qualcosa non torna si parte da zero."""
        dati = leggi_impostazioni()
        for nome, scheda in (("imposizione", self.scheda_imposizione),
                             ("copertina", self.scheda_copertina)):
            try:
                scheda.applica(dati.get(nome, {}) if isinstance(dati.get(nome), dict) else {})
            except Exception:
                pass

    def salva_impostazioni(self):
        try:
            scrivi_impostazioni({"imposizione": self.scheda_imposizione.impostazioni(),
                                 "copertina": self.scheda_copertina.impostazioni()})
        except Exception:
            pass

    def chiudi(self):
        """Salva lo stato delle schede che lo prevedono, poi chiude."""
        self.salva_impostazioni()
        if self.scheda_tasselli is not None:
            try:
                self.scheda_tasselli.chiudi()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        root.call("tk", "scaling", 1.2)
    except tk.TclError:
        pass
    stile = ttk.Style(root)
    if "clam" in stile.theme_names():
        stile.theme_use("clam")
    App(root)
    root.mainloop()
