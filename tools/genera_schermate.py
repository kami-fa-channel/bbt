"""Genera le schermate del README (docs/img/*.png) con dati di esempio.

Serve un display.  Su Linux senza schermo:

    xvfb-run -a -s "-screen 0 1400x1000x24" python tools/genera_schermate.py

Servono anche pillow e pypdfium2 (per mostrare il contenuto delle pagine
nell'anteprima).  Il PDF di esempio, la cartella di configurazione e i font in
cache stanno in una cartella temporanea: non si tocca niente della tua home.
"""

import os
import random
import sys
import tempfile
import time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
USCITA = RADICE / "docs" / "img"

# Prima di importare il programma: la configurazione va in una cartella temporanea.
TEMP = tempfile.mkdtemp(prefix="legatoria_schermate_")
os.environ["HOME"] = os.environ["USERPROFILE"] = TEMP
sys.path.insert(0, str(RADICE))

import tkinter as tk                                    # noqa: E402
from tkinter import filedialog, ttk                     # noqa: E402

from PIL import Image, ImageGrab                        # noqa: E402
from reportlab.lib.styles import ParagraphStyle         # noqa: E402
from reportlab.lib.enums import TA_JUSTIFY              # noqa: E402
from reportlab.pdfgen import canvas                     # noqa: E402
from reportlab.platypus import Frame, Paragraph         # noqa: E402

from legatoria.gui.app import App                       # noqa: E402

LARGHEZZA, ALTEZZA = 1180, 880
CARATTERI_PREFERITI = ("Liberation Serif", "Caladea", "DejaVu Serif")
PAROLE = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor "
          "incididunt ut labore et dolore magna aliqua ut enim ad minim veniam quis nostrud "
          "exercitation ullamco laboris nisi aliquip ex ea commodo consequat duis aute irure "
          "in reprehenderit in voluptate velit esse cillum eu fugiat nulla pariatur excepteur "
          "sint occaecat cupidatat non proident sunt in culpa qui officia deserunt mollit anim "
          "id est laborum").split()


def crea_pdf_di_esempio(percorso, pagine=240):
    """Un libro finto in A5: testo segnaposto, titolo corrente e numero di pagina."""
    caso = random.Random(7)
    w, h = 148 * 72 / 25.4, 210 * 72 / 25.4
    stile = ParagraphStyle("corpo", fontName="Times-Roman", fontSize=10.5, leading=14.5,
                           alignment=TA_JUSTIFY, firstLineIndent=14)
    c = canvas.Canvas(str(percorso), pagesize=(w, h))
    for n in range(1, pagine + 1):
        c.setFont("Times-Italic", 8)
        c.drawString(20 * 72 / 25.4, h - 14 * 72 / 25.4, "Titolo del libro" if n % 2 else "Nome dell'autore")
        c.setFont("Times-Roman", 9)
        c.drawCentredString(w / 2, 12 * 72 / 25.4, str(n))
        cornice = Frame(20 * 72 / 25.4, 22 * 72 / 25.4, w - 40 * 72 / 25.4, h - 46 * 72 / 25.4,
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        blocchi = []
        for _ in range(4):
            frase = " ".join(caso.choice(PAROLE) for _ in range(caso.randint(70, 110)))
            blocchi.append(Paragraph(frase.capitalize() + ".", stile))
        cornice.addFromList(blocchi, c)
        c.showPage()
    c.save()


def aspetta(root, secondi=0.6):
    fine = time.time() + secondi
    while time.time() < fine:
        root.update()
        time.sleep(0.03)


def cattura(root, nome):
    aspetta(root)
    x, y = root.winfo_rootx(), root.winfo_rooty()
    img = ImageGrab.grab(bbox=(x, y, x + root.winfo_width(), y + root.winfo_height()))
    # bordo sottile, cosi' l'immagine si stacca dalla pagina; poi palette ridotta per pesare meno
    bordo = Image.new("RGB", (img.width + 2, img.height + 2), "#9a9a9a")
    bordo.paste(img, (1, 1))
    bordo.quantize(colors=128, dither=Image.Dither.NONE).save(USCITA / nome, optimize=True)
    print("  scritta", USCITA / nome)


def sequenza(root, app, pdf):
    # ---- Imposizione: un libro da 240 pagine, guardia e una bianca di correzione
    filedialog.askopenfilename = lambda **k: str(pdf)
    imp = app.scheda_imposizione
    imp.apri()
    imp.v_guardie.set("1")
    imp.v_pos.set("4")
    imp.n_fasc.set(2)
    imp.n_facc.set(1)
    imp.disegna()
    cattura(root, "finestra-imposizione.png")

    # ---- Copertina: l'esempio del manuale (blocco A5 da 48 mm)
    app.note.select(1)
    cop = app.scheda_copertina
    cop.v_h.set("210")
    cop.v_l.set("145")
    cop.v_d.set("48")
    cop.v_unghia.set("3")
    cop.v_cartone.set("3")
    cop.v_gola.set("5")
    cattura(root, "finestra-copertina.png")

    # ---- Tasselli: aspetto la lettura dei font di sistema e scelgo un carattere con le grazie
    app.note.select(2)
    tas = app.scheda_tasselli
    if tas is not None:
        fine = time.time() + 60
        while not tas.fonts and time.time() < fine:
            aspetta(root, 0.2)
        if not tas.fonts:
            sys.exit("Errore: la lettura dei font non e' finita in 60 secondi.")
        scelti = [f for f in tas.fonts if f.supported and f.style == "Regular"]
        for famiglia in CARATTERI_PREFERITI:
            trovati = [f for f in scelti if f.family == famiglia]
            if trovati:
                tas._seleziona((trovati[0].path, trovati[0].index))
                break
        aspetta(root, 0.8)
        tas.vars["decoro_modello"].set("greca continua")
        aspetta(root, 0.3)
        cattura(root, "finestra-tasselli.png")
    else:
        print("  scheda Tasselli non disponibile (manca reportlab o fonttools): schermata saltata")
    app.chiudi()


def main():
    USCITA.mkdir(parents=True, exist_ok=True)
    pdf = Path(TEMP) / "esempio.pdf"
    crea_pdf_di_esempio(pdf)

    root = tk.Tk()
    root.call("tk", "scaling", 1.2)
    stile = ttk.Style(root)
    if "clam" in stile.theme_names():
        stile.theme_use("clam")
    app = App(root)
    root.geometry(f"{LARGHEZZA}x{ALTEZZA}+0+0")
    # La lettura dei font usa un thread che parla con la finestra solo dentro il
    # mainloop: la sequenza quindi parte da li'.
    root.after(500, lambda: sequenza(root, app, pdf))
    root.mainloop()


if __name__ == "__main__":
    main()
