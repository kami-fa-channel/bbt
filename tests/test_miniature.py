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
