import pytest
from pypdf import PdfReader

from legatoria import copertina as cop


def test_esempio_del_capitolo_18_con_i_parametri_del_readme():
    a = cop.opzioni(210, 145, 48, unghia=3, cartone=3, gola=5)
    r = cop.calcola(a)
    assert r["piatto"] == (216, 143)
    assert r["dorso_cartoncino"] == 56
    assert r["rivestimento"] == (246, 382)


def test_stesso_libro_con_i_valori_automatici():
    """Il manuale lo dichiara: con i valori automatici viene un millimetro in piu'."""
    r = cop.calcola(cop.opzioni(210, 145, 48))
    assert r["piatto"] == (217, 144)
    assert r["rivestimento"] == (247, 383)


def test_le_fasce_coprono_tutto_il_rivestimento():
    r = cop.calcola(cop.opzioni(210, 145, 48, unghia=3, cartone=3, gola=5))
    assert r["fasce"][0][1] == 0 and r["fasce"][-1][2] == r["rivestimento"][1]
    assert [f[0] for f in r["fasce"]] == ["rimbocco", "piatto posteriore", "gola", "DORSO",
                                           "gola", "piatto anteriore", "rimbocco"]
    assert r["fasce"][3][1:] == (163, 219)          # la tabella del capitolo 17.1 del manuale


def test_brossura_capitolo_17():
    r = cop.calcola(cop.opzioni(210, 148, 12, "brossura"))
    assert r["copertina"] == (216, 328)             # H+2u, 2(L+u+h)+D
    assert [x for x, _ in r["cordonature"]][1:3] == [158, 170]   # inizio e fine del dorso


@pytest.mark.parametrize("dorso, cartone, unghia", [(5, 2, 2.5), (10, 2.5, 3), (24.9, 2.5, 3),
                                                     (25, 3, 3.5), (48, 3, 3.5)])
def test_valori_automatici_secondo_lo_spessore(dorso, cartone, unghia):
    assert cop.default_cartone(dorso) == cartone
    assert cop.default_unghia(dorso) == unghia


def test_arrotondamento_al_mezzo_millimetro():
    assert cop.arrotonda(4.74) == 4.5 and cop.arrotonda(4.76) == 5.0


def test_la_sagoma_pdf_ha_le_dimensioni_del_rivestimento(tmp_path):
    a = cop.opzioni(210, 145, 48, unghia=3, cartone=3, gola=5)
    r = cop.calcola(a)
    cop.esporta_sagoma(a, r, tmp_path / "sagoma.pdf")
    box = PdfReader(str(tmp_path / "sagoma.pdf")).pages[0].mediabox
    assert float(box.width) * 25.4 / 72 == pytest.approx(382, abs=0.1)
    assert float(box.height) * 25.4 / 72 == pytest.approx(246, abs=0.1)


def test_le_frecce_della_fibra_sono_verticali_dentro_ai_pezzi():
    a = cop.opzioni(210, 145, 48)
    r = cop.calcola(a)
    frecce = cop.frecce_fibra(a, r)
    tot_h, tot_l = r["rivestimento"]
    assert len(frecce) == 4                       # rivestimento, due piatti, dorso
    for x, alto, basso in frecce:
        assert 0 < x < tot_l and 0 <= alto < basso <= tot_h
    xs = [x for x, _, _ in frecce[1:]]
    assert xs == sorted(xs)                       # piatto posteriore, dorso, piatto anteriore

    brossura = cop.opzioni(210, 145, 20, "brossura")
    una = cop.frecce_fibra(brossura, cop.calcola(brossura))
    assert len(una) == 1
