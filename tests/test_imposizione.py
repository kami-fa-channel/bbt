from types import SimpleNamespace

import pytest
from pypdf import PdfReader
from pypdf.generic import ArrayObject, IndirectObject

from legatoria import imposizione as imp
from legatoria.errori import ErroreLegatoria
from conftest import RADICE, numeri_sul_foglio, y_marche_di_collazione


def argomenti(**kw):
    base = dict(carta="a4", margine_dorso=15, margine_esterno=10, margine_testa=10,
                margine_piede=10, scala=1.0, shingling=0.0, segni=False)
    base.update(kw)
    return SimpleNamespace(**base)


# ------------------------------------------------------------------ logica pura

def test_ordine_del_fascicolo_da_16_pagine():
    facciate = imp.ordine_fascicolo(16)
    assert facciate[0] == (16, 1)      # fronte del foglio piu' esterno
    assert facciate[1] == (2, 15)      # retro
    assert facciate[-1] == (8, 9)      # le due pagine centrali
    pagine = sorted(p for coppia in facciate for p in coppia)
    assert pagine == list(range(1, 17))


def test_blocco_con_guardie_bianche_e_riempimento():
    blocco = imp.costruisci_blocco(pagine_orig=10, posizioni=[4], guardie=1, signature=16)
    assert len(blocco) % 16 == 0
    assert blocco[:2] == [None, None] and blocco[-2:] == [None, None]     # le guardie
    assert blocco[2 + 3] is None                    # la bianca di correzione prende il posto 4
    assert [p for p in blocco if p is not None] == list(range(10))         # il testo resta in ordine


def test_posizione_della_bianca_sposta_il_testo():
    blocco = imp.costruisci_blocco(8, [4], 0, 16)
    assert blocco[3] is None and blocco[4] == 3


def test_tabella_fascicolature_80_grammi():
    tab = imp.tabella_fascicolature(80, 749)
    assert tab["consigliati"] == 5
    assert [r["fogli"] for r in tab["righe"]] == list(range(1, 9))
    assert tab["righe"][0]["giudizio"] == "ok (molte cuciture)"
    assert tab["righe"][3]["fascicoli"] == 47 and tab["righe"][3]["bianche"] == 3
    testo = "\n".join(imp.righe_tabella(tab))
    assert "<== CONSIGLIATO" in testo


def test_esempio_del_capitolo_10_del_readme():
    p = imp.piano(pagine_orig=749, posizioni=[4], guardie=1, fogli=4, grammatura=80)
    assert p.n_fascicoli == 48
    assert p.riempimento == 14
    assert p.pagine_pdf == 384
    assert p.fogli_da_stampare == 192
    tr = imp.tranche(50, 4, p.n_fascicoli)
    assert tr["per_blocco"] == 6
    assert [(x["inizio"], x["fine"]) for x in tr["elenco"]][:2] == [(1, 48), (49, 96)]
    assert (tr["elenco"][-1]["inizio"], tr["elenco"][-1]["fine"]) == (337, 384)
    assert (tr["elenco"][-1]["f1"], tr["elenco"][-1]["f2"]) == (43, 48)


def test_riepilogo_e_stima_delle_misure_usano_la_stessa_ipotesi_sul_filo():
    """Regressione: il riepilogo contava 0,3-0,5 mm di filo per fascicolo e il
    passaggio delle misure alla copertina 0,25, quindi il dorso stimato poteva
    uscire piu' stretto anche del minimo che il riepilogo stesso prevedeva."""
    for pagine, fogli, grammatura in ((749, 4, 80), (200, 3, 100), (60, 2, 60), (1200, 5, 80)):
        p = imp.piano(pagine, [], 0, fogli, grammatura)
        m = imp.misure_blocco_stimate(p, "a4")
        minimo, massimo = p.dorso_mm
        assert (m.dorso_min, m.dorso_max) == (minimo, massimo)
        assert minimo < m.dorso < massimo
        filo_medio = sum(imp.FILO_MM_PER_FASCICOLO) / 2
        assert m.dorso == pytest.approx(p.spessore_carta_mm + p.n_fascicoli * filo_medio)
        assert p.dorso_mm == pytest.approx((p.spessore_carta_mm + p.filo_mm[0],
                                            p.spessore_carta_mm + p.filo_mm[1]))


def test_il_filo_indicato_dall_utente_sostituisce_l_intervallo():
    generico = imp.piano(749, [], 0, 4, 80)
    mio = imp.piano(749, [], 0, 4, 80, filo_mm=0.4)
    assert not generico.filo_indicato and mio.filo_indicato
    assert mio.filo_per_fascicolo == (0.4, 0.4)
    assert mio.filo_mm == pytest.approx((mio.n_fascicoli * 0.4,) * 2)
    assert mio.dorso_mm[0] == mio.dorso_mm[1]
    assert mio.dorso_mm[0] == pytest.approx(mio.spessore_carta_mm + mio.n_fascicoli * 0.4)
    # il filo non tocca il resto del piano
    for campo in ("blocco", "n_fascicoli", "riempimento", "pagine_pdf", "spessore_carta_mm"):
        assert getattr(mio, campo) == getattr(generico, campo)


def test_la_stima_delle_misure_segue_il_filo_indicato():
    p = imp.piano(749, [], 0, 4, 80, filo_mm=0.55)
    m = imp.misure_blocco_stimate(p, "a4")
    assert m.dorso == pytest.approx(p.spessore_carta_mm + p.n_fascicoli * 0.55)
    assert m.dorso_min == m.dorso_max == m.dorso


def test_un_filo_generico_e_uno_pari_alla_media_danno_lo_stesso_dorso():
    media = sum(imp.FILO_MM_PER_FASCICOLO) / 2
    generico = imp.misure_blocco_stimate(imp.piano(300, [], 0, 4, 80), "a4")
    indicato = imp.misure_blocco_stimate(imp.piano(300, [], 0, 4, 80, filo_mm=media), "a4")
    assert generico.dorso == pytest.approx(indicato.dorso)


@pytest.mark.parametrize("valore", [0, -0.1, float("nan")])
def test_filo_non_valido(valore):
    with pytest.raises(ErroreLegatoria, match="maggiore di zero"):
        imp.piano(100, [], 0, 4, 80, filo_mm=valore)
    with pytest.raises(ErroreLegatoria):
        imp.valida_filo(valore)
    imp.valida_filo(None)
    imp.valida_filo(0.4)


def test_avviso_se_il_filo_sembra_lo_spessore_di_tutto_il_libro():
    assert imp.avviso_filo(None) is None and imp.avviso_filo(0.4) is None
    assert imp.avviso_filo(imp.FILO_MM_MASSIMO_PLAUSIBILE) is None
    avviso = imp.avviso_filo(16)
    assert "16 mm" in avviso and "dividi" in avviso


def test_il_manuale_dichiara_la_stessa_ipotesi_sul_filo_del_programma():
    """Il manuale e il programma dicevano tre cose diverse sul filo (10-20 %, 0,25 mm,
    0,3-0,5 mm).  Se cambia FILO_MM_PER_FASCICOLO questo test obbliga ad aggiornare il testo."""
    minimo, massimo = imp.FILO_MM_PER_FASCICOLO
    dichiarata = f"{minimo:g}–{massimo:g} mm per fascicolo".replace(".", ",")
    manuale = (RADICE / "docs" / "manuale.md").read_text(encoding="utf-8")
    assert manuale.count(dichiarata) >= 3, f"il manuale non dice piu' '{dichiarata}' (capitoli 2, 13, 16.6)"
    assert "10–20 %" not in manuale
    assert f"il valore di mezzo, {(minimo + massimo) / 2:g} mm".replace(".", ",") in manuale


def test_misure_stimate_del_blocco_dal_formato_del_foglio():
    p = imp.piano(200, [], 0, 4, 80)
    m = imp.misure_blocco_stimate(p, "a4", rifilo_mm=3)
    assert (m.altezza, m.larghezza) == (210, 148.5 - 3)
    m = imp.misure_blocco_stimate(p, "a3", rifilo_mm=0)
    assert (m.altezza, m.larghezza) == (297, 210)


def test_le_tranche_non_spezzano_mai_un_fascicolo():
    for fogli in range(1, 9):
        tr = imp.tranche(50, fogli, 30)
        for x in tr["elenco"][:-1]:
            assert (x["fine"] - x["inizio"] + 1) % (fogli * 2) == 0


def test_leggi_posizioni_rigido_e_tollerante():
    assert imp.leggi_posizioni(["4,120", "8"], 749) == ([4, 120, 8], [])
    with pytest.raises(ErroreLegatoria, match="fuori dall'intervallo 1-750"):
        imp.leggi_posizioni(["9999"], 749)
    with pytest.raises(ErroreLegatoria, match="'abc' non valida"):
        imp.leggi_posizioni(["abc"], 749)
    assert imp.leggi_posizioni(["4 abc 9999"], 749, rigido=False) == ([4], [9999])


# ------------------------------------------------------------------ file veri

def test_imposizione_mette_le_pagine_dove_devono_stare(pdf_numerato, tmp_path):
    reader = imp.apri_pdf(pdf_numerato(32))
    piano = imp.piano(32, [], 0, 4, 80)
    uscita = tmp_path / "out.pdf"
    n_fasc, n_pag = imp.impagina(reader, piano.blocco, argomenti(), 4, uscita)
    assert (n_fasc, n_pag) == (2, 16)
    out = PdfReader(str(uscita))
    assert numeri_sul_foglio(out, 0) == [(16, "sx"), (1, "dx")]
    assert numeri_sul_foglio(out, 1) == [(2, "sx"), (15, "dx")]
    assert numeri_sul_foglio(out, 7) == [(8, "sx"), (9, "dx")]
    assert numeri_sul_foglio(out, 8) == [(32, "sx"), (17, "dx")]     # secondo fascicolo
    tutti = [n for i in range(len(out.pages)) for n, _ in numeri_sul_foglio(out, i)]
    assert sorted(tutti) == list(range(1, 33))                        # ogni pagina una volta sola


def test_il_file_non_ha_riferimenti_pendenti(pdf_bianco, tmp_path):
    """Regressione: con i segni, l'ordine sbagliato delle compressioni lasciava
    /Contents di una pagina che puntava a un oggetto eliminato."""
    reader = imp.apri_pdf(pdf_bianco(749))
    piano = imp.piano(749, [], 0, 4, 80)
    uscita = tmp_path / "out.pdf"
    imp.impagina(reader, piano.blocco, argomenti(segni=True, shingling=0.1), 4, uscita)
    out = PdfReader(str(uscita))
    for i, pagina in enumerate(out.pages):
        contenuti = pagina.raw_get("/Contents")
        contenuti = contenuti.get_object() if isinstance(contenuti, IndirectObject) else contenuti
        elementi = contenuti if isinstance(contenuti, ArrayObject) else [contenuti]
        for e in elementi:
            assert not isinstance(e, IndirectObject) or e.get_object() is not None, f"facciata {i + 1}"


@pytest.mark.parametrize("n_fascicoli", [1, 20, 47, 52, 59, 104, 118])
def test_ogni_fascicolo_ha_la_sua_marca_di_collazione(pdf_bianco, tmp_path, n_fascicoli):
    """Regressione: per certi numeri (52, 59, 104...) un troncamento in virgola
    mobile faceva ricominciare la scaletta dall'alto sull'ultimo fascicolo."""
    reader = imp.apri_pdf(pdf_bianco(n_fascicoli * 16))
    piano = imp.piano(n_fascicoli * 16, [], 0, 4, 80)
    uscita = tmp_path / "out.pdf"
    imp.impagina(reader, piano.blocco, argomenti(segni=True), 4, uscita)
    marche = y_marche_di_collazione(PdfReader(str(uscita)))
    assert len(marche) == n_fascicoli
    assert [i for i, _ in marche] == [8 * k for k in range(n_fascicoli)]   # 1a facciata di ognuno
    ys = [y for _, y in marche]
    assert ys == sorted(ys) and len(set(ys)) == len(ys), "la scaletta deve scendere sempre"


def test_margini_troppo_grandi_sono_un_errore_non_un_sys_exit(pdf_bianco, tmp_path):
    reader = imp.apri_pdf(pdf_bianco(16))
    piano = imp.piano(16, [], 0, 4, 80)
    with pytest.raises(ErroreLegatoria, match="margini"):
        imp.impagina(reader, piano.blocco, argomenti(margine_dorso=100, margine_esterno=100),
                     4, tmp_path / "x.pdf")


def test_pdf_mancante_e_pdf_protetto(tmp_path, pdf_bianco):
    with pytest.raises(ErroreLegatoria, match="non esiste"):
        imp.apri_pdf(tmp_path / "non_c_e.pdf")
    from pypdf import PdfReader as R, PdfWriter as W
    w = W(clone_from=R(str(pdf_bianco(4))))
    w.encrypt("segreto")
    protetto = tmp_path / "protetto.pdf"
    with open(protetto, "wb") as fh:
        w.write(fh)
    with pytest.raises(ErroreLegatoria, match="password"):
        imp.apri_pdf(protetto)
