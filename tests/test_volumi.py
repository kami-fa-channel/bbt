"""Divisione di un PDF in volumi."""
import pytest
from pypdf import PdfReader

from legatoria import volumi
from legatoria.errori import ErroreLegatoria
from test_cli import legatoria


def test_leggi_tagli():
    assert volumi.leggi_tagli("240, 480;  600") == [240, 480, 600]
    assert volumi.leggi_tagli("") == []
    with pytest.raises(ErroreLegatoria, match="'x'"):
        volumi.leggi_tagli("240 x")


def test_un_taglio_da_due_volumi_e_due_da_tre():
    assert volumi.intervalli(352, [240]) == [(1, 240), (241, 352)]
    assert volumi.intervalli(352, [100, 200]) == [(1, 100), (101, 200), (201, 352)]
    assert volumi.intervalli(352, []) == [(1, 352)]


@pytest.mark.parametrize("tagli", [[0], [352], [400], [100, 100], [200, 100]])
def test_tagli_non_validi(tagli):
    with pytest.raises(ErroreLegatoria):
        volumi.intervalli(352, tagli)


def test_parti_uguali():
    assert volumi.tagli_uguali(100, 4) == [25, 50, 75]
    with pytest.raises(ErroreLegatoria):
        volumi.tagli_uguali(3, 5)


def test_i_volumi_hanno_le_pagine_giuste(pdf_numerato, tmp_path):
    uscite = volumi.dividi(pdf_numerato(10), [4, 7])
    assert [u.name for u in uscite] == ["numerato_vol1.pdf", "numerato_vol2.pdf", "numerato_vol3.pdf"]
    assert all(u.parent == tmp_path for u in uscite)
    primi = [numeri_sul_foglio_primo(u) for u in uscite]
    assert primi == [1, 5, 8]
    assert [len(PdfReader(str(u)).pages) for u in uscite] == [4, 3, 3]


def numeri_sul_foglio_primo(percorso):
    return int(PdfReader(str(percorso)).pages[0].extract_text().split()[0])


def test_non_sovrascrive_senza_permesso(pdf_bianco):
    percorso = pdf_bianco(10)
    volumi.dividi(percorso, [5])
    with pytest.raises(ErroreLegatoria, match="esistono gia'"):
        volumi.dividi(percorso, [5])
    volumi.dividi(percorso, [5], sovrascrivi=True)


def test_riga_di_comando(pdf_bianco, tmp_path):
    cartella = tmp_path / "fuori"
    cartella.mkdir()
    r = legatoria("volumi", pdf_bianco(10), "6", "-o", cartella)
    assert r.returncode == 0 and "pagine 7-10 (4)" in r.stdout
    assert sorted(p.name for p in cartella.iterdir()) == ["bianco_vol1.pdf", "bianco_vol2.pdf"]
    r = legatoria("volumi", pdf_bianco(10), "--parti", 3, "-o", cartella, "--sovrascrivi")
    assert r.returncode == 0 and (cartella / "bianco_vol3.pdf").is_file()
    r = legatoria("volumi", pdf_bianco(10), "20")
    assert r.returncode != 0 and "Errore:" in r.stderr


def ordine_pagine(percorso):
    """Cosa c'e' su ogni pagina: il numero stampato, 'N' se e' una pagina per appunti con
    la griglia (tanto contenuto e nessun testo), '-' se e' bianca."""
    risultato = []
    for p in PdfReader(str(percorso)).pages:
        testo = p.extract_text().strip()
        contenuto = p.get_contents().get_data() if p.get("/Contents") else b""
        risultato.append(testo or ("N" if len(contenuto) > 500 else "-"))
    return risultato


@pytest.mark.parametrize("lato, atteso", [
    ("sinistra", ["-", "N", "1", "N", "2", "N", "3"]),
    ("destra", ["-", "1", "N", "2", "N", "3", "N"]),
])
def test_appunti_accanto_a_ogni_pagina(pdf_numerato, lato, atteso):
    [uscita] = volumi.dividi(pdf_numerato(3), [], appunti=volumi.Appunti(lato, "quadretti"))
    assert uscita.name == "numerato_appunti.pdf"
    assert ordine_pagine(uscita) == atteso


def test_le_pagine_bianche_non_hanno_la_griglia(pdf_numerato):
    [uscita] = volumi.dividi(pdf_numerato(2), [], appunti=volumi.Appunti("destra", "bianca"))
    assert ordine_pagine(uscita) == ["-", "1", "-", "2", "-"]


def test_appunti_con_i_volumi_non_coprono_quelli_senza(pdf_numerato, tmp_path):
    base = volumi.dividi(pdf_numerato(6), [3])
    con = volumi.dividi(pdf_numerato(6), [3], appunti=volumi.Appunti("destra", "righe"))
    assert [u.name for u in con] == ["numerato_vol1_appunti.pdf", "numerato_vol2_appunti.pdf"]
    assert all(u.exists() for u in base + con)
    assert [len(PdfReader(str(u)).pages) for u in con] == [7, 7]


def test_la_pagina_per_appunti_ha_la_misura_della_pagina(pdf_bianco):
    [uscita] = volumi.dividi(pdf_bianco(2), [], appunti=volumi.Appunti("sinistra", "bianca"))
    for p in PdfReader(str(uscita)).pages:
        assert (round(float(p.mediabox.width)), round(float(p.mediabox.height))) == (
            round(148 * 72 / 25.4), round(210 * 72 / 25.4))


def test_i_segnalibri_seguono_le_pagine(pdf_numerato):
    from pypdf import PdfWriter
    w = PdfWriter()
    w.append(PdfReader(str(pdf_numerato(6))))
    w.add_outline_item("Terza", 2)
    with open(pdf_numerato(6).parent / "con_indice.pdf", "wb") as fh:
        w.write(fh)
    [uscita] = volumi.dividi(pdf_numerato(6).parent / "con_indice.pdf", [],
                             appunti=volumi.Appunti("destra", "bianca"))
    r = PdfReader(str(uscita))
    [voce] = r.outline
    assert r.get_destination_page_number(voce) == 1 + 2 * 2      # bianca + (pagina, appunti) x 2


def test_senza_tagli_ne_appunti_non_fa_niente(pdf_bianco):
    with pytest.raises(ErroreLegatoria, match="niente da fare"):
        volumi.dividi(pdf_bianco(4), [])


@pytest.mark.parametrize("appunti", [volumi.Appunti("su"), volumi.Appunti(tipo="a pois"),
                                     volumi.Appunti(passo=0.2), volumi.Appunti(margine=-1),
                                     volumi.Appunti(spessore=0), volumi.Appunti(passo=5, spessore=3)])
def test_appunti_non_validi(appunti, pdf_bianco):
    with pytest.raises(ErroreLegatoria):
        volumi.dividi(pdf_bianco(4), [2], appunti=appunti)


def test_appunti_da_riga_di_comando(pdf_bianco, tmp_path):
    r = legatoria("volumi", pdf_bianco(10), "5", "--appunti", "sinistra", "--griglia", "righe",
                  "--passo", 7, "--spessore", 0.2, "-o", tmp_path)
    assert r.returncode == 0 and "11 con gli appunti" in r.stdout
    assert (tmp_path / "bianco_vol2_appunti.pdf").is_file()
    r = legatoria("volumi", pdf_bianco(10), "--appunti", "destra", "--sovrascrivi")
    assert r.returncode == 0 and (tmp_path / "bianco_appunti.pdf").is_file()
