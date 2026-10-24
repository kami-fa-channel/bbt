"""Scheda Copertina: misure dei pezzi della cassa o della brossura."""

import importlib.util
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import copertina as mc
from .comuni import (C_FONDO, C_PAGINA, C_PIEGA, C_SEGNO, applica_variabili, campo,
                     leggi_variabili, numero, testo_scrollabile)


class SchedaCopertina(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=8)
        self.app = app
        self.ultimo = None
        self.in_aggiornamento = False
        self.da_imposizione = False

        sinistra = ttk.Frame(self)
        sinistra.pack(side="left", fill="y", padx=(0, 10))
        destra = ttk.Frame(self)
        destra.pack(side="right", fill="both", expand=True)

        self.form(sinistra)

        divisore = ttk.PanedWindow(destra, orient="vertical")
        divisore.pack(fill="both", expand=True)

        cornice_canvas = ttk.Frame(divisore)
        self.canvas = tk.Canvas(cornice_canvas, bg=C_FONDO, highlightthickness=1,
                                highlightbackground="#d8d8d0")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.aggiorna())
        divisore.add(cornice_canvas, weight=3)

        cornice_testo = ttk.Frame(divisore)
        self.testo = testo_scrollabile(cornice_testo, "white")
        divisore.add(cornice_testo, weight=2)
        self.aggiorna()

    def form(self, p):
        ttk.Label(p, text="Blocco libro finito", font=("", 10, "bold")).pack(anchor="w")
        ttk.Label(p, text="misure in mm, dopo cucitura,\nrifilo e arrotondatura",
                  foreground="#777").pack(anchor="w", pady=(0, 6))
        self.v_h = campo(p, "Altezza pagina", "210", self.misura_cambiata, 8)
        self.v_l = campo(p, "Larghezza pagina", "145", self.misura_cambiata, 8)
        self.v_d = campo(p, "Dorso (arco)", "48", self.misura_cambiata, 8)
        ttk.Label(p, text="sempre modificabili a mano",
                  foreground="#777").pack(anchor="w")

        ttk.Separator(p).pack(fill="x", pady=8)
        self.v_leg = tk.StringVar(value="rigida")
        self.v_leg.trace_add("write", lambda *_: self.aggiorna())
        ttk.Radiobutton(p, text="Copertina rigida", variable=self.v_leg,
                        value="rigida").pack(anchor="w")
        ttk.Radiobutton(p, text="Brossura", variable=self.v_leg,
                        value="brossura").pack(anchor="w")

        ttk.Separator(p).pack(fill="x", pady=8)
        ttk.Label(p, text="Parametri", font=("", 10, "bold")).pack(anchor="w")
        ttk.Label(p, text="vuoto = valore automatico",
                  foreground="#777").pack(anchor="w", pady=(0, 6))
        self.v_unghia = campo(p, "Unghia", "", self.aggiorna, 8)
        self.v_cartone = campo(p, "Cartone dei piatti", "", self.aggiorna, 8)
        self.v_gola = campo(p, "Gola", "", self.aggiorna, 8)
        self.v_cerniera = campo(p, "Cerniere (brossura)", "7", self.aggiorna, 8)
        self.v_rimbocco = campo(p, "Rimbocco", "15", self.aggiorna, 8)

        self.v_indorsato = tk.BooleanVar(value=False)
        self.v_cavo = tk.BooleanVar(value=True)
        for var, testo in ((self.v_indorsato, "Cerniere formate col martello"),
                           (self.v_cavo, "Dorso cavo")):
            var.trace_add("write", lambda *_: self.aggiorna())
            ttk.Checkbutton(p, text=testo, variable=var).pack(anchor="w")

        ttk.Separator(p).pack(fill="x", pady=8)
        ttk.Button(p, text="Esporta sagoma PDF 1:1",
                   command=self.esporta_pdf).pack(fill="x", pady=2)
        ttk.Button(p, text="Copia la lista negli appunti",
                   command=self.copia).pack(fill="x", pady=2)
        self.stato = ttk.Label(p, text="", foreground="#777", wraplength=210)
        self.stato.pack(anchor="w", pady=(8, 0))

    def variabili(self):
        return {"altezza": self.v_h, "larghezza": self.v_l, "dorso": self.v_d,
                "legatura": self.v_leg, "unghia": self.v_unghia, "cartone": self.v_cartone,
                "gola": self.v_gola, "cerniera": self.v_cerniera, "rimbocco": self.v_rimbocco,
                "indorsato": self.v_indorsato, "cavo": self.v_cavo}

    def impostazioni(self):
        return leggi_variabili(self.variabili())

    def applica(self, dati):
        applica_variabili(self.variabili(), dati, {"legatura": ("rigida", "brossura")})

    def misura_cambiata(self):
        """Le misure trasferite sono solo un punto di partenza: appena l'utente
        ne corregge una, l'avviso sul trasferimento non serve piu'."""
        if self.da_imposizione:
            self.da_imposizione = False
            self.stato.config(text="")
        self.aggiorna()

    def imposta(self, H, L, D, intervallo_dorso=None):
        """Porta qui le misure stimate dall'imposizione.

        intervallo_dorso, se c'e', e' (minimo, massimo) del dorso possibile: D e'
        il valore di mezzo e l'avviso dice quanto puo' scostarsi.
        """
        self.v_h.set(f"{H:g}")
        self.v_l.set(f"{L:g}")
        self.v_d.set(f"{D:.1f}")
        self.da_imposizione = True
        testo = "Misure stimate dall'imposizione: buone per ordinare i materiali. "
        if intervallo_dorso and abs(intervallo_dorso[1] - intervallo_dorso[0]) < 1e-9:
            testo += (f"Il dorso ({D:.1f} mm) e' calcolato con il filo che hai indicato; "
                      "dipende comunque da quanto tiri il filo e batti il dorso. ")
        elif intervallo_dorso:
            testo += (f"Il dorso ({D:.1f} mm) e' il valore di mezzo: puo' andare da "
                      f"{intervallo_dorso[0]:.1f} a {intervallo_dorso[1]:.1f} mm secondo "
                      "quanto tiri il filo e batti il dorso. ")
        testo += "Correggile a mano con le misure vere del blocco cucito, soprattutto il dorso."
        self.stato.config(text=testo)

    def opzioni(self):
        def opz(var):
            v = numero(var, 0)
            return v if v > 0 else None
        H, L, D = numero(self.v_h, 0), numero(self.v_l, 0), numero(self.v_d, 0)
        if min(H, L, D) <= 0:
            raise ValueError
        return mc.opzioni(H, L, D, self.v_leg.get(), opz(self.v_unghia),
                          opz(self.v_cartone), opz(self.v_gola),
                          self.v_indorsato.get(), self.v_cavo.get(),
                          opz(self.v_cerniera) or 7.0, opz(self.v_rimbocco) or 15.0)

    def aggiorna(self):
        if self.in_aggiornamento:
            return
        self.in_aggiornamento = True
        try:
            try:
                a = self.opzioni()
            except ValueError:
                self.canvas.delete("all")
                self.canvas.create_text(20, 20, anchor="nw", fill="#999",
                                        text="Inserisci altezza, larghezza e dorso.")
                return
            r = mc.calcola(a)
            self.ultimo = (a, r)
            # i campi lasciati vuoti mostrano in grigio il valore automatico in uso
            # (la brossura non ha ne' cartone ne' gola)
            rigida = a.legatura == "rigida"
            for var, valore, serve in ((self.v_unghia, a.unghia, True),
                                       (self.v_cartone, a.cartone, rigida),
                                       (self.v_gola, a.gola, rigida)):
                var.segnaposto(mc.fmt(valore) if serve else "")
            self.disegna(a, r)
            self.testo.delete("1.0", "end")
            self.testo.insert("1.0", "\n".join(mc.righe_testo(a, r)))
        finally:
            self.in_aggiornamento = False

    def disegna(self, a, r):
        c = self.canvas
        c.delete("all")
        W = c.winfo_width() or 700
        H = c.winfo_height() or 400
        bordo = 60
        tot_h, tot_l = r["rivestimento"] if a.legatura == "rigida" else r["copertina"]
        k = min((W - 2 * bordo) / tot_l, (H - 2 * bordo) / tot_h)
        if k <= 0:
            return
        x0 = (W - tot_l * k) / 2
        y0 = (H - tot_h * k) / 2

        def rect(mx0, my0, mx1, my1, **kw):
            c.create_rectangle(x0 + mx0 * k, y0 + my0 * k,
                               x0 + mx1 * k, y0 + my1 * k, **kw)

        def quota(mx0, mx1, my, testo):
            xa, xb, y = x0 + mx0 * k, x0 + mx1 * k, y0 + my * k
            c.create_line(xa, y, xb, y, fill=C_SEGNO, arrow="both", arrowshape=(6, 7, 2))
            c.create_text((xa + xb) / 2, y - 8, text=testo, fill=C_SEGNO, font=("", 8))

        if a.legatura == "rigida":
            piatto_h, piatto_l = r["piatto"]
            g, rim, dorso_l = r["gola"], a.rimbocco, r["dorso_cartoncino"]
            rect(0, 0, tot_l, tot_h, outline="#888880", dash=(4, 3))
            x = rim
            for nome, larg, colore in (("piatto", piatto_l, C_PAGINA),
                                       (None, g, None),
                                       ("dorso", dorso_l, C_PIEGA),
                                       (None, g, None),
                                       ("piatto", piatto_l, C_PAGINA)):
                if nome:
                    rect(x, rim, x + larg, rim + piatto_h, outline=colore, width=2)
                    c.create_text(x0 + (x + larg / 2) * k, y0 + (rim + piatto_h / 2) * k,
                                  text=nome, fill=colore)
                else:
                    c.create_text(x0 + (x + larg / 2) * k, y0 + (rim - 5) * k,
                                  text="gola", fill=C_SEGNO, font=("", 7))
                x += larg
            quota(0, tot_l, -14, f"rivestimento {mc.fmt(tot_l)}")
            quota(rim, rim + piatto_l, tot_h + 22, f"piatto {mc.fmt(piatto_l)}")
            quota(rim + piatto_l + g, rim + piatto_l + g + dorso_l, tot_h + 22,
                  f"dorso {mc.fmt(dorso_l)}")
            c.create_text(x0 - 10, y0 + tot_h / 2 * k, anchor="e", fill=C_SEGNO,
                          font=("", 8),
                          text=f"{mc.fmt(tot_h)}\n(piatto {mc.fmt(piatto_h)})")
        else:
            cop_h, cop_l = r["copertina"]
            rect(0, 0, cop_l, cop_h, outline=C_PAGINA, width=2)
            for x, _ in r["cordonature"]:
                c.create_line(x0 + x * k, y0, x0 + x * k, y0 + cop_h * k,
                              fill=C_PIEGA, dash=(5, 3))
                c.create_text(x0 + x * k, y0 + cop_h * k + 10, text=mc.fmt(x),
                              fill=C_PIEGA, font=("", 7))
            quota(0, cop_l, -14, f"copertina {mc.fmt(cop_l)}")
            c.create_text(x0 - 10, y0 + cop_h / 2 * k, anchor="e", fill=C_SEGNO,
                          font=("", 8), text=mc.fmt(cop_h))
            xd0, xd1 = r["cordonature"][1][0], r["cordonature"][2][0]
            c.create_text(x0 + (xd0 + xd1) / 2 * k, y0 + cop_h / 2 * k,
                          text="dorso", fill=C_PIEGA)
        for mx, my0, my1 in mc.frecce_fibra(a, r):
            c.create_line(x0 + mx * k, y0 + my0 * k, x0 + mx * k, y0 + my1 * k, fill="#444",
                          width=2, arrow="both", arrowshape=(9, 11, 4))
        c.create_text(x0, y0 + tot_h * k + 40, anchor="nw", fill="#999", font=("", 8),
                      text=f"{r['consiglio']}  ·  le frecce mostrano il senso della fibra: "
                           "parallela al dorso, cioè verticale in questo disegno")

    def copia(self):
        if not self.ultimo:
            return
        a, r = self.ultimo
        self.clipboard_clear()
        self.clipboard_append("\n".join(mc.righe_testo(a, r)))
        self.stato.config(text="Lista copiata negli appunti.")

    def esporta_pdf(self):
        if not self.ultimo:
            return
        if importlib.util.find_spec("reportlab") is None:
            messagebox.showerror("reportlab mancante",
                                 "Per la sagoma PDF serve reportlab:\n\npip install reportlab")
            return
        a, r = self.ultimo
        percorso = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                initialfile="sagoma_copertina.pdf",
                                                filetypes=[("PDF", "*.pdf")])
        if not percorso:
            return
        mc.esporta_sagoma(a, r, percorso)
        self.stato.config(text=f"Salvato: {os.path.basename(percorso)}")

