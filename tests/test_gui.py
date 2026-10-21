"""La finestra.  Servono tkinter e un display (su Linux senza schermo: xvfb-run pytest).

Di norma, se mancano, i test si saltano.  Con LEGATORIA_GUI_OBBLIGATORIA=1 (come fa
l'integrazione continua su GitHub) invece falliscono: un controllo che salta in
silenzio i test della finestra darebbe un falso verde.
"""
import os
import re
import time

import pytest

GUI_OBBLIGATORIA = os.environ.get("LEGATORIA_GUI_OBBLIGATORIA") == "1"

try:
    import tkinter as tk
except ImportError:
    if GUI_OBBLIGATORIA:
        raise
    pytest.skip("tkinter non disponibile", allow_module_level=True)
from tkinter import filedialog, messagebox, ttk

from legatoria import tasselli
from legatoria.tasselli import scan_fonts
from legatoria.gui.comuni import Suggerimento



@pytest.fixture
def app(tmp_path, monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError:
        if GUI_OBBLIGATORIA:
            pytest.fail("nessun display, ma i test della finestra sono obbligatori")
        pytest.skip("nessun display")
    from legatoria.gui import scheda_tasselli
    from legatoria.gui.app import App
    # niente scansione dei font in secondo piano ne' file nella cartella dell'utente
    monkeypatch.setattr(scheda_tasselli.SchedaTasselli, "_avvia_scansione", lambda self: None)
    monkeypatch.setattr(scheda_tasselli, "ULTIMO", str(tmp_path / "ultimo.json"))
    a = App(root)
    root.update()
    yield a
    try:
        a.chiudi()          # ferma anche i lavori pendenti della scheda Tasselli
    except tk.TclError:
        pass                # gia' chiusa dal test stesso


def test_tre_schede(app):
    nomi = [app.note.tab(i, "text").strip() for i in range(app.note.index("end"))]
    assert nomi == ["Imposizione", "Copertina", "Tasselli"]
    assert app.scheda_tasselli is not None


def test_riepilogo_con_tranche_e_tabella(app, pdf_bianco, monkeypatch):
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(200)))
    imp = app.scheda_imposizione
    imp.apri()
    testo = imp.testo.get("1.0", "end")
    assert "blocchi da circa 50 pagine" in testo
    assert "FASCICOLATURE POSSIBILI" in testo and "CONSIGLIATO" in testo
    imp.v_tranche.set("100")
    assert "blocchi da circa 100 pagine" in imp.testo.get("1.0", "end")


def attendi_generazione(app, imp, secondi=30):
    """La generazione gira in un thread: si lascia lavorare la finestra finche' ha finito."""
    fine = time.time() + secondi
    while imp._lavoro and time.time() < fine:
        app.root.update()
        time.sleep(0.01)
    assert not imp._lavoro, "la generazione non e' finita"


def test_genera_scrive_il_file(app, pdf_bianco, tmp_path, monkeypatch):
    uscita = tmp_path / "libro.pdf"
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(64)))
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **k: str(uscita))
    imp = app.scheda_imposizione
    imp.apri()
    imp.genera()
    attendi_generazione(app, imp)
    assert uscita.is_file() and imp.stato.cget("text").startswith("Fatto:")
    assert not imp.barra.winfo_ismapped()                  # a lavoro finito la barra sparisce
    assert "disabled" not in imp.pulsante_genera.state()


def test_la_barra_segue_l_imposizione(app, pdf_bianco, tmp_path, monkeypatch):
    from legatoria import imposizione
    visti, errori = [], []
    originale = imposizione.impagina

    def impagina_lenta(reader, blocco, args, fogli, percorso, avanzamento=None):
        def spia(fatte, totale):                 # gira nel thread di lavoro: niente tkinter qui
            visti.append((fatte, totale))
            avanzamento(fatte, totale)
            time.sleep(0.002)
        return originale(reader, blocco, args, fogli, percorso, spia)

    monkeypatch.setattr(imposizione, "impagina", impagina_lenta)
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: errori.append(a))
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(64)))
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **k: str(tmp_path / "l.pdf"))
    imp = app.scheda_imposizione
    imp.apri()
    imp.genera()
    assert imp.barra.winfo_manager() == "pack"             # visibile subito
    assert "disabled" in imp.pulsante_genera.state()       # e niente doppia generazione
    imp.genera()                                           # ignorato: non parte un secondo lavoro
    attendi_generazione(app, imp)
    assert not errori
    assert visti and visti[-1] == (32, 32)                 # 64 pagine = 32 facciate
    assert [v[0] for v in visti] == list(range(1, 33))


def test_margini_impossibili_non_chiudono_il_programma(app, pdf_bianco, tmp_path, monkeypatch):
    """Regressione: un sys.exit dentro la logica chiudeva l'intera finestra."""
    errori = []
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(16)))
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **k: str(tmp_path / "x.pdf"))
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: errori.append(a))
    imp = app.scheda_imposizione
    imp.apri()
    imp.v_dorso.set("100")
    imp.v_est.set("100")
    imp.genera()
    attendi_generazione(app, imp)
    assert errori and "margini" in errori[0][1]


def test_ripristina_impaginazione(app, pdf_bianco, monkeypatch):
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(16)))
    imp = app.scheda_imposizione
    imp.apri()
    imp.v_dorso.set("30")
    imp.v_scala.set("0.8")
    imp.v_shing.set("0.2")
    imp.v_segni.set(False)
    imp.ripristina_impaginazione()
    assert (imp.v_dorso.get(), imp.v_est.get(), imp.v_testa.get(), imp.v_piede.get()) == ("15", "10", "10", "10")
    assert imp.v_scala.get() == "1.0" and imp.v_shing.get() == "0"
    assert imp.v_segni.get() is True


def test_le_misure_passano_alla_copertina(app, pdf_bianco, monkeypatch):
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(200)))
    app.scheda_imposizione.apri()
    app.scheda_imposizione.passa_misure()
    assert app.note.index(app.note.select()) == 1
    assert app.scheda_copertina.v_h.get() == "210"          # lato corto dell'A4
    assert "misure stimate" in app.scheda_copertina.stato.cget("text").lower()


def test_il_dorso_stimato_e_lo_stesso_nel_riepilogo_e_nella_copertina(app, pdf_bianco, monkeypatch):
    """Regressione: i due numeri venivano da ipotesi diverse sul filo."""
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(749)))
    imp = app.scheda_imposizione
    imp.apri()
    riga = next(r for r in imp.testo.get("1.0", "end").splitlines() if r.startswith("Dorso stimato"))
    dorso, minimo, massimo = map(float, re.search(
        r"([\d.]+) mm \(fra ([\d.]+) e ([\d.]+)\)", riga).groups())
    assert minimo < dorso < massimo
    imp.passa_misure()
    cop = app.scheda_copertina
    assert float(cop.v_d.get()) == pytest.approx(dorso, abs=0.05)
    avviso = cop.stato.cget("text")
    assert f"{minimo:.1f}" in avviso and f"{massimo:.1f}" in avviso


def test_la_scritta_dell_anteprima_dice_se_il_contenuto_si_vede(app, pdf_bianco, monkeypatch):
    from legatoria.gui import scheda_imposizione
    if not scheda_imposizione.RENDERING:
        pytest.skip("servono pillow e pypdfium2 oppure pdftoppm")
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(64)))
    imp = app.scheda_imposizione
    imp.apri()

    def scritte():
        return " ".join(imp.canvas.itemcget(i, "text") for i in imp.canvas.find_all()
                        if imp.canvas.type(i) == "text")
    imp.v_render.set(True)
    app.root.update()
    assert "con il contenuto ridotto" in scritte() and "schematica" not in scritte()
    imp.v_render.set(False)
    app.root.update()
    assert "Anteprima schematica" in scritte()


def aspetta_miniature(app, imp, secondi=20):
    fine = time.time() + secondi
    while time.time() < fine:
        app.root.update()
        if imp.miniature is None or (not imp.miniature.in_attesa() and imp._attesa is None):
            break
        time.sleep(0.02)
    app.root.update()


def test_la_vista_fascicolo_mostra_tutte_le_facciate(app, pdf_numerato, monkeypatch):
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_numerato(40)))
    imp = app.scheda_imposizione
    imp.apri()
    imp.n_fasc.set(2)
    imp.disegna()
    assert imp.v_vista.get() == "fascicolo"
    c = imp.canvas
    scritte = [c.itemcget(i, "text") for i in c.find_all() if c.type(i) == "text"]
    # fogli fronte e retro, e le pagine 17-32 del libro (il secondo fascicolo, -f 4)
    for foglio in range(1, 5):
        assert f"foglio {foglio} · fronte" in scritte and f"foglio {foglio} · retro" in scritte
    numeri = sorted(int(t.split()[1]) for t in scritte if t.startswith("pag. "))
    assert numeri == list(range(17, 33))
    assert all(c.find_withtag(f"facciata{j}") for j in range(8))
    assert "pagine 17-32 del libro" in imp.et_facc.cget("text")

    imp.ingrandisci(5)                                   # come il clic sulla facciata 6
    assert imp.v_vista.get() == "foglio" and imp.n_facc.get() == 6
    assert "foglio 3 di 4, retro" in imp.et_facc.cget("text")


def test_la_rotella_sfoglia_facciate_e_fascicoli(app, pdf_bianco, monkeypatch):
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(64)))
    imp = app.scheda_imposizione
    imp.apri()
    imp.v_vista.set("foglio")
    imp.n_facc.set(8)
    imp.scorri(1)                                        # dall'ultima facciata al fascicolo dopo
    assert (imp.n_fasc.get(), imp.n_facc.get()) == (2, 1)
    imp.scorri(-1)
    assert (imp.n_fasc.get(), imp.n_facc.get()) == (1, 8)
    imp.scorri(-10)                                      # non va prima dell'inizio
    imp.scorri(-1)
    assert imp.n_fasc.get() == 1 and imp.n_facc.get() >= 1
    imp.v_vista.set("fascicolo")
    imp.n_fasc.set(imp.n_fascicoli)
    imp.scorri(1)                                        # ne' oltre la fine
    assert imp.n_fasc.get() == imp.n_fascicoli


def test_l_anteprima_mette_la_pagina_sotto_il_margine_di_testa(app, pdf_bianco, monkeypatch):
    """Regressione: l'anteprima misurava dall'alto il margine di piede."""
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(16)))
    imp = app.scheda_imposizione
    imp.apri()
    imp.v_render.set(False)
    imp.v_vista.set("foglio")
    imp.v_segni.set(False)

    def alto_e_basso():
        c = imp.canvas
        rettangoli = [c.coords(i) for i in c.find_all() if c.type(i) == "rectangle"]
        foglio, pagina = rettangoli[0], rettangoli[1]
        return pagina[1] - foglio[1], foglio[3] - pagina[3]
    imp.v_testa.set("10"); imp.v_piede.set("10")
    sopra, sotto = alto_e_basso()
    assert sopra == pytest.approx(sotto, abs=1)
    imp.v_testa.set("40")
    sopra, sotto = alto_e_basso()
    assert sopra > sotto + 5


def test_le_miniature_compaiono_nell_anteprima(app, pdf_numerato, monkeypatch):
    from legatoria.gui import scheda_imposizione
    if not scheda_imposizione.RENDERING:
        pytest.skip("servono pillow e pypdfium2 oppure pdftoppm")
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_numerato(16)))
    imp = app.scheda_imposizione
    imp.apri()
    aspetta_miniature(app, imp)
    immagini = [i for i in imp.canvas.find_all() if imp.canvas.type(i) == "image"]
    assert len(immagini) == 16                           # tutto il fascicolo, senza bianche


def test_filo_indicato_nella_finestra(app, pdf_bianco, monkeypatch):
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(749)))
    imp = app.scheda_imposizione
    imp.apri()
    n = imp.n_fascicoli
    # l'etichetta dice quanti giri fare
    assert f"{n} giri" in imp.et_filo.cget("text") and f"dividi per {n}" in imp.et_filo.cget("text")
    generico = imp.testo.get("1.0", "end")
    assert "(fra " in generico and "indicati da te" not in generico

    imp.v_filo.set("0,4")                                  # la virgola italiana deve andare bene
    testo = imp.testo.get("1.0", "end")
    assert "0.4 mm per fascicolo, indicati da te" in testo
    assert "(con il filo che hai indicato)" in testo
    riga = next(r for r in testo.splitlines() if r.startswith("Dorso stimato"))
    dorso = float(re.search(r"copertina: ([\d.]+) mm", riga).group(1))
    imp.passa_misure()
    cop = app.scheda_copertina
    assert float(cop.v_d.get()) == pytest.approx(dorso, abs=0.05)
    assert "calcolato con il filo che hai indicato" in cop.stato.cget("text")
    assert "puo' andare da" not in cop.stato.cget("text")

    imp.v_filo.set("")                                     # campo vuoto: torna la stima generica
    assert "(fra " in imp.testo.get("1.0", "end")
    imp.v_filo.set("abc")                                  # testo illeggibile: come vuoto
    assert "(fra " in imp.testo.get("1.0", "end")


def test_avviso_nella_finestra_se_il_filo_sembra_il_totale(app, pdf_bianco, monkeypatch):
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_bianco(200)))
    imp = app.scheda_imposizione
    imp.apri()
    imp.v_filo.set("12")
    assert "Attenzione: 12 mm di filo per fascicolo" in imp.testo.get("1.0", "end")
    imp.v_filo.set("0.5")
    assert "Attenzione" not in imp.testo.get("1.0", "end")


def test_la_copertina_calcola_e_esporta(app, tmp_path, monkeypatch):
    cop = app.scheda_copertina
    cop.v_d.set("48")
    cop.v_unghia.set("3"); cop.v_cartone.set("3"); cop.v_gola.set("5")
    assert "246 x 382" in cop.testo.get("1.0", "end")
    uscita = tmp_path / "sagoma.pdf"
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **k: str(uscita))
    cop.esporta_pdf()
    assert uscita.is_file()


def test_chiudendo_si_salva_l_ultimo_libro(app, tmp_path):
    app.chiudi()
    assert (tmp_path / "ultimo.json").is_file()


def toplevel_discendenti(widget):
    """I Toplevel fra i discendenti di `widget` (un tooltip e' figlio del suo widget,
    non della finestra principale: cercarlo solo fra i figli diretti di root non lo trova)."""
    trovati = []
    for figlio in widget.winfo_children():
        if isinstance(figlio, tk.Toplevel):
            trovati.append(figlio)
        trovati += toplevel_discendenti(figlio)
    return trovati


def aspetta(widget, ms):
    fine = [False]
    widget.after(ms, lambda: fine.__setitem__(0, True))
    while not fine[0]:
        widget.update()


def trova_campo(radice, tipo, variabile):
    """Il widget di classe `tipo` collegato alla variabile tk `variabile`."""
    for w in radice.winfo_children():
        try:
            if isinstance(w, tipo) and str(w.cget("textvariable")) == str(variabile):
                return w
        except tk.TclError:
            pass
        trovato = trova_campo(w, tipo, variabile)
        if trovato:
            return trovato


def rotella(campo, direzione):
    """Simula uno scatto di rotella sopra un campo: Linux (Button-4/5) e Windows/macOS (MouseWheel)."""
    campo.event_generate("<Button-4>" if direzione < 0 else "<Button-5>", x=5, y=5)
    campo.event_generate("<MouseWheel>", x=5, y=5, delta=120 if direzione < 0 else -120)


def test_la_rotella_sopra_un_campo_non_ne_cambia_il_valore(app):
    """Regressione: scorrendo il pannello con il puntatore sopra "Base da incollare" la
    sporgenza saliva da sola, e con Dorso 2 attivato compariva un pezzo non richiesto."""
    tas = app.scheda_tasselli
    app.note.select(2)
    app.root.update()
    spinbox = trova_campo(tas, ttk.Spinbox, tas.vars["t2_cornice_mm"])
    tendina = trova_campo(tas, ttk.Combobox, tas.vars["t2_composizione"])
    assert spinbox is not None and tendina is not None
    prima = (tas.vars["t2_cornice_mm"].get(), tas.vars["t2_composizione"].get())
    for direzione in (-1, 1, 1, -1, 1):
        rotella(spinbox, direzione)
        rotella(tendina, direzione)
    app.root.update()
    assert (tas.vars["t2_cornice_mm"].get(), tas.vars["t2_composizione"].get()) == prima
    assert tas.leggi_config().tasselli[2].cornice_mm == 0
    assert not any("(base)" in t.nome for t, *_ in tasselli.disponi(tas.leggi_config()))


def test_la_rotella_sopra_un_campo_scorre_il_pannello(app):
    tas = app.scheda_tasselli
    app.note.select(2)
    # Finestra bassa, cosi' il pannello e' scorrevole qualunque siano i font del sistema
    # (con altri Tk o altri caratteri l'altezza del contenuto cambia).
    app.root.minsize(300, 200)
    app.root.geometry("1100x360")
    app.root.update()
    app.root.update()
    # un campo numerico del pannello visibile (il primo scheda, "Libro"), non di una scheda nascosta
    chiave, campo = next((k, c) for k, c in ((k, trova_campo(tas, ttk.Spinbox, v)) for k, v in tas.vars.items())
                         if c is not None and c.winfo_ismapped())
    canvas = campo
    while not isinstance(canvas, tk.Canvas):
        canvas = canvas.master
    assert canvas.bbox("all")[3] > canvas.winfo_height(), "il pannello dovrebbe essere scorrevole"
    assert canvas.yview()[0] == 0
    valore = tas.vars[chiave].get()
    for _ in range(3):
        rotella(campo, +1)              # Tk 8.6 su X11 manda Button-5, Tk 9 manda MouseWheel
        app.root.update()
    assert canvas.yview()[0] > 0, f"il pannello non e' scorso (campo {chiave})"
    assert tas.vars[chiave].get() == valore


def test_la_base_da_incollare_compare_nell_anteprima_con_il_nome_giusto(app):
    tas = app.scheda_tasselli
    app.note.select(2)
    app.root.update()

    def scritte():
        return [tas.canvas.itemcget(i, "text") for i in tas.canvas.find_all()
                if tas.canvas.type(i) == "text"]
    tas._preview()
    assert not any("(base)" in x for x in scritte())
    tas.vars["t2_cornice_mm"].set("1.5")
    tas._preview()
    assert "Dorso 2 (base)" in scritte()
    assert not any("(cornice)" in x for x in scritte())


def test_suggerimento_compare_dopo_il_ritardo_e_sparisce(app):
    """Il tooltip generico usato per esempio da 'Porta le misure alla copertina'."""
    pulsante = ttk.Button(app.root, text="prova")
    pulsante.pack()
    Suggerimento(pulsante, "testo di prova")   # nessun riferimento tenuto, come nell'uso reale
    app.root.update()

    pulsante.event_generate("<Enter>", x=5, y=5)
    app.root.update()
    assert toplevel_discendenti(app.root) == [], "non deve comparire subito"

    aspetta(app.root, Suggerimento.RITARDO_MS + 200)
    tips = toplevel_discendenti(app.root)
    assert len(tips) == 1
    assert tips[0].winfo_children()[0].cget("text") == "testo di prova"

    pulsante.event_generate("<Leave>")
    app.root.update()
    assert toplevel_discendenti(app.root) == [], "deve sparire spostando via il mouse"


def test_suggerimento_sparisce_al_click_e_non_compare_se_il_mouse_passa_veloce(app):
    pulsante = ttk.Button(app.root, text="prova")
    pulsante.pack()
    Suggerimento(pulsante, "testo di prova")
    app.root.update()

    pulsante.event_generate("<Enter>", x=5, y=5)
    app.root.update()
    aspetta(app.root, Suggerimento.RITARDO_MS + 200)
    pulsante.event_generate("<ButtonPress-1>", x=5, y=5)
    app.root.update()
    assert toplevel_discendenti(app.root) == [], "un click deve nascondere il tooltip"

    pulsante.event_generate("<Enter>", x=5, y=5)
    app.root.update()
    aspetta(app.root, Suggerimento.RITARDO_MS - 200)
    pulsante.event_generate("<Leave>")
    app.root.update()
    aspetta(app.root, 400)
    assert toplevel_discendenti(app.root) == [], "via prima del ritardo, non deve comparire affatto"


def test_suggerimento_funziona_senza_essere_assegnato_a_una_variabile(app):
    """Il codice reale lo usa cosi': Suggerimento(pulsante, testo), senza tenerne
    il risultato.  Il metodo bound passato a bind() tiene in vita l'istanza."""
    import gc
    pulsante = ttk.Button(app.root, text="prova")
    pulsante.pack()
    Suggerimento(pulsante, "sopravvivo?")
    gc.collect()
    app.root.update()

    pulsante.event_generate("<Enter>", x=5, y=5)
    app.root.update()
    aspetta(app.root, Suggerimento.RITARDO_MS + 200)
    assert len(toplevel_discendenti(app.root)) == 1


def trova_pulsante(radice, testo):
    """Il ttk.Button il cui testo contiene `testo`."""
    for w in radice.winfo_children():
        if isinstance(w, ttk.Button) and testo in str(w.cget("text")):
            return w
        trovato = trova_pulsante(w, testo)
        if trovato:
            return trovato


def test_il_pulsante_porta_le_misure_ha_il_suggerimento_sulla_stima(app):
    """Il tooltip aggiunto sul pulsante spiega perche' il dorso stimato va corretto
    a mano (il dorso e' un arco, la stima e' una corda)."""
    pulsante = trova_pulsante(app.scheda_imposizione, "Porta le misure alla copertina")
    assert pulsante is not None
    app.root.update()

    pulsante.event_generate("<Enter>", x=5, y=5)
    app.root.update()
    aspetta(app.root, Suggerimento.RITARDO_MS + 200)
    tips = toplevel_discendenti(app.root)
    assert len(tips) == 1
    testo = tips[0].winfo_children()[0].cget("text")
    assert "corda" in testo and "arco" in testo and "corretto a mano" in testo


# ---------------------------------------------------------------------------
# Tasselli: linee estese dei bordi
# ---------------------------------------------------------------------------

def _linee_bordo_in_anteprima(tas):
    """Le linee blu di bordo (linee estese e crocini) disegnate nell'anteprima."""
    cv = tas.canvas
    return [i for i in cv.find_all()
            if cv.type(i) == "line" and cv.itemcget(i, "fill") == "#3a6ea5"]


def _testo_info(tas):
    return tas.lbl_info.cget("text")


def test_i_campi_delle_linee_estese_arrivano_alla_configurazione(app):
    tas = app.scheda_tasselli
    tas.vars["bordo_stile"].set("contorno + linee estese")
    tas.vars["linee_offset_mm"].set("1.5")
    tas.vars["linee_lung_mm"].set("14")
    cfg = tas.leggi_config()
    assert cfg.bordo_stile == "contorno + linee estese"
    assert (cfg.linee_offset_mm, cfg.linee_lung_mm) == (1.5, 14.0)
    from legatoria.tasselli import BORDER_STYLES
    assert "linee estese" in BORDER_STYLES and "contorno + linee estese" in BORDER_STYLES


def test_l_anteprima_disegna_le_linee_estese_solo_con_lo_stile_nuovo(app):
    tas = app.scheda_tasselli
    app.note.select(2)
    app.root.update()
    tas.vars["bordo_stile"].set("contorno")
    tas._preview()
    assert _linee_bordo_in_anteprima(tas) == []
    tas.vars["bordo_stile"].set("contorno + linee estese")
    tas._preview()
    n_pezzi = len(tas._rect_map)
    assert n_pezzi == 3
    assert len(_linee_bordo_in_anteprima(tas)) == 8 * n_pezzi
    tas.vars["bordo_stile"].set("linee estese")
    tas._preview()
    assert len(_linee_bordo_in_anteprima(tas)) == 8 * n_pezzi


def test_l_anteprima_mostra_anche_i_crocini(app):
    """Regressione: l'anteprima disegnava solo il contorno, e i crocini si vedevano
    soltanto nel PDF."""
    tas = app.scheda_tasselli
    app.note.select(2)
    app.root.update()
    tas.vars["bordo_stile"].set("contorno + crocini")
    tas._preview()
    assert len(_linee_bordo_in_anteprima(tas)) == 8 * len(tas._rect_map)


def test_la_nota_dell_anteprima_dice_quando_la_distanza_e_stata_aumentata(app):
    tas = app.scheda_tasselli
    app.note.select(2)
    app.root.update()
    tas.vars["bordo_stile"].set("contorno")
    tas._preview()
    assert "distanza fra i pezzi" not in _testo_info(tas)
    tas.vars["bordo_stile"].set("contorno + linee estese")
    tas._preview()
    assert "Linee estese: distanza fra i pezzi portata a 21.5 mm" in _testo_info(tas)
    tas.vars["gap_mm"].set("30")                     # gia' abbastanza: niente da segnalare
    tas._preview()
    assert "portata a" not in _testo_info(tas)


def test_dopo_la_generazione_la_finestra_segnala_le_linee_accorciate(app, tmp_path):
    tas = app.scheda_tasselli
    fonts = [f for f in scan_fonts(use_cache=False) if f.supported]
    if not fonts:
        pytest.skip("nessun font TrueType di sistema")
    tas.cfg.font_path, tas.cfg.font_index = fonts[0].path, fonts[0].index
    tas.vars["bordo_stile"].set("contorno + linee estese")
    assert tas._genera(str(tmp_path / "ok.pdf"))
    assert "accorciate" not in _testo_info(tas)
    tas.vars["margine_mm"].set("4")                  # pezzi quasi a filo del foglio: niente spazio per le linee
    assert tas._genera(str(tmp_path / "stretto.pdf"))
    assert "Linee di taglio accorciate, troppo vicine al bordo del foglio in:" in _testo_info(tas)


def _rettangoli_pezzi(tas, colore):
    """I rettangoli dei pezzi nell'anteprima con quel colore di contorno."""
    cv = tas.canvas
    return [i for i in cv.find_all()
            if cv.type(i) == "rectangle" and cv.itemcget(i, "outline") == colore]


@pytest.mark.parametrize("stile, contorno_blu", [
    ("contorno", True),
    ("contorno tratteggiato", True),
    ("contorno + crocini", True),
    ("contorno + linee estese", True),
    ("crocini agli angoli", False),
    ("linee estese", False),
    ("nessuno", False),
])
def test_l_anteprima_disegna_il_rettangolo_in_blu_solo_se_il_contorno_si_stampa(app, stile, contorno_blu):
    """Regressione: con "linee estese" (o "crocini agli angoli") il PDF non ha il contorno, ma
    l'anteprima disegnava comunque il rettangolo in blu, e insieme alle linee sembrava un
    cancelletto col quadretto in mezzo."""
    tas = app.scheda_tasselli
    app.note.select(2)
    app.root.update()
    tas.vars["bordo_stile"].set(stile)
    tas._preview()
    n = len(tas._rect_map)
    assert n == 3
    assert len(_rettangoli_pezzi(tas, "#3a6ea5")) == (n if contorno_blu else 0)
    assert len(_rettangoli_pezzi(tas, "#c8c8c8")) == (0 if contorno_blu else n)


def test_senza_contorno_la_nota_spiega_che_il_rettangolo_grigio_non_si_stampa(app):
    tas = app.scheda_tasselli
    app.note.select(2)
    app.root.update()
    for stile, nota in (("linee estese", True), ("crocini agli angoli", True),
                        ("contorno + linee estese", False), ("contorno", False), ("nessuno", False)):
        tas.vars["bordo_stile"].set(stile)
        tas._preview()
        assert ("rettangolo grigio" in _testo_info(tas)) is nota, stile


def test_solo_linee_estese_lascia_le_squadrette_e_toglie_il_contorno_nell_anteprima(app):
    """Il cancelletto senza il quadretto in mezzo: otto linee per pezzo, niente contorno blu."""
    tas = app.scheda_tasselli
    app.note.select(2)
    app.root.update()
    tas.vars["bordo_stile"].set("linee estese")
    tas._preview()
    n = len(tas._rect_map)
    assert len(_linee_bordo_in_anteprima(tas)) == 8 * n
    assert _rettangoli_pezzi(tas, "#3a6ea5") == []


# ---------------------------------------------------------------------------
# Tasselli: zoom dell'anteprima, spostamento della vista, calamita
# ---------------------------------------------------------------------------

from types import SimpleNamespace  # noqa: E402

from legatoria.gui import scheda_tasselli as st  # noqa: E402
from legatoria.tasselli import disponi, mm  # noqa: E402


def _ev(x, y, state=0):
    """Un evento del mouse finto, con quello che serve ai gestori della scheda."""
    return SimpleNamespace(x=x, y=y, state=state, num="??", delta=0)


def _tasselli(app):
    """La scheda Tasselli, visibile, con l'anteprima disegnata."""
    tas = app.scheda_tasselli
    app.note.select(2)
    app.root.geometry("1180x760")
    app.root.update()
    app.root.update()
    tas._preview()
    return tas


def _vista(tas):
    return tas._canvas_scale(tas.leggi_config())      # scala, x, y, larghezza, altezza (punti)


def _schermo(tas, x_mm, y_mm_dall_alto):
    """Dove sta sullo schermo un punto del foglio (mm dall'angolo alto a sinistra)."""
    s, ox, oy, _pw, _ph = _vista(tas)
    return ox + x_mm * mm * s, oy + y_mm_dall_alto * mm * s


def _centro_pezzo(tas, i):
    s, ox, oy, _pw, ph = _vista(tas)
    _idx, x, y, w, h, _serie, _origine = tas._rect_map[i]
    return ox + (x + w / 2) * s, oy + (ph - (y + h / 2)) * s


def _posizioni(tas):
    return [(t.nome, x / mm, y / mm) for t, x, y, _s, _o in disponi(tas.leggi_config())]


def _linee_guida(tas):
    cv = tas.canvas
    return [i for i in cv.find_all() if cv.type(i) == "line" and cv.itemcget(i, "fill") == st.COLORE_GUIDA]


# ---- zoom

def test_lo_zoom_tiene_fermo_il_punto_sotto_il_puntatore(app):
    tas = _tasselli(app)
    sx, sy = _schermo(tas, 105, 148)                  # il centro del foglio
    tas._zoom_intorno(4.0, sx, sy)
    assert tas._zoom == pytest.approx(4.0)
    nx, ny = _schermo(tas, 105, 148)
    assert (nx, ny) == (pytest.approx(sx, abs=1e-6), pytest.approx(sy, abs=1e-6))
    assert tas.lbl_zoom.cget("text") == "Zoom \u00d74,0"
    # un altro punto, lontano dal centro, con il foglio ormai piu' grande della finestra
    sx, sy = _schermo(tas, 60, 220)
    tas._zoom_intorno(1.5, sx, sy)
    nx, ny = _schermo(tas, 60, 220)
    assert (nx, ny) == (pytest.approx(sx, abs=1e-6), pytest.approx(sy, abs=1e-6))


def test_lo_zoom_ha_un_massimo_e_un_minimo(app):
    tas = _tasselli(app)
    for _ in range(60):
        tas._zoom_intorno(1.5)
        s, *_ = _vista(tas)
        # controllo a ogni scatto: senza limite i caratteri diventerebbero enormi e il disegno si pianta
        assert s * mm <= st.PX_PER_MM_MAX * (1 + 1e-6), "si e' ingrandito oltre il massimo"
    assert s * mm == pytest.approx(st.PX_PER_MM_MAX, rel=1e-6), "non ha raggiunto il massimo"
    for _ in range(80):
        tas._zoom_intorno(1 / 1.5)
    assert tas._zoom == 1.0, "non si riduce sotto il foglio intero"
    assert tas.lbl_zoom.cget("text") == "Zoom \u00d71"


def test_adatta_riporta_alla_vista_intera(app):
    tas = _tasselli(app)
    s1, ox1, oy1, *_ = _vista(tas)
    sx, sy = _schermo(tas, 30, 40)
    tas._zoom_intorno(6.0, sx, sy)
    tas._pan_da = (0, 0, *tas._pan)
    tas._pan_move(_ev(-80, -60))
    assert tas._zoom > 1 and tas._pan != [0.0, 0.0]
    tas._zoom_adatta()
    assert tas._zoom == 1.0 and tas._pan == [0.0, 0.0]
    assert _vista(tas)[:3] == (pytest.approx(s1), pytest.approx(ox1), pytest.approx(oy1))


def test_lo_zoom_resta_quando_l_anteprima_si_ridisegna_o_la_finestra_cambia(app):
    tas = _tasselli(app)
    tas._zoom_intorno(3.0)
    tas._preview()
    assert tas._zoom == pytest.approx(3.0)
    app.root.geometry("1400x900")
    app.root.update()
    app.root.update()
    assert tas._zoom == pytest.approx(3.0), "cambiando la finestra lo zoom non deve ripartire da 1"


def test_i_pulsanti_meno_piu_adatta(app):
    tas = _tasselli(app)
    piu, meno, adatta = (trova_pulsante(tas, t) for t in ("+", "\u2212", "Adatta"))
    assert piu is not None and meno is not None and adatta is not None
    piu.invoke()
    assert tas._zoom == pytest.approx(st.FATTORE_ZOOM_PULSANTI)
    piu.invoke()
    meno.invoke()
    assert tas._zoom == pytest.approx(st.FATTORE_ZOOM_PULSANTI)
    adatta.invoke()
    assert tas._zoom == 1.0


def test_la_rotella_sull_anteprima_ingrandisce_e_riduce(app):
    """Linux con Tk 8.6 manda Button-4 e Button-5, gli altri sistemi MouseWheel."""
    tas = _tasselli(app)
    cv = tas.canvas
    cv.event_generate("<Button-5>", x=100, y=100)         # a zoom 1 riduce: resta 1
    assert tas._zoom == 1.0
    cv.event_generate("<Button-4>", x=100, y=100)
    assert tas._zoom == pytest.approx(st.FATTORE_ZOOM)
    cv.event_generate("<Button-5>", x=100, y=100)
    assert tas._zoom == pytest.approx(1.0)
    cv.event_generate("<MouseWheel>", x=100, y=100, delta=120)
    assert tas._zoom == pytest.approx(st.FATTORE_ZOOM)
    cv.event_generate("<MouseWheel>", x=100, y=100, delta=-120)
    assert tas._zoom == pytest.approx(1.0)


# ---- spostamento della vista

def test_trascinando_lo_sfondo_si_sposta_la_vista_ma_solo_se_ingrandita(app):
    tas = _tasselli(app)
    vuoto = _schermo(tas, 105, 270)                   # in basso, dove non ci sono pezzi
    tas._drag_start(_ev(*vuoto))
    tas._drag_move(_ev(vuoto[0] - 50, vuoto[1] - 30))
    tas._drag_fine()
    assert tas._pan == [0.0, 0.0], "a foglio intero non c'e' niente da spostare"

    tas._zoom_intorno(4.0, *_schermo(tas, 105, 148))
    prima = list(tas._pan)
    vuoto = _schermo(tas, 105, 200)
    tas._drag_start(_ev(*vuoto))
    tas._drag_move(_ev(vuoto[0] - 50, vuoto[1] - 30))
    assert tas._pan == [pytest.approx(prima[0] - 50), pytest.approx(prima[1] - 30)]
    assert tas._rect_map and _posizioni(tas) == _posizioni(tas)
    tas._drag_fine()
    assert tas._pan_da is None


def test_la_vista_non_esce_dal_foglio(app):
    tas = _tasselli(app)
    tas._zoom_intorno(5.0, *_schermo(tas, 105, 148))
    W, H = tas.canvas.winfo_width(), tas.canvas.winfo_height()
    for dx, dy in ((-100000, -100000), (100000, 100000), (-100000, 100000)):
        tas._pan_da = (0, 0, *tas._pan)
        tas._pan_move(_ev(dx, dy))
        s, ox, oy, pw, ph = _vista(tas)
        m = st.MARGINE_VISTA_PX
        assert ox <= m + 1e-6 and ox + pw * s >= W - m - 1e-6, "vuoto a sinistra o a destra del foglio"
        assert oy <= m + 1e-6 and oy + ph * s >= H - m - 1e-6, "vuoto in alto o in basso"


def test_il_tasto_destro_e_quello_centrale_spostano_la_vista(app):
    tas = _tasselli(app)
    tas._zoom_intorno(4.0, *_schermo(tas, 105, 148))
    for tasto in (2, 3):
        prima = list(tas._pan)
        tas.canvas.event_generate("<ButtonPress-%d>" % tasto, x=300, y=300)
        tas.canvas.event_generate("<B%d-Motion>" % tasto, x=270, y=320)
        tas.canvas.event_generate("<ButtonRelease-%d>" % tasto, x=270, y=320)
        assert tas._pan == [pytest.approx(prima[0] - 30), pytest.approx(prima[1] + 20)], tasto
        assert tas._pan_da is None


# ---- trascinare i pezzi

@pytest.mark.parametrize("ingrandimento", [1.0, 6.0])
def test_trascinare_un_pezzo_funziona_a_qualunque_zoom(app, ingrandimento):
    tas = _tasselli(app)
    tas._calamita.set(False)                                     # qui si prova solo la conversione
    if ingrandimento > 1:
        tas._zoom_intorno(ingrandimento, *_centro_pezzo(tas, 1))
    s, _ox, _oy, _pw, ph = _vista(tas)
    cx, cy = _centro_pezzo(tas, 1)
    _i, rx, ry, rw, rh, _se, _o = tas._rect_map[1]
    x0, y0 = rx / mm, (ph - ry - rh) / mm            # dov'e' adesso (il campo, in automatico, non lo dice)
    tas._drag_start(_ev(cx, cy))
    tas._drag_move(_ev(cx + 30, cy + 20))
    tas._drag_fine()
    t = tas.leggi_config().tasselli[1]
    assert not t.auto
    assert t.x_mm == pytest.approx(x0 + 30 / (s * mm), abs=0.06)
    assert t.y_mm == pytest.approx(y0 + 20 / (s * mm), abs=0.06)


def test_un_clic_senza_spostamento_non_muove_nessun_pezzo(app):
    """Regressione: cliccare su un pezzo in posizione automatica lo mandava a (20; 20) mm,
    e gli altri scivolavano fino a 0,05 mm perche' venivano arrotondati al decimo."""
    tas = _tasselli(app)
    tas.vars["gap_mm"].set(12.34)                                # posizioni non multiple di 0,1 mm
    tas._preview()
    prima = _posizioni(tas)
    for i in range(len(tas._rect_map)):
        tas._drag_start(_ev(*_centro_pezzo(tas, i)))
        tas._drag_fine()
        assert _posizioni(tas) == [(n, pytest.approx(x, abs=1e-9), pytest.approx(y, abs=1e-9))
                                   for n, x, y in prima], "il pezzo %d si e' mosso" % i
        tas._preview()


def test_un_clic_senza_spostamento_non_muove_neanche_i_pezzi_di_un_altra_serie(app):
    tas = _tasselli(app)
    tas.vars["serie"].set(2)
    tas.vars["gap_mm"].set(12.34)
    tas._preview()
    prima = _posizioni(tas)
    assert len(prima) == 6
    ultimo = len(tas._rect_map) - 1                              # un pezzo della serie 2
    tas._drag_start(_ev(*_centro_pezzo(tas, ultimo)))
    tas._drag_fine()
    assert _posizioni(tas) == [(n, pytest.approx(x, abs=1e-9), pytest.approx(y, abs=1e-9))
                               for n, x, y in prima]


def test_il_trascinamento_con_gli_eventi_veri_del_mouse(app):
    tas = _tasselli(app)
    tas._calamita.set(False)
    cx, cy = _centro_pezzo(tas, 1)
    x0 = tas.leggi_config().tasselli[1].x_mm
    tas.canvas.event_generate("<Button-1>", x=int(cx), y=int(cy))
    tas.canvas.event_generate("<B1-Motion>", x=int(cx) + 40, y=int(cy))
    assert tas._drag is not None
    tas.canvas.event_generate("<ButtonRelease-1>", x=int(cx) + 40, y=int(cy))
    assert tas._drag is None
    assert tas.leggi_config().tasselli[1].x_mm > x0 + 5


# ---- calamita

def _trascina_sul_bordo_del_piatto(tas, extra_mm, stato=0, dy_mm=-40.0):
    """Trascina Dorso 1 quasi a filo del bordo destro del Piatto, extra_mm oltre.
    Restituisce (x del bordo destro del Piatto in mm, campo x del Dorso 1 dopo il gesto)."""
    s, ox, oy, _pw, ph = _vista(tas)
    _i, x, y, w, h, _se, _o = tas._rect_map[1]                     # Dorso 1
    _i0, px, py, pwd, phd, _s0, _o0 = tas._rect_map[0]             # Piatto
    bordo = (px + pwd) / mm
    tas._drag_start(_ev(*_centro_pezzo(tas, 1)))
    nx = ox + (px + pwd + extra_mm * mm + w / 2) * s
    ny = oy + (ph - (py + phd + dy_mm * mm - h / 2)) * s
    tas._drag_move(_ev(nx, ny, stato))
    return bordo


def test_la_calamita_aggancia_il_bordo_e_mostra_la_linea_guida(app):
    tas = _tasselli(app)
    bordo = _trascina_sul_bordo_del_piatto(tas, extra_mm=0.4)
    t = tas.leggi_config().tasselli[1]
    assert t.x_mm == pytest.approx(bordo, abs=1e-6), "il bordo sinistro del Dorso 1 non e' a filo del Piatto"
    assert tas._guide is not None and any(abs(g - bordo) < 1e-6 for g in tas._guide[0])
    assert len(_linee_guida(tas)) >= 1
    tas._drag_fine()
    assert tas._guide is None and _linee_guida(tas) == [], "le guide devono sparire al rilascio"
    assert tas.leggi_config().tasselli[1].x_mm == pytest.approx(bordo, abs=1e-6), "e il pezzo resta dov'e'"


def test_ctrl_e_la_casella_escludono_la_calamita(app):
    tas = _tasselli(app)
    bordo = _trascina_sul_bordo_del_piatto(tas, extra_mm=0.4, stato=0x4)          # Ctrl premuto
    x = tas.leggi_config().tasselli[1].x_mm
    assert abs(x - bordo) > 0.1 and tas._guide is None and _linee_guida(tas) == []
    tas._drag_fine()

    tas = _tasselli(app)
    tas._calamita.set(False)                                                          # casella spenta
    bordo = _trascina_sul_bordo_del_piatto(tas, extra_mm=0.4)
    assert abs(tas.leggi_config().tasselli[1].x_mm - bordo) > 0.1 and tas._guide is None
    tas._drag_fine()


def test_la_calamita_diventa_piu_fine_ingrandendo(app):
    """La soglia e' in pixel: a foglio intero 1,5 mm sono pochi pixel e si aggancia, ingrandito
    quegli stessi 1,5 mm sono tanti pixel e il pezzo resta dov'e'."""
    tas = _tasselli(app)
    bordo = _trascina_sul_bordo_del_piatto(tas, extra_mm=1.5)
    assert tas.leggi_config().tasselli[1].x_mm == pytest.approx(bordo, abs=1e-6)
    tas._drag_fine()

    tas = _tasselli(app)
    tas._zoom_intorno(8.0, *_centro_pezzo(tas, 1))
    bordo = _trascina_sul_bordo_del_piatto(tas, extra_mm=1.5)
    x = tas.leggi_config().tasselli[1].x_mm
    assert abs(x - bordo) > 1.0, "a x8 il pezzo non doveva agganciarsi al bordo del Piatto"
    assert not (tas._guide and any(abs(g - bordo) < 1e-6 for g in tas._guide[0]))
    tas._drag_fine()


def test_la_calamita_si_aggancia_al_margine_del_foglio(app):
    tas = _tasselli(app)
    s, ox, oy, _pw, ph = _vista(tas)
    tas._drag_start(_ev(*_centro_pezzo(tas, 2)))                                     # Dorso 2
    _i, x, y, w, h, _se, _o = tas._rect_map[2]
    margine = tas.leggi_config().margine_mm
    nx = ox + (margine * mm + 0.3 * mm + w / 2) * s                                  # 0,3 mm oltre il margine
    ny = oy + (ph - (y + h / 2) - 60 * mm) * s
    tas._drag_move(_ev(nx, ny))
    assert tas.leggi_config().tasselli[2].x_mm == pytest.approx(margine, abs=1e-6)
    tas._drag_fine()


def test_le_guide_si_disegnano_solo_finche_si_trascina(app):
    tas = _tasselli(app)
    tas._guide = ([50.0, 80.0], [100.0])
    tas._preview()
    assert len(_linee_guida(tas)) == 3
    tas._guide = None
    tas._preview()
    assert _linee_guida(tas) == []


def test_la_calamita_vale_anche_per_i_pezzi_delle_altre_serie(app):
    tas = _tasselli(app)
    tas.vars["serie"].set(2)
    tas._preview()
    n = len(tas._rect_map)
    assert n == 6
    i = n - 1                                                                         # un pezzo della serie 2
    tas._drag_start(_ev(*_centro_pezzo(tas, i)))
    s, ox, oy, _pw, ph = _vista(tas)
    _i, x, y, w, h, _se, _o = tas._rect_map[0]                                        # bordo sinistro del Piatto
    _ii, xi, yi, wi, hi, _s2, _o2 = tas._rect_map[i]
    nx = ox + (x + 0.3 * mm + wi / 2) * s
    ny = oy + (ph - (yi + hi / 2)) * s
    tas._drag_move(_ev(nx, ny))
    assert tas._guide is not None and any(abs(g - x / mm) < 1e-6 for g in tas._guide[0])
    tas._drag_fine()


# ---- i campi decimali della finestra devono accettare i decimali

def test_nessun_campo_decimale_e_un_campo_intero(app):
    """Regressione: larghezza, altezza e y dei tasselli di partenza erano IntVar, che troncano:
    23,5 mm diventava 23 mm, e trascinando un pezzo la sua y si arrotondava al millimetro (per difetto)."""
    import dataclasses
    from tkinter import IntVar
    from legatoria.tasselli import Config, Tassello
    tas = app.scheda_tasselli
    for i in range(len(tas.cfg.tasselli)):
        for f in dataclasses.fields(Tassello):
            if f.type == "float":
                assert not isinstance(tas.vars["t%d_%s" % (i, f.name)], IntVar), (i, f.name)
    for f in dataclasses.fields(Config):
        if f.type == "float":
            assert not isinstance(tas.vars[f.name], IntVar), f.name


def test_una_larghezza_con_i_decimali_arriva_intera_alla_configurazione(app):
    tas = app.scheda_tasselli
    tas.vars["t1_larghezza_mm"].set(23.5)
    tas.vars["t1_altezza_mm"].set(85.25)
    tas.vars["t1_y_mm"].set(60.75)
    t = tas.leggi_config().tasselli[1]
    assert (t.larghezza_mm, t.altezza_mm, t.y_mm) == (23.5, 85.25, 60.75)


def test_trascinando_la_y_conserva_i_decimali(app):
    tas = _tasselli(app)
    tas._calamita.set(False)
    cx, cy = _centro_pezzo(tas, 1)
    tas._drag_start(_ev(cx, cy))
    tas._drag_move(_ev(cx, cy + 7.3))                # uno spostamento che non da' un numero intero
    y = tas.leggi_config().tasselli[1].y_mm
    assert y != int(y), "la y e' stata troncata a un intero: %r" % y
    tas._drag_fine()


# ---------------------------------------------------------------------------
# Tasselli: decoro "fleuron agli angoli"
# ---------------------------------------------------------------------------

def _linee_decoro_in_anteprima(tas):
    """Le linee del decoro nell'anteprima (colore #222222, diverso dal blu dei bordi)."""
    cv = tas.canvas
    return [i for i in cv.find_all() if cv.type(i) == "line" and cv.itemcget(i, "fill") == "#222222"]


def test_fleuron_agli_angoli_e_nella_lista_dei_modelli(app):
    from legatoria.tasselli import DECORI
    assert "fleuron agli angoli" in DECORI


def test_i_campi_del_fleuron_arrivano_alla_configurazione(app):
    tas = app.scheda_tasselli
    tas.vars["decoro_modello"].set("fleuron agli angoli")
    tas.vars["decoro_fleuron_dim_mm"].set(14.5)
    tas.vars["decoro_fleuron_ricciolo"].set(False)
    tas.vars["decoro_fleuron_centrale"].set(True)
    cfg = tas.leggi_config()
    assert cfg.decoro_modello == "fleuron agli angoli"
    assert cfg.decoro_fleuron_dim_mm == 14.5
    assert cfg.decoro_fleuron_ricciolo is False
    assert cfg.decoro_fleuron_centrale is True


def test_l_anteprima_disegna_il_fleuron_solo_con_quel_modello(app):
    tas = _tasselli(app)
    tas.vars["decoro_modello"].set("nessuno")
    tas._preview()
    assert _linee_decoro_in_anteprima(tas) == []
    tas.vars["decoro_modello"].set("fleuron agli angoli")
    tas._preview()
    assert len(_linee_decoro_in_anteprima(tas)) > 0


def test_il_ricciolo_e_il_centrale_cambiano_quante_linee_disegna_l_anteprima(app):
    tas = _tasselli(app)
    tas.vars["decoro_modello"].set("fleuron agli angoli")
    tas.vars["decoro_fleuron_ricciolo"].set(False)
    tas.vars["decoro_fleuron_centrale"].set(False)
    tas._preview()
    base = len(_linee_decoro_in_anteprima(tas))
    assert base > 0

    tas.vars["decoro_fleuron_ricciolo"].set(True)
    tas._preview()
    con_ricciolo = len(_linee_decoro_in_anteprima(tas))
    assert con_ricciolo > base

    tas.vars["decoro_fleuron_centrale"].set(True)
    tas._preview()
    con_centrale = len(_linee_decoro_in_anteprima(tas))
    assert con_centrale > con_ricciolo


def test_l_anteprima_del_fleuron_corrisponde_al_pdf_nel_numero_di_curve(app, tmp_path):
    """L'anteprima campiona le stesse curve del motore: stesso numero di tratti
    (foglie + ricciolo) per ciascuno dei tre tasselli attivi, per 4 angoli."""
    from legatoria.tasselli import curve_fleuron_angolo
    tas = _tasselli(app)
    tas.vars["decoro_modello"].set("fleuron agli angoli")
    tas._preview()
    n_pezzi = len(tas._rect_map)
    attese = len(curve_fleuron_angolo(11.0, True)) * 4 * n_pezzi   # 4 angoli per pezzo
    assert len(_linee_decoro_in_anteprima(tas)) == attese


# ---------------------------------------------------------------------------
# Avviso sullo spessore minimo per la doratura col foil
# ---------------------------------------------------------------------------

def test_l_anteprima_avvisa_se_lo_spessore_e_sotto_la_soglia_di_doratura(app):
    tas = _tasselli(app)
    tas.vars["decoro_modello"].set("filetto semplice")
    tas.vars["decoro_spessore_mm"].set(0.1)
    tas._preview()
    assert "doratura" in _testo_info(tas) and "0.10" in _testo_info(tas)
    tas.vars["decoro_spessore_mm"].set(0.4)
    tas._preview()
    assert "doratura" not in _testo_info(tas)


def test_il_campo_spessore_accetta_comunque_un_valore_sotto_la_soglia(app):
    """L'avviso non deve impedire di scegliere uno spessore fine: resta solo un avviso."""
    tas = app.scheda_tasselli
    tas.vars["decoro_modello"].set("filetto semplice")
    tas.vars["decoro_spessore_mm"].set(0.05)
    assert tas.leggi_config().decoro_spessore_mm == 0.05


def test_dopo_la_generazione_compare_l_avviso_di_doratura(app, tmp_path):
    tas = app.scheda_tasselli
    fonts = [f for f in scan_fonts(use_cache=False) if f.supported]
    if not fonts:
        pytest.skip("nessun font TrueType di sistema")
    tas.cfg.font_path, tas.cfg.font_index = fonts[0].path, fonts[0].index
    tas.vars["decoro_modello"].set("filetto semplice")
    tas.vars["decoro_spessore_mm"].set(0.1)
    assert tas._genera(str(tmp_path / "sottile.pdf"))
    assert "doratura" in _testo_info(tas)


# ---------------------------------------------------------------------------
# Tasselli: decoro continuo (greca, festone, dentelli)
# ---------------------------------------------------------------------------

def test_i_tre_stili_continui_sono_nella_lista_dei_modelli(app):
    from legatoria.tasselli import DECORI
    for stile in ("greca continua", "festone continuo", "dentelli continui"):
        assert stile in DECORI


def test_i_campi_dei_bordi_continui_arrivano_alla_configurazione(app):
    tas = app.scheda_tasselli
    tas.vars["decoro_modello"].set("greca continua")
    tas.vars["decoro_continuo_rientro_mm"].set(3.0)
    tas.vars["decoro_continuo_fascia_mm"].set(5.0)
    tas.vars["decoro_continuo_raggio_mm"].set(4.0)
    tas.vars["decoro_continuo_altezza_mm"].set(3.0)
    tas.vars["decoro_continuo_modulo_mm"].set(8.0)
    cfg = tas.leggi_config()
    assert cfg.decoro_modello == "greca continua"
    assert (cfg.decoro_continuo_rientro_mm, cfg.decoro_continuo_fascia_mm,
           cfg.decoro_continuo_raggio_mm, cfg.decoro_continuo_altezza_mm,
           cfg.decoro_continuo_modulo_mm) == (3.0, 5.0, 4.0, 3.0, 8.0)


@pytest.mark.parametrize("stile", ["greca continua", "festone continuo", "dentelli continui"])
def test_l_anteprima_disegna_qualcosa_solo_col_modello_giusto(app, stile):
    tas = _tasselli(app)
    tas.vars["decoro_modello"].set("nessuno")
    tas._preview()
    assert _linee_decoro_in_anteprima(tas) == []
    tas.vars["decoro_modello"].set(stile)
    tas._preview()
    assert len(_linee_decoro_in_anteprima(tas)) > 0


def test_cambiare_i_parametri_cambia_il_disegno_nell_anteprima(app):
    tas = _tasselli(app)
    tas.vars["decoro_modello"].set("dentelli continui")
    tas.vars["decoro_continuo_altezza_mm"].set(1.0)
    tas._preview()
    bassi = len(_linee_decoro_in_anteprima(tas))
    tas.vars["decoro_continuo_altezza_mm"].set(6.0)
    tas._preview()
    alti = len(_linee_decoro_in_anteprima(tas))
    assert bassi > 0 and alti > 0     # in entrambi i casi qualcosa si disegna


def test_lo_spessore_sotto_soglia_avvisa_anche_per_i_bordi_continui(app):
    tas = _tasselli(app)
    tas.vars["decoro_modello"].set("festone continuo")
    tas.vars["decoro_spessore_mm"].set(0.1)
    tas._preview()
    assert "doratura" in _testo_info(tas)
    tas.vars["decoro_spessore_mm"].set(0.4)
    tas._preview()
    assert "doratura" not in _testo_info(tas)


# ---------------------------------------------------------------------------
# Tasselli: decoro "cornice bitmap"
# ---------------------------------------------------------------------------

def test_l_anteprima_disegna_i_blocchetti_della_cornice_bitmap(app, tmp_path):
    from PIL import Image
    from legatoria.tasselli import BITMAP_RUOLI, DECORO_BITMAP
    for r in BITMAP_RUOLI:
        Image.new("RGBA", (40, 40), (0, 0, 0, 255)).save(tmp_path / ("fr_%s.png" % r), dpi=(600, 600))
    tas = _tasselli(app)
    tas.vars["decoro_modello"].set("nessuno")
    tas._preview()
    immagini = lambda: [i for i in tas.canvas.find_all() if tas.canvas.type(i) == "image"]
    assert immagini() == []
    tas.vars["decoro_bitmap_prefisso"].set(str(tmp_path / "fr_"))
    tas.vars["decoro_modello"].set(DECORO_BITMAP)
    tas._preview()
    assert len(immagini()) >= 8
    assert tas.leggi_config().decoro_bitmap_prefisso == str(tmp_path / "fr_")


def test_la_scelta_della_cornice_bitmap_parte_dalla_libreria_cornici(app, tmp_path, monkeypatch):
    from legatoria import tasselli
    from legatoria.gui import scheda_tasselli
    lib = tmp_path / "cornici"
    lib.mkdir()
    monkeypatch.setattr(scheda_tasselli, "CARTELLA_CORNICI", str(lib))
    viste = {}
    monkeypatch.setattr(scheda_tasselli.filedialog, "askopenfilename",
                        lambda **k: viste.update(k) or "")
    _tasselli(app)._file_bitmap()
    assert viste["initialdir"] == str(lib)
    assert tasselli.CARTELLA_CORNICI.endswith("cornici")


def test_menabo_sfoglia_per_aperture(app, pdf_numerato, monkeypatch):
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **k: str(pdf_numerato(40)))
    imp = app.scheda_imposizione
    imp.apri()
    imp.v_vista.set("menabo")
    imp.disegna()
    assert imp.apertura == 0 and imp.pagine_apertura(0) == (None, 0)
    imp.scorri(1)
    assert imp.pagine_apertura(imp.apertura) == (1, 2)
    for _ in range(40):
        imp.scorri(1)
    assert imp.apertura == imp.n_aperture() - 1
    assert imp.n_fasc.get() == imp.n_fascicoli
    imp.n_fasc.set(2)
    imp.disegna()
    assert imp.fascicolo_apertura(imp.apertura) == 1
