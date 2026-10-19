"""Rendering delle pagine per l'anteprima dell'imposizione."""
import shutil
import time

import pytest

pytest.importorskip("PIL")

from legatoria.gui import miniature  # noqa: E402


def aspetta(m, secondi=20):
    fine = time.time() + secondi
    while m.in_attesa() and time.time() < fine:
        time.sleep(0.02)


def test_i_lati_vanno_a_gradini():
    assert miniature.lato_a_gradini(1) == miniature.GRADINO_PX
    assert miniature.lato_a_gradini(miniature.GRADINO_PX + 1) == 2 * miniature.GRADINO_PX
    assert miniature.lato_a_gradini(10 ** 6) == miniature.MASSIMO_PX


@pytest.mark.parametrize("nome", ["pdfium", "pdftoppm"])
def test_ogni_motore_rende_la_pagina(pdf_numerato, nome):
    if nome == "pdfium":
        pytest.importorskip("pypdfium2")
    elif not shutil.which("pdftoppm"):
        pytest.skip("pdftoppm non c'e'")
    m = miniature.Miniature(pdf_numerato(3), nome)
    try:
        assert m.chiedi(1, 200) is None                  # la prima volta va in coda
        aspetta(m)
        immagine = m.chiedi(1, 200)
        assert immagine is not None
        # pagina A5 verticale: il lato lungo e' quello chiesto, a gradini
        assert immagine.height == miniature.lato_a_gradini(200)
        assert immagine.width == pytest.approx(immagine.height * 148 / 210, abs=2)
        # la pagina porta il suo numero in nero al centro: non e' tutta bianca
        assert immagine.convert("L").getextrema()[0] < 100
    finally:
        m.chiudi()


def test_senza_motore_niente_miniature(pdf_numerato):
    m = miniature.Miniature(pdf_numerato(1), nome_motore=None)
    assert m._thread is None
    assert not m.disponibile and m.chiedi(0, 100) is None and not m.in_attesa()


def test_una_pagina_che_non_si_rende_non_blocca(pdf_numerato):
    if miniature.motore() is None:
        pytest.skip("nessun motore di rendering")
    m = miniature.Miniature(pdf_numerato(2))
    try:
        m.chiedi(99, 100)                                # non esiste
        aspetta(m)
        assert not m.in_attesa() and m.chiedi(99, 100) is None
    finally:
        m.chiudi()


def test_due_miniature_non_usano_pdfium_insieme(pdf_numerato, monkeypatch):
    """Aprire un altro PDF mentre il thread del precedente sta ancora rendendo:
    pdfium non e' thread-safe, quindi i rendering di istanze diverse non devono
    sovrapporsi (su GitHub, con Python 3.9, il processo andava in crash)."""
    pytest.importorskip("pypdfium2")
    import threading
    dentro, massimo, blocco = [0], [0], threading.Lock()
    vero = miniature.Miniature._rendi_pdfium

    def lento(documento, indice, lato):
        with blocco:
            dentro[0] += 1
            massimo[0] = max(massimo[0], dentro[0])
        try:
            time.sleep(0.05)
            return vero(documento, indice, lato)
        finally:
            with blocco:
                dentro[0] -= 1

    monkeypatch.setattr(miniature.Miniature, "_rendi_pdfium", staticmethod(lento))
    pdf = pdf_numerato(4)
    a, b = miniature.Miniature(pdf, "pdfium"), miniature.Miniature(pdf, "pdfium")
    try:
        for i in range(4):
            a.chiedi(i, 200)
            b.chiedi(i, 200)
        aspetta(a)
        aspetta(b)
        assert a.chiedi(3, 200) is not None and b.chiedi(3, 200) is not None
        assert massimo[0] == 1
    finally:
        a.chiudi()
        b.chiudi()
