"""La calamita dell'anteprima dei tasselli: funzione pura, tutto in mm, y dal basso."""
import random

import pytest

from legatoria.tasselli import calamita

A4 = (210.0, 297.0)


def cala(x, y, w, h, altri=(), soglia=2.0, margine=15.0, pagina=A4):
    return calamita(x, y, w, h, list(altri), soglia, pagina[0], pagina[1], margine)


# ---------------------------------------------------------------- casi scritti a mano

def test_il_bordo_sinistro_si_aggancia_al_bordo_destro_di_un_altro_pezzo():
    altro = (50.0, 100.0, 30.0, 10.0)                       # occupa x da 50 a 80
    x, y, gx, gy = cala(81.5, 100.4, 20.0, 8.0, [altro])     # altezza diversa: si allinea solo in basso
    assert x == pytest.approx(80.0)                          # affiancato, a filo
    assert y == pytest.approx(100.0)                         # e allineato in basso
    assert gx == [80.0] and gy == [100.0]


def test_pezzi_della_stessa_altezza_allineano_bordo_basso_centro_e_bordo_alto_insieme():
    altro = (50.0, 100.0, 30.0, 10.0)
    _x, y, _gx, gy = cala(150.0, 100.6, 20.0, 10.0, [altro])
    assert y == pytest.approx(100.0) and gy == [100.0, 105.0, 110.0]


def test_i_centri_si_allineano():
    altro = (50.0, 100.0, 30.0, 10.0)                        # centro (65, 105)
    x, y, gx, gy = cala(60.0, 200.0, 12.0, 8.0, [altro], soglia=1.5)   # centro x = 66
    assert x + 6.0 == pytest.approx(65.0) and gx == [65.0]
    assert y == 200.0 and gy == []                           # lontano in verticale: niente aggancio


def test_bordi_alti_e_bassi_si_allineano_anche_fra_pezzi_di_altezza_diversa():
    altro = (50.0, 100.0, 30.0, 10.0)                        # dall'alto: y = 110
    x, y, gx, gy = cala(150.0, 103.0, 20.0, 8.0, [altro], soglia=2.0)  # alto = 111 -> a 110
    assert y + 8.0 == pytest.approx(110.0) and gy == [110.0]


def test_si_aggancia_ai_margini_e_al_centro_del_foglio():
    x, y, gx, gy = cala(15.6, 40.0, 30.0, 10.0)              # margine sinistro a 15
    assert x == pytest.approx(15.0) and gx == [15.0]
    x, y, gx, gy = cala(210 - 15 - 30 - 0.7, 40.0, 30.0, 10.0)   # bordo destro sul margine destro (195)
    assert x + 30.0 == pytest.approx(195.0) and gx == [195.0]
    x, y, gx, gy = cala(89.7, 40.0, 30.0, 10.0)              # centro sul centro del foglio (105)
    assert x + 15.0 == pytest.approx(105.0) and gx == [105.0]


def test_oltre_la_soglia_non_si_muove_niente():
    altro = (50.0, 100.0, 30.0, 10.0)
    assert cala(120.0, 200.0, 20.0, 10.0, [altro], soglia=2.0, margine=0.0) == (120.0, 200.0, [], [])
    assert cala(81.5, 200.0, 20.0, 10.0, [altro], soglia=1.0, margine=0.0)[0] == 81.5   # 1,5 mm > 1


def test_i_due_assi_sono_indipendenti():
    altro = (50.0, 100.0, 30.0, 10.0)
    x1, y1, *_ = cala(81.5, 100.8, 20.0, 10.0, [altro])
    x2, y2, *_ = cala(81.5, 260.0, 20.0, 10.0, [altro])
    assert x1 == x2                                          # l'aggancio in x non dipende da y
    assert y2 == 260.0 and y1 == pytest.approx(100.0)


def test_a_parita_si_sceglie_lo_spostamento_piu_piccolo():
    a, b = (50.0, 100.0, 30.0, 10.0), (83.0, 100.0, 30.0, 10.0)       # destre a 80 e 113, sinistre a 50 e 83
    x, *_ = cala(80.6, 40.0, 20.0, 10.0, [a, b], soglia=3.0, margine=0.0)
    assert x == pytest.approx(80.0)                          # 0,6 dal bordo destro di a, non 2,4 dal sinistro di b


def test_piu_allineamenti_contemporanei_mostrano_tutte_le_guide():
    a, b = (50.0, 100.0, 30.0, 10.0), (50.0, 200.0, 45.0, 10.0)       # due pezzi con lo stesso bordo sinistro
    x, y, gx, gy = cala(50.5, 150.0, 20.0, 10.0, [a, b], soglia=1.0, margine=0.0)
    assert x == 50.0 and gx == [50.0]                        # una sola coordinata, non due uguali


def test_soglia_zero_si_aggancia_solo_a_cio_che_e_gia_allineato():
    altro = (50.0, 100.0, 30.0, 10.0)
    assert cala(80.5, 100.0, 20.0, 10.0, [altro], soglia=0.0, margine=0.0)[:2] == (80.5, 100.0)
    x, y, gx, gy = cala(80.0, 100.0, 20.0, 8.0, [altro], soglia=0.0, margine=0.0)
    assert (x, y) == (80.0, 100.0) and gx == [80.0] and gy == [100.0]


def test_soglia_negativa_e_come_zero():
    altro = (50.0, 100.0, 30.0, 10.0)
    assert cala(80.5, 100.5, 20.0, 10.0, [altro], soglia=-3.0, margine=0.0)[:2] == (80.5, 100.5)


# ---------------------------------------------------------------- proprieta' su disposizioni casuali

def _caso(seme):
    caso = random.Random(seme)
    altri = [(caso.uniform(0, 180), caso.uniform(0, 270), caso.uniform(5, 60), caso.uniform(5, 60))
             for _ in range(caso.randint(0, 6))]
    mobile = (caso.uniform(0, 180), caso.uniform(0, 270), caso.uniform(5, 60), caso.uniform(5, 60))
    return mobile, altri, caso.uniform(0.2, 4.0), caso.choice([0.0, 10.0, 15.0])


def _bersagli(altri, dim_pagina, margine, asse):
    i, d = (0, 2) if asse == "x" else (1, 3)
    t = [o[i] + k for o in altri for k in (0.0, o[d], o[d] / 2.0)]
    return t + [margine, dim_pagina - margine, dim_pagina / 2.0]


@pytest.mark.parametrize("seme", range(200))
def test_proprieta_generali(seme):
    (x, y, w, h), altri, soglia, margine = _caso(seme)
    nx, ny, gx, gy = calamita(x, y, w, h, altri, soglia, A4[0], A4[1], margine)
    for (pos, npos, dim, asse, guide, pagina) in ((x, nx, w, "x", gx, A4[0]), (y, ny, h, "y", gy, A4[1])):
        bersagli = _bersagli(altri, pagina, margine, asse)
        delta_min = min((abs(t - (pos + f)) for t in bersagli for f in (0.0, dim / 2.0, dim)), default=None)
        assert abs(npos - pos) <= soglia + 1e-9, "si e' spostato piu' della soglia"
        if delta_min is not None and delta_min <= soglia:
            assert abs(npos - pos) == pytest.approx(delta_min, abs=1e-9), "non ha scelto il piu' vicino"
            assert guide, "aggancio senza linea guida"
            for g in guide:                                  # ogni guida e' un bersaglio con cui il pezzo e' allineato
                assert any(abs(g - t) < 1e-5 for t in bersagli)
                assert any(abs(g - (npos + f)) < 1e-5 for f in (0.0, dim / 2.0, dim))
        else:
            assert npos == pos and guide == [], "si e' mosso senza niente a portata"


@pytest.mark.parametrize("seme", range(200))
def test_e_idempotente(seme):
    """Agganciare un pezzo gia' agganciato non lo sposta piu'."""
    (x, y, w, h), altri, soglia, margine = _caso(seme)
    nx, ny, gx, gy = calamita(x, y, w, h, altri, soglia, A4[0], A4[1], margine)
    assert calamita(nx, ny, w, h, altri, soglia, A4[0], A4[1], margine) == (
        pytest.approx(nx, abs=1e-9), pytest.approx(ny, abs=1e-9), gx, gy)


@pytest.mark.parametrize("seme", range(100))
def test_gli_assi_non_si_influenzano(seme):
    (x, y, w, h), altri, soglia, margine = _caso(seme)
    nx, _ny, gx, _gy = calamita(x, y, w, h, altri, soglia, A4[0], A4[1], margine)
    caso = random.Random(seme + 1000)
    nx2, *_ = calamita(x, caso.uniform(0, 270), w, h, altri, soglia, A4[0], A4[1], margine)
    assert nx2 == nx, "l'aggancio in x e' cambiato spostando il pezzo in verticale"
