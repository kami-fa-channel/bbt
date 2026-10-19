import dataclasses
import os

import pytest

from legatoria import tasselli as tl


@pytest.fixture
def config(tmp_path, monkeypatch):
    """Una Config con un font TrueType di sistema, senza toccare la cartella dell'utente."""
    monkeypatch.setattr(tl, "CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(tl, "FONT_CACHE", str(tmp_path / "font_cache.json"))
    fonts = [f for f in tl.scan_fonts(use_cache=False) if f.supported]
    if not fonts:
        pytest.skip("nessun font TrueType di sistema")
    f = fonts[0]
    return tl.Config(font_path=f.path, font_index=f.index, font_label=f"{f.family} {f.style}")


def test_senza_font_e_un_errore_chiaro():
    with pytest.raises(ValueError, match="font"):
        tl.build_pdf(tl.Config(), "/tmp/inutile.pdf")


def test_tasselli_di_default(config, tmp_path):
    info = tl.build_pdf(config, str(tmp_path / "t.pdf"))
    assert info["tasselli"] == 3 and info["pagine"] == 1
    assert info["overflow"] == [] and info["fuori_foglio"] == []


def test_serie_multiple_moltiplicano_i_tasselli(config, tmp_path):
    info = tl.build_pdf(dataclasses.replace(config, serie=3), str(tmp_path / "t.pdf"))
    assert info["tasselli"] == 9


def test_pagina_di_prova_aggiunge_pagine(config, tmp_path):
    info = tl.build_pdf(dataclasses.replace(config, prova=True), str(tmp_path / "t.pdf"))
    assert info["pagine"] >= 2


def test_config_sopravvive_al_salvataggio(config):
    d = dataclasses.asdict(dataclasses.replace(config, titolo="Prova\nseconda riga", serie=2))
    assert tl.config_da_dict(d) == dataclasses.replace(config, titolo="Prova\nseconda riga", serie=2)


def _con_base(config, indice, **modifiche):
    tasselli = [dataclasses.replace(t) for t in config.tasselli]
    tasselli[indice] = dataclasses.replace(tasselli[indice], **modifiche)
    return dataclasses.replace(config, tasselli=tasselli)


def test_la_base_da_incollare_e_un_pezzo_a_parte_che_sporge(config):
    pezzi = {t.nome: t for t, *_ in tl.disponi(_con_base(config, 2, cornice_mm=1.5))}
    assert sorted(pezzi) == ["Dorso 1", "Dorso 2", "Dorso 2 (base)", "Piatto"]
    base, dorso = pezzi["Dorso 2 (base)"], pezzi["Dorso 2"]
    assert base.larghezza_mm == dorso.larghezza_mm + 3 and base.altezza_mm == dorso.altezza_mm + 3
    assert base.composizione == tl.VUOTO and not base.decoro       # niente testo, niente cornice stampata


def test_senza_sporgenza_o_con_il_tassello_disattivato_la_base_non_c_e(config):
    """Regressione: con Dorso 2 disattivato la base non si vede, ma il valore resta nella
    configurazione: riattivandolo la base ricompariva (e sembrava un pezzo non richiesto)."""
    assert not any("(base)" in t.nome for t, *_ in tl.disponi(config))
    disattivato = _con_base(config, 2, cornice_mm=1.5, attivo=False)
    assert not any("(base)" in t.nome for t, *_ in tl.disponi(disattivato))
    riattivato = dataclasses.replace(disattivato, tasselli=[
        dataclasses.replace(t, attivo=True) if t.nome == "Dorso 2" else t for t in disattivato.tasselli])
    assert any(t.nome == "Dorso 2 (base)" for t, *_ in tl.disponi(riattivato))


def test_la_base_segue_le_copie_e_le_serie(config):
    cfg = dataclasses.replace(_con_base(config, 2, cornice_mm=1.5, copie=2), serie=2)
    nomi = [t.nome for t, *_ in tl.disponi(cfg)]           # i pezzi della serie 2 hanno il suffisso " #2"
    for nome in ("Dorso 2", "Dorso 2 (base)", "Dorso 2 #2", "Dorso 2 (base) #2"):
        assert nomi.count(nome) == 2, nome


# ---------------------------------------------------------------------------
# Linee estese: i bordi di ogni pezzo prolungati fuori dagli angoli
# ---------------------------------------------------------------------------

import math
import random

STILE = "contorno + linee estese"


def _cfg(base=None, **modifiche):
    base = base or tl.Config()
    return dataclasses.replace(base, bordo_stile=STILE, **modifiche)


def _cfg_manuale(pezzi, **modifiche):
    """Una Config con i soli pezzi indicati, in posizione libera.
    pezzi = [(x_mm da sinistra, y_mm dall'alto, larghezza_mm, altezza_mm)]."""
    modello = tl.Config().tasselli[0]
    tasselli = [dataclasses.replace(modello, nome="P%d" % (i + 1), auto=False, x_mm=x, y_mm=y,
                                    larghezza_mm=w, altezza_mm=h, composizione=tl.VUOTO, decoro=False)
                for i, (x, y, w, h) in enumerate(pezzi)]
    return _cfg(tasselli=tasselli, **modifiche)


def _rett_mm(piazzati):
    return [(t.nome, x / tl.mm, y / tl.mm, t.larghezza_mm, t.altezza_mm) for t, x, y, _s, _o in piazzati]


def _segmenti_mm(linee):
    return [tuple(v / tl.mm for v in seg) for seg in linee.segmenti]


def test_gli_stili_nuovi_sono_elencati():
    assert "linee estese" in tl.BORDER_STYLES and STILE in tl.BORDER_STYLES


def test_ogni_pezzo_ha_otto_linee_sul_prolungamento_dei_suoi_bordi():
    cfg = _cfg_manuale([(60, 100, 40, 20)], linee_offset_mm=1.0, linee_lung_mm=8.0)
    (nome, x, y, w, h), = _rett_mm(tl.disponi(cfg))
    segmenti = _segmenti_mm(tl.segmenti_linee_estese(cfg, tl.disponi(cfg)))
    assert len(segmenti) == 8
    trovate = set()
    for x1, y1, x2, y2 in segmenti:
        assert math.hypot(x2 - x1, y2 - y1) == pytest.approx(8.0, abs=0.01)      # lung. dal punto di partenza
        if abs(y1 - y2) < 1e-6:                                    # orizzontale: sta sulla linea del bordo alto o basso
            assert min(abs(y1 - y), abs(y1 - (y + h))) < 1e-6
            a, b = sorted((x1, x2))
            assert b <= x - 1.0 + 1e-6 or a >= x + w + 1.0 - 1e-6  # fuori dal pezzo, parte a 1 mm dall'angolo
            trovate.add(("H", round(y1 - y, 3), "sx" if b <= x else "dx"))
        else:                                                      # verticale: sta sulla linea del bordo sinistro o destro
            assert abs(x1 - x2) < 1e-6 and min(abs(x1 - x), abs(x1 - (x + w))) < 1e-6
            a, b = sorted((y1, y2))
            assert b <= y - 1.0 + 1e-6 or a >= y + h + 1.0 - 1e-6
            trovate.add(("V", round(x1 - x, 3), "giu" if b <= y else "su"))
    assert len(trovate) == 8, "due linee per ciascuno dei quattro bordi, una per lato"


def test_gli_altri_stili_non_disegnano_linee_estese():
    for stile in ("nessuno", "contorno", "contorno tratteggiato", "crocini agli angoli", "contorno + crocini"):
        cfg = dataclasses.replace(tl.Config(), bordo_stile=stile)
        assert tl.segmenti_linee_estese(cfg, tl.disponi(cfg)).segmenti == [], stile


def test_la_distanza_fra_i_pezzi_sale_da_sola_solo_con_le_linee_estese():
    assert tl.gap_effettivo_mm(dataclasses.replace(tl.Config(), bordo_stile="contorno")) == 12.0
    cfg = _cfg(linee_offset_mm=0.5, linee_lung_mm=10.0)
    assert tl.distanza_minima_linee_mm(cfg) == 21.5
    assert tl.gap_effettivo_mm(cfg) == 21.5
    assert tl.gap_effettivo_mm(_cfg(gap_mm=40.0)) == 40.0, "una distanza gia' maggiore non si tocca"
    assert tl.serie_gap_effettivo_mm(cfg) == 21.5
    # e la disposizione la usa davvero: fra due pezzi affiancati ci sono almeno 21,5 mm
    modello = tl.Config().tasselli[0]
    due = _cfg(tasselli=[dataclasses.replace(modello, nome="A", larghezza_mm=30, altezza_mm=10),
                         dataclasses.replace(modello, nome="B", larghezza_mm=30, altezza_mm=10)])
    (_, xa, _, wa, _), (_, xb, _, _, _) = _rett_mm(tl.disponi(due))
    assert xb - (xa + wa) == pytest.approx(21.5, abs=0.01)


def test_le_linee_stanno_per_intero_quando_c_e_spazio():
    cfg = _cfg()
    linee = tl.segmenti_linee_estese(cfg, tl.disponi(cfg))
    assert len(linee.segmenti) == 8 * len(tl.disponi(cfg))
    assert linee.vicine_ad_altri_pezzi == [] and linee.vicine_al_bordo == []
    assert tl.avvisi_linee(cfg, linee) == []


def test_fra_due_pezzi_vicini_ogni_linea_si_ferma_a_meta_strada():
    """Due pezzi allineati a 6 mm l'uno dall'altro: la linea di A verso B si ferma a 3 mm
    dal proprio angolo (meta' dello spazio), e cosi' quella di B verso A."""
    cfg = _cfg_manuale([(50, 100, 30, 10), (86, 100, 30, 10)], linee_offset_mm=0.5, linee_lung_mm=10.0)
    linee = tl.segmenti_linee_estese(cfg, tl.disponi(cfg))
    # le linee orizzontali di A verso B partono a 80,5 (80 + offset) e finiscono a meta' strada
    fine_a = [max(x1, x2) for x1, y1, x2, y2 in _segmenti_mm(linee)
              if abs(y1 - y2) < 1e-6 and min(x1, x2) == pytest.approx(80.5, abs=1e-6)]
    assert len(fine_a) == 2                                     # bordo alto e bordo basso
    assert fine_a == [pytest.approx(83.0, abs=0.05)] * 2        # 80 + 6/2
    assert linee.vicine_ad_altri_pezzi == ["P1", "P2"]
    frasi = tl.avvisi_linee(cfg, linee)
    assert len(frasi) == 1 and "pezzi troppo vicini" in frasi[0] and "22 mm" in frasi[0]
    assert "P1, P2" in frasi[0]


def test_vicino_al_bordo_del_foglio_le_linee_si_fermano_a_3_mm():
    cfg = _cfg_manuale([(8, 100, 30, 10)], linee_offset_mm=0.5, linee_lung_mm=10.0)
    linee = tl.segmenti_linee_estese(cfg, tl.disponi(cfg))
    assert min(min(x1, x2) for x1, y1, x2, y2 in _segmenti_mm(linee)) == pytest.approx(3.0, abs=0.05)
    assert linee.vicine_al_bordo == ["P1"] and linee.vicine_ad_altri_pezzi == []
    assert "bordo del foglio" in tl.avvisi_linee(cfg, linee)[0]


def test_pezzi_sovrapposti_perdono_le_linee_che_entrerebbero_nell_altro_e_lo_segnalano():
    cfg = _cfg_manuale([(50, 100, 30, 10), (50, 102, 30, 10)])            # sovrapposti
    piazzati = tl.disponi(cfg)
    linee = tl.segmenti_linee_estese(cfg, piazzati)
    assert 0 < len(linee.segmenti) < 16 and linee.vicine_ad_altri_pezzi == ["P1", "P2"]
    rett = [(x, y, w, h) for _n, x, y, w, h in _rett_mm(piazzati)]
    for (x1, y1, x2, y2), i in zip(_segmenti_mm(linee), linee.proprietari):
        altro = rett[1 - i]
        for k in range(21):                                    # nessun punto di nessuna linea tocca l'altro pezzo
            px, py = x1 + (x2 - x1) * k / 20, y1 + (y2 - y1) * k / 20
            assert not (altro[0] <= px <= altro[0] + altro[2] and altro[1] <= py <= altro[1] + altro[3])


@pytest.mark.parametrize("seme", range(40))
def test_ogni_linea_sta_piu_vicina_al_proprio_pezzo_che_a_qualunque_altro(seme):
    """La proprieta' che rende le linee usabili: dopo il ritaglio grossolano, una linea
    che sta sul margine di un pezzo e' sempre quella di quel pezzo."""
    caso = random.Random(seme)
    pezzi, occupati = [], []
    while len(pezzi) < 5:
        w, h = caso.uniform(10, 60), caso.uniform(8, 60)
        x, y = caso.uniform(10, 150), caso.uniform(10, 240)
        r = (x - 2, y - 2, w + 4, h + 4)
        if all(r[0] + r[2] < o[0] or o[0] + o[2] < r[0] or r[1] + r[3] < o[1] or o[1] + o[3] < r[1]
               for o in occupati):                                          # niente pezzi sovrapposti
            pezzi.append((x, y, w, h))
            occupati.append(r)
    cfg = _cfg_manuale(pezzi, linee_offset_mm=caso.uniform(0, 2), linee_lung_mm=caso.uniform(5, 25))
    piazzati = tl.disponi(cfg)
    rett = [(x, y, w, h) for _n, x, y, w, h in _rett_mm(piazzati)]
    pw, ph = cfg.pagina_pt()
    pw, ph = pw / tl.mm, ph / tl.mm

    def dist(px, py, r):
        x, y, w, h = r
        return math.hypot(max(x - px, 0, px - (x + w)), max(y - py, 0, py - (y + h)))

    linee = tl.segmenti_linee_estese(cfg, piazzati)
    assert len(linee.segmenti) == len(linee.proprietari)
    for (x1, y1, x2, y2), i in zip(_segmenti_mm(linee), linee.proprietari):
        proprio = rett[i]
        altri = [r for j, r in enumerate(rett) if j != i]
        lungh = math.hypot(x2 - x1, y2 - y1)
        assert lungh <= cfg.linee_lung_mm + 1e-6
        passi = max(2, int(lungh / 0.1))
        for k in range(passi + 1):
            px, py = x1 + (x2 - x1) * k / passi, y1 + (y2 - y1) * k / passi
            assert tl.MARGINE_LINEE_MM - 1e-6 <= px <= pw - tl.MARGINE_LINEE_MM + 1e-6
            assert tl.MARGINE_LINEE_MM - 1e-6 <= py <= ph - tl.MARGINE_LINEE_MM + 1e-6
            propria = dist(px, py, proprio)
            for altro in altri:
                assert dist(px, py, altro) + 1e-3 >= max(propria, tl.LINEE_LIBERO_MM), \
                    "una linea e' piu' vicina a un altro pezzo che al proprio (o gli sta troppo addosso)"


def test_la_distanza_e_l_offset_negativi_o_nulli_non_rompono_niente():
    cfg = _cfg(linee_offset_mm=-3.0, linee_lung_mm=0.0)
    assert tl.segmenti_linee_estese(cfg, tl.disponi(cfg)).segmenti == []


def test_un_file_salvato_prima_delle_linee_estese_si_apre_con_i_valori_di_default():
    vecchio = dataclasses.asdict(tl.Config())
    del vecchio["linee_offset_mm"], vecchio["linee_lung_mm"]
    cfg = tl.config_da_dict(vecchio)
    assert (cfg.linee_offset_mm, cfg.linee_lung_mm) == (0.5, 10.0)


def test_i_crocini_restano_quelli_di_prima():
    segmenti = tl.segmenti_crocini(100.0, 200.0, 50.0, 30.0, tl.Config())
    assert len(segmenti) == 8
    off, ln = 1.5 * tl.mm, 4.0 * tl.mm
    assert segmenti[0] == (100.0 - off, 200.0, 100.0 - off - ln, 200.0)
    assert segmenti[1] == (100.0, 200.0 - off, 100.0, 200.0 - off - ln)


# ---- il PDF vero

def _scuri(immagine):
    """Quanti pixel scuri (sotto 200 su 255) ci sono in un'immagine a toni di grigio."""
    return sum(immagine.histogram()[:200])


def _pixel_scuri(pdf, pagina, x_mm, y_mm, mm_pagina_h, raggio_mm=0.6):
    """Pixel scuri attorno a (x_mm, y_mm), con y dal basso, nella pagina indicata."""
    pdfium = pytest.importorskip("pypdfium2")
    px_per_mm = 8.0
    img = pdfium.PdfDocument(str(pdf))[pagina].render(scale=px_per_mm * 25.4 / 72).to_pil().convert("L")
    cx, cy = int(round(x_mm * px_per_mm)), int(round((mm_pagina_h - y_mm) * px_per_mm))
    r = int(raggio_mm * px_per_mm)
    return _scuri(img.crop((max(cx - r, 0), max(cy - r, 0), cx + r + 1, cy + r + 1)))


def test_il_pdf_contiene_le_linee_estese_e_solo_con_lo_stile_nuovo(config, tmp_path):
    cfg = dataclasses.replace(config, bordo_stile=STILE, bordo_grigio=0.0, bordo_spessore_mm=0.2)
    piazzati = tl.disponi(cfg)
    (t, x, y, _s, _o) = piazzati[0]                                  # il piatto, in alto a sinistra
    x_mm, y_mm = x / tl.mm, y / tl.mm
    ph_mm = cfg.pagina_pt()[1] / tl.mm
    # un punto a 5 mm dall'angolo in alto a destra, sul prolungamento del bordo alto
    sul_prolungamento = (x_mm + t.larghezza_mm + 5.0, y_mm + t.altezza_mm)
    pdf = tmp_path / "estese.pdf"
    tl.build_pdf(cfg, str(pdf))
    assert _pixel_scuri(pdf, 0, *sul_prolungamento, ph_mm) > 0
    # lo stesso punto senza linee estese e' vuoto (nessun altro pezzo ci passa)
    solo_contorno = tmp_path / "contorno.pdf"
    tl.build_pdf(dataclasses.replace(cfg, bordo_stile="contorno"), str(solo_contorno))
    assert _pixel_scuri(solo_contorno, 0, *sul_prolungamento, ph_mm) == 0


def test_con_la_pagina_separata_le_linee_vanno_solo_sulla_pagina_delle_guide(config, tmp_path):
    cfg = dataclasses.replace(config, bordo_stile=STILE, bordo_grigio=0.0, bordo_spessore_mm=0.2,
                              bordo_pagina_separata=True)
    (t, x, y, _s, _o) = tl.disponi(cfg)[0]
    ph_mm = cfg.pagina_pt()[1] / tl.mm
    punto = (x / tl.mm + t.larghezza_mm + 5.0, y / tl.mm + t.altezza_mm)
    pdf = tmp_path / "separata.pdf"
    info = tl.build_pdf(cfg, str(pdf))
    assert info["pagine"] == 2
    assert _pixel_scuri(pdf, 0, *punto, ph_mm) == 0, "la pagina col testo (quella da dorare) non deve avere le guide"
    assert _pixel_scuri(pdf, 1, *punto, ph_mm) > 0


def test_build_pdf_riferisce_le_linee_accorciate(config):
    lontani = dataclasses.replace(config, bordo_stile=STILE)
    modello = config.tasselli[0]
    vicini = dataclasses.replace(config, bordo_stile=STILE, tasselli=[
        dataclasses.replace(modello, nome="A", auto=False, x_mm=50, y_mm=100, larghezza_mm=30, altezza_mm=10),
        dataclasses.replace(modello, nome="B", auto=False, x_mm=86, y_mm=100, larghezza_mm=30, altezza_mm=10)])
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        info = tl.build_pdf(vicini, os.path.join(d, "x.pdf"))
        assert info["linee_accorciate"] == ["A", "B"]
        assert len(info["avvisi_linee"]) == 1 and "pezzi troppo vicini" in info["avvisi_linee"][0]
        ok = tl.build_pdf(lontani, os.path.join(d, "y.pdf"))
        assert ok["linee_accorciate"] == [] and ok["avvisi_linee"] == []


def test_la_pagina_di_prova_con_le_sole_linee_estese_ha_comunque_un_contorno(config, tmp_path):
    """Le celle della pagina di prova sono troppo vicine per le linee estese, e con questo
    stile non c'e' contorno: senza un ripiego resterebbero senza bordo."""
    cfg = dataclasses.replace(config, bordo_stile="linee estese", prova=True,
                              bordo_grigio=0.0, bordo_spessore_mm=0.2)
    pdf = tmp_path / "prova.pdf"
    info = tl.build_pdf(cfg, str(pdf))
    assert info["pagine"] >= 2
    base = cfg.tasselli[0]
    ph_mm = cfg.pagina_pt()[1] / tl.mm
    # un punto sul bordo sinistro della prima cella (in alto a sinistra), a meta' altezza:
    # li' c'e' solo il contorno, il testo e' piu' all'interno
    sul_bordo = (cfg.margine_mm, ph_mm - cfg.margine_mm - base.altezza_mm / 2.0)
    assert _pixel_scuri(pdf, 1, *sul_bordo, ph_mm) > 0, "la cella della pagina di prova non ha bordo"
    # e fuori dal bordo, a 3 mm, non c'e' niente
    assert _pixel_scuri(pdf, 1, sul_bordo[0] - 3.0, sul_bordo[1], ph_mm) == 0


def test_solo_linee_estese_non_stampa_il_contorno_ma_contorno_piu_linee_si(config, tmp_path):
    """Il cancelletto senza il quadretto: con lo stile "linee estese" il bordo del pezzo e' vuoto
    (le linee restano fuori dagli angoli), con "contorno + linee estese" c'e' anche il contorno."""
    ph_mm = config.pagina_pt()[1] / tl.mm
    base = dataclasses.replace(config, bordo_grigio=0.0, bordo_spessore_mm=0.2)
    (t, x, y, _s, _o) = tl.disponi(dataclasses.replace(base, bordo_stile=STILE))[0]
    x_mm, y_mm = x / tl.mm, y / tl.mm
    meta_bordo_alto = (x_mm + t.larghezza_mm / 2.0, y_mm + t.altezza_mm)
    sul_prolungamento = (x_mm + t.larghezza_mm + 5.0, y_mm + t.altezza_mm)
    for stile, contorno in (("linee estese", False), (STILE, True), ("contorno", True)):
        pdf = tmp_path / ("%s.pdf" % stile.replace(" ", "_").replace("+", "e"))
        tl.build_pdf(dataclasses.replace(base, bordo_stile=stile), str(pdf))
        assert (_pixel_scuri(pdf, 0, *meta_bordo_alto, ph_mm) > 0) is contorno, stile
        assert (_pixel_scuri(pdf, 0, *sul_prolungamento, ph_mm) > 0) is ("estese" in stile), stile


# ---------------------------------------------------------------------------
# I campi decimali devono restare decimali
# ---------------------------------------------------------------------------

def test_i_campi_float_restano_float_anche_se_creati_con_un_intero():
    """Regressione: Tassello(larghezza_mm=95) teneva un intero, la finestra ne faceva un campo
    intero e una larghezza di 23,5 mm diventava 23."""
    t = tl.Tassello(larghezza_mm=95, altezza_mm=32, y_mm=60, raggio_mm=2, rotazione=90, copie=2)
    assert all(isinstance(getattr(t, n), float) for n in ("larghezza_mm", "altezza_mm", "y_mm", "raggio_mm"))
    assert isinstance(t.rotazione, int) and isinstance(t.copie, int), "i campi interi restano interi"
    assert isinstance(t.attivo, bool) and t.attivo is True, "i booleani non si toccano"
    c = tl.Config(margine_mm=15, gap_mm=12, serie=2)
    assert isinstance(c.margine_mm, float) and isinstance(c.gap_mm, float) and isinstance(c.serie, int)


def test_i_tasselli_di_partenza_hanno_tutti_i_campi_float_decimali():
    for t in tl.Config().tasselli:
        for f in dataclasses.fields(tl.Tassello):
            if f.type == "float":
                assert isinstance(getattr(t, f.name), float), (t.nome, f.name)


def test_un_file_salvato_con_numeri_interi_si_apre_con_campi_decimali():
    """I file scritti dalle versioni con il difetto hanno "larghezza_mm": 95 (intero)."""
    d = dataclasses.asdict(tl.Config())
    for t in d["tasselli"]:
        t["larghezza_mm"], t["altezza_mm"], t["y_mm"] = 95, 32, 60
    d["margine_mm"], d["gap_mm"] = 15, 12
    cfg = tl.config_da_dict(d)
    assert all(isinstance(t.larghezza_mm, float) and isinstance(t.y_mm, float) for t in cfg.tasselli)
    assert isinstance(cfg.margine_mm, float) and isinstance(cfg.gap_mm, float)
    assert cfg.tasselli[0].larghezza_mm == 95.0


def test_dataclasses_replace_mantiene_i_decimali():
    t = tl.Tassello(larghezza_mm=95)
    assert isinstance(dataclasses.replace(t, altezza_mm=40).altezza_mm, float)
    assert dataclasses.replace(t, larghezza_mm=23.5).larghezza_mm == 23.5


# ---------------------------------------------------------------------------
# Decoro "fleuron agli angoli": geometria pura
# ---------------------------------------------------------------------------

def test_fleuron_agli_angoli_e_elencato():
    assert "fleuron agli angoli" in tl.DECORI


def test_curve_fleuron_angolo_conta_e_radicamento():
    curve = tl.curve_fleuron_angolo(11.0)
    assert len(curve) == 17                                        # 2 foglie x 7 + ricciolo x 3
    radicate = sum(1 for x0, y0, *_c, x1, y1 in curve
                   if math.hypot(x0, y0) < 1e-9 or math.hypot(x1, y1) < 1e-9)
    assert radicate == 5                                            # le due basi delle foglie + inizio ricciolo... vedi sotto
    senza = tl.curve_fleuron_angolo(11.0, con_ricciolo=False)
    assert len(senza) == 14


def test_curve_fleuron_centrale_conta_e_apertura_simmetrica():
    curve = tl.curve_fleuron_centrale(7.0)
    assert len(curve) == 14                                         # 2 foglie x 7
    # le due foglie partono entrambe dall'origine e si aprono a specchio rispetto
    # all'asse Y: stessa distanza dall'origine, angoli simmetrici rispetto a 90 gradi
    prima, seconda = curve[0], curve[7]                             # primo tratto di ciascuna foglia
    assert math.hypot(prima[0], prima[1]) < 1e-9 and math.hypot(seconda[0], seconda[1]) < 1e-9
    ang1 = math.degrees(math.atan2(prima[7] - prima[1], prima[6] - prima[0]))
    ang2 = math.degrees(math.atan2(seconda[7] - seconda[1], seconda[6] - seconda[0]))
    assert (ang1 - 90) == pytest.approx(-(ang2 - 90), abs=1e-6)


def test_le_curve_scalano_linearmente_con_la_dimensione():
    a = tl.curve_fleuron_angolo(10.0, con_ricciolo=False)
    b = tl.curve_fleuron_angolo(20.0, con_ricciolo=False)
    for ca, cb in zip(a, b):
        assert all(y == pytest.approx(x * 2, abs=1e-9) for x, y in zip(ca, cb))


def test_ruota_curva_e_isometrica_e_compone():
    c = (3.0, 1.0, 5.0, 2.0, 6.0, -1.0, 8.0, 0.0)

    def lunghezza_corda(curva):
        x0, y0, *_c, x1, y1 = curva
        return math.hypot(x1 - x0, y1 - y0)

    r90 = tl.ruota_curva(c, 90)
    assert lunghezza_corda(r90) == pytest.approx(lunghezza_corda(c), abs=1e-9)
    doppia = tl.ruota_curva(tl.ruota_curva(c, 40), 50)
    diretta = tl.ruota_curva(c, 90)
    assert all(a == pytest.approx(b, abs=1e-7) for a, b in zip(doppia, diretta))
    giro = tl.ruota_curva(c, 360)
    assert all(a == pytest.approx(b, abs=1e-7) for a, b in zip(giro, c))


def test_campiona_curva_include_gli_estremi_e_rispetta_la_retta():
    # controlli coincidenti con gli estremi: la curva e' geometricamente una retta
    # (anche se i punti non sono equispaziati lungo di essa, essendo Bezier cubica)
    curva = (0.0, 0.0, 0.0, 0.0, 10.0, 0.0, 10.0, 0.0)
    punti = tl.campiona_curva(curva, passi=5)
    assert len(punti) == 6
    assert punti[0] == (0.0, 0.0) and punti[-1] == (10.0, 0.0)
    assert all(y == pytest.approx(0.0, abs=1e-9) for _x, y in punti)            # tutti sull'asse X
    xs = [x for x, _y in punti]
    assert xs == sorted(xs) and len(set(xs)) == 6                              # crescenti, tutti distinti


def test_campiona_curva_segue_davvero_una_curva_non_degenere():
    curva = (0.0, 0.0, 3.0, 8.0, 7.0, 8.0, 10.0, 0.0)               # un arco, non una retta
    punti = tl.campiona_curva(curva, passi=8)
    assert len(punti) == 9 and punti[0] == (0.0, 0.0) and punti[-1] == (10.0, 0.0)
    assert max(y for _x, y in punti) > 3.0                                     # si alza a arco


def test_dim_fleuron_rispetta_il_campo_entro_il_limite_geometrico():
    """Il limite e' 0.52 del lato corto (non un terzo, corretto perche' con quello
    il valore di default 11 mm risultava gia' quasi al massimo sui tasselli tipici,
    e il campo sembrava non avere effetto)."""
    cfg = dataclasses.replace(tl.Config(), decoro_fleuron_dim_mm=11.0)
    assert tl.dim_fleuron(cfg, 95 * tl.mm, 60 * tl.mm) == pytest.approx(11.0 * tl.mm)   # 11 < 60 * 0.52
    piccolo = tl.dim_fleuron(cfg, 18 * tl.mm, 18 * tl.mm)           # 18 * 0.52 = 9.36, meno di 11
    assert piccolo == pytest.approx(18 * 0.52 * tl.mm)
    assert tl.dim_fleuron(dataclasses.replace(cfg, decoro_fleuron_dim_mm=-3.0), 40 * tl.mm, 40 * tl.mm) > 0


def test_dim_fleuron_permette_di_ingrandire_le_foglie_sui_tasselli_di_default():
    """Regressione: con il vecchio limite (un terzo del lato corto) il valore di
    default (11 mm) era gia' al massimo su tutti e tre i tasselli di partenza, e
    aumentare il campo non aveva alcun effetto visibile."""
    for larghezza, altezza in ((95.0, 32.0), (24.0, 85.0), (24.0, 40.0)):
        w, h = larghezza * tl.mm, altezza * tl.mm
        base = tl.dim_fleuron(dataclasses.replace(tl.Config(), decoro_fleuron_dim_mm=11.0), w, h)
        assert base == pytest.approx(11.0 * tl.mm), (larghezza, altezza)      # 11 mm non e' piu' tagliato
        piu_grande = tl.dim_fleuron(dataclasses.replace(tl.Config(), decoro_fleuron_dim_mm=16.0), w, h)
        assert piu_grande > base, (larghezza, altezza)                        # e crescere ha effetto


def test_dim_fleuron_impedisce_comunque_la_sovrapposizione_fra_angoli_opposti():
    """La proiezione di una foglia lungo il lato e' lunghezza * cos(30 gradi): due
    foglie di angoli opposti si toccherebbero quando 2 * dim * cos(30) >= L."""
    L = 30.0
    cfg = dataclasses.replace(tl.Config(), decoro_fleuron_dim_mm=1000.0)       # valore enorme, sempre tagliato
    dim = tl.dim_fleuron(cfg, L * tl.mm, L * tl.mm) / tl.mm
    proiezione_totale = 2 * dim * math.cos(math.radians(30))
    assert proiezione_totale < L, "le foglie di angoli opposti si toccherebbero"


# ---------------------------------------------------------------------------
# Decoro "fleuron agli angoli": nel PDF
# ---------------------------------------------------------------------------

def test_il_fleuron_disegna_qualcosa_vicino_a_ogni_angolo_ma_non_al_centro(config, tmp_path):
    cfg = dataclasses.replace(config, decoro_modello="fleuron agli angoli", bordo_stile="nessuno")
    (t, x, y, _s, _o) = tl.disponi(cfg)[0]                          # il Piatto: 95 x 32 mm
    x_mm, y_mm = x / tl.mm, y / tl.mm
    ph_mm = cfg.pagina_pt()[1] / tl.mm
    pdf = tmp_path / "fleuron.pdf"
    tl.build_pdf(cfg, str(pdf))
    for angolo in ((x_mm + 2, y_mm + 2), (x_mm + t.larghezza_mm - 2, y_mm + 2),
                  (x_mm + 2, y_mm + t.altezza_mm - 2)):
        assert _pixel_scuri(pdf, 0, *angolo, ph_mm, raggio_mm=2.5) > 0, angolo
    # niente accanto al bordo, a meta' strada fra un angolo e il successivo (senza testo li')
    meta_bordo_basso = (x_mm + t.larghezza_mm / 2.0, y_mm)
    assert _pixel_scuri(pdf, 0, *meta_bordo_basso, ph_mm, raggio_mm=1.5) == 0


def test_il_ricciolo_si_puo_disattivare(config, tmp_path):
    """Con il ricciolo attivo, la zona dell'angolo ha piu' inchiostro che senza."""
    cfg = dataclasses.replace(config, decoro_modello="fleuron agli angoli", bordo_stile="nessuno")
    (t, x, y, _s, _o) = tl.disponi(cfg)[0]
    ph_mm = cfg.pagina_pt()[1] / tl.mm
    angolo_alto_sx = (x / tl.mm, y / tl.mm + t.altezza_mm)                    # y dal basso

    pdf_con, pdf_senza = tmp_path / "con.pdf", tmp_path / "senza.pdf"
    tl.build_pdf(dataclasses.replace(cfg, decoro_fleuron_ricciolo=True), str(pdf_con))
    tl.build_pdf(dataclasses.replace(cfg, decoro_fleuron_ricciolo=False), str(pdf_senza))
    scuri_con = _pixel_scuri(pdf_con, 0, *angolo_alto_sx, ph_mm, raggio_mm=7.0)
    scuri_senza = _pixel_scuri(pdf_senza, 0, *angolo_alto_sx, ph_mm, raggio_mm=7.0)
    assert scuri_con > scuri_senza, (scuri_con, scuri_senza)


def test_il_motivo_centrale_si_puo_attivare(config, tmp_path):
    cfg = dataclasses.replace(config, decoro_modello="fleuron agli angoli", bordo_stile="nessuno")
    (t, x, y, _s, _o) = tl.disponi(cfg)[0]
    ph_mm = cfg.pagina_pt()[1] / tl.mm
    meta_bordo_alto = (x / tl.mm + t.larghezza_mm / 2.0, y / tl.mm + t.altezza_mm)
    senza = tmp_path / "senza_centrale.pdf"
    con = tmp_path / "con_centrale.pdf"
    tl.build_pdf(cfg, str(senza))
    tl.build_pdf(dataclasses.replace(cfg, decoro_fleuron_centrale=True), str(con))
    assert _pixel_scuri(senza, 0, *meta_bordo_alto, ph_mm, raggio_mm=1.5) == 0
    assert _pixel_scuri(con, 0, *meta_bordo_alto, ph_mm, raggio_mm=1.5) > 0


def test_il_fleuron_su_un_tassello_piccolo_non_sbordano_ne_si_accavallano(config, tmp_path):
    """Le foglie di due angoli opposti di un pezzo piccolo non devono invadersi a vicenda,
    e nessuna deve finire fuori dal pezzo."""
    modello = config.tasselli[0]
    piccolo = dataclasses.replace(config, bordo_stile="nessuno", decoro_modello="fleuron agli angoli",
                                  decoro_fleuron_dim_mm=20.0,       # volutamente troppo grande
                                  tasselli=[dataclasses.replace(modello, larghezza_mm=18, altezza_mm=18,
                                                                composizione=tl.VUOTO, decoro=True)])
    (t, x, y, _s, _o) = tl.disponi(piccolo)[0]
    ph_mm = piccolo.pagina_pt()[1] / tl.mm
    pdf = tmp_path / "piccolo.pdf"
    tl.build_pdf(piccolo, str(pdf))
    # a meta' di ciascun lato, ben fuori dal raggio delle foglie (che restano vicine agli angoli)
    x_mm, y_mm = x / tl.mm, y / tl.mm
    for punto in ((x_mm + t.larghezza_mm / 2.0, y_mm), (x_mm + t.larghezza_mm / 2.0, y_mm + t.altezza_mm)):
        assert _pixel_scuri(pdf, 0, *punto, ph_mm, raggio_mm=1.0) == 0, punto
    # e fuori dal pezzo (1 mm oltre il bordo) non ci deve essere niente
    fuori = (x_mm - 1.0, y_mm + t.altezza_mm / 2.0)
    assert _pixel_scuri(pdf, 0, *fuori, ph_mm, raggio_mm=0.6) == 0


def test_il_fleuron_non_richiede_scostare_il_testo_come_un_filetto_continuo(config):
    """Le foglie stanno negli angoli, il centro del tassello resta libero: il padding
    utile non deve crescere quanto con un filetto continuo attorno a tutto il bordo."""
    t = config.tasselli[0]
    base = dataclasses.replace(config, decoro_modello="nessuno")
    filetto = dataclasses.replace(config, decoro_modello="filetto semplice", decoro_rientro_mm=2.5)
    fleuron = dataclasses.replace(config, decoro_modello="fleuron agli angoli", decoro_rientro_mm=2.5)
    assert tl.padding_utile(fleuron, t) == tl.padding_utile(base, t)
    assert tl.padding_utile(filetto, t) > tl.padding_utile(base, t)


# ---------------------------------------------------------------------------
# Avviso sullo spessore minimo per la doratura col foil
# ---------------------------------------------------------------------------

def test_avvisi_doratura_segnala_un_decoro_troppo_sottile():
    cfg = dataclasses.replace(tl.Config(), decoro_modello="filetto semplice", decoro_spessore_mm=0.1)
    frasi = tl.avvisi_doratura(cfg)
    assert len(frasi) == 1 and "0.10" in frasi[0] and "0.2" in frasi[0]


def test_avvisi_doratura_non_segnala_uno_spessore_sufficiente():
    cfg = dataclasses.replace(tl.Config(), decoro_modello="filetto semplice", decoro_spessore_mm=0.4)
    assert tl.avvisi_doratura(cfg) == []


def test_avvisi_doratura_non_controlla_niente_senza_decoro_e_senza_filetto():
    cfg = tl.Config(decoro_modello="nessuno", filetto=False)
    assert tl.avvisi_doratura(cfg) == []


def test_avvisi_doratura_controlla_anche_il_filetto_secondario_del_doppio():
    base = dataclasses.replace(tl.Config(), decoro_modello="doppio filetto",
                               decoro_spessore_mm=0.4, decoro_spessore2_mm=0.1)
    frasi = tl.avvisi_doratura(base)
    assert len(frasi) == 1 and "0.10" in frasi[0]
    entrambi_sottili = dataclasses.replace(base, decoro_spessore_mm=0.1)
    assert len(tl.avvisi_doratura(entrambi_sottili)) == 1              # una frase sola, coi due valori
    assert "0.10" in tl.avvisi_doratura(entrambi_sottili)[0]


def test_avvisi_doratura_controlla_il_filetto_fra_i_blocchi():
    cfg = dataclasses.replace(tl.Config(), filetto=True, filetto_spessore_mm=0.15)
    frasi = tl.avvisi_doratura(cfg)
    assert len(frasi) == 1 and "0.15" in frasi[0]
    assert tl.avvisi_doratura(dataclasses.replace(cfg, filetto=False)) == []
    assert tl.avvisi_doratura(dataclasses.replace(cfg, filetto_spessore_mm=0.3)) == []


def test_avvisi_doratura_funziona_col_fleuron():
    cfg = dataclasses.replace(tl.Config(), decoro_modello="fleuron agli angoli", decoro_spessore_mm=0.1)
    assert len(tl.avvisi_doratura(cfg)) == 1
    assert tl.avvisi_doratura(dataclasses.replace(cfg, decoro_spessore_mm=0.4)) == []


def test_build_pdf_riferisce_gli_avvisi_di_doratura(config):
    import tempfile, os
    sottile = dataclasses.replace(config, decoro_modello="filetto semplice", decoro_spessore_mm=0.1)
    with tempfile.TemporaryDirectory() as d:
        info = tl.build_pdf(sottile, os.path.join(d, "x.pdf"))
        assert len(info["avvisi_doratura"]) == 1
        ok = tl.build_pdf(dataclasses.replace(sottile, decoro_spessore_mm=0.4), os.path.join(d, "y.pdf"))
        assert ok["avvisi_doratura"] == []


def test_il_minimo_hard_e_piu_spesso_di_prima(config):
    """Regressione: il minimo hard era 0,02 mm, un tratto praticamente invisibile
    anche a schermo.  Con uno spessore quasi zero il PDF deve comunque usare
    almeno 0,05 mm: lo verifichiamo intercettando le chiamate reali a
    setLineWidth durante la generazione, non ispezionando i pixel (a 0,02 mm
    l'antialiasing lascia comunque qualche pixel scuro, quindi un confronto sui
    pixel non distinguerebbe i due minimi)."""
    import os
    import tempfile

    import reportlab.pdfgen.canvas as rl

    quasi_zero = dataclasses.replace(config, decoro_modello="filetto semplice",
                                     decoro_spessore_mm=0.001)
    catturati = []
    originale = rl.Canvas.setLineWidth

    def spia(self, larghezza):
        catturati.append(larghezza)
        return originale(self, larghezza)

    rl.Canvas.setLineWidth = spia
    try:
        with tempfile.TemporaryDirectory() as d:
            tl.build_pdf(quasi_zero, os.path.join(d, "x.pdf"))
    finally:
        rl.Canvas.setLineWidth = originale
    assert catturati, "nessuna chiamata a setLineWidth intercettata"
    assert min(catturati) >= 0.05 * tl.mm - 1e-9, min(catturati) / tl.mm


# ---------------------------------------------------------------------------
# Decoro continuo: greca, festone, dentelli
# ---------------------------------------------------------------------------

def test_i_tre_stili_continui_sono_elencati():
    for stile in ("greca continua", "festone continuo", "dentelli continui"):
        assert stile in tl.DECORI
        assert stile in tl.DECORI_CONTINUI


def test_stile_sconosciuto_o_normale_non_produce_punti():
    assert tl.punti_bordo_continuo(tl.Config(decoro_modello="filetto semplice"), 0, 0, 95, 32) == []
    assert tl.punti_bordo_continuo(tl.Config(decoro_modello="nessuno"), 0, 0, 95, 32) == []


@pytest.mark.parametrize("stile", ["greca continua", "festone continuo", "dentelli continui"])
def test_ogni_stile_continuo_produce_punti_dentro_al_tassello(stile):
    cfg = dataclasses.replace(tl.Config(), decoro_modello=stile)
    w, h = 95 * tl.mm, 32 * tl.mm
    pts = tl.punti_bordo_continuo(cfg, 0, 0, w, h)
    assert len(pts) >= 8
    margine = 3 * tl.mm            # generoso: festone e dentelli sporgono verso l'interno
    for x, y in pts:
        assert -margine <= x <= w + margine
        assert -margine <= y <= h + margine


@pytest.mark.parametrize("stile", ["greca continua", "festone continuo", "dentelli continui"])
def test_ogni_stile_continuo_forma_un_contorno_chiuso_senza_salti(stile):
    """I punti concatenati, chiudendo l'ultimo sul primo, non devono avere salti
    piu' grandi di un paio di moduli: altrimenti un lato si stacca dal successivo."""
    cfg = dataclasses.replace(tl.Config(), decoro_modello=stile)
    pts = tl.punti_bordo_continuo(cfg, 0, 0, 95 * tl.mm, 32 * tl.mm)
    chiusi = pts + [pts[0]]
    salti = [math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(chiusi, chiusi[1:])]
    limite = 8 * tl.mm             # piu' largo del piu' grande fra modulo/fascia/raggio di default
    assert max(salti) < limite, max(salti) / tl.mm


@pytest.mark.parametrize("stile", ["greca continua", "festone continuo", "dentelli continui"])
def test_funziona_anche_su_un_tassello_stretto_come_un_dorso(stile):
    cfg = dataclasses.replace(tl.Config(), decoro_modello=stile)
    pts = tl.punti_bordo_continuo(cfg, 0, 0, 24 * tl.mm, 85 * tl.mm)      # Dorso 1
    assert len(pts) >= 8
    pts_corto = tl.punti_bordo_continuo(cfg, 0, 0, 24 * tl.mm, 40 * tl.mm)  # Dorso 2, ancora piu' piccolo
    assert len(pts_corto) >= 8


def test_il_rientro_sposta_il_bordo_verso_l_interno():
    largo = dataclasses.replace(tl.Config(), decoro_modello="dentelli continui",
                                decoro_continuo_rientro_mm=1.0)
    stretto = dataclasses.replace(largo, decoro_continuo_rientro_mm=5.0)
    w, h = 95 * tl.mm, 32 * tl.mm
    pts_largo = tl.punti_bordo_continuo(largo, 0, 0, w, h)
    pts_stretto = tl.punti_bordo_continuo(stretto, 0, 0, w, h)
    box_largo = (min(x for x, y in pts_largo), max(x for x, y in pts_largo))
    box_stretto = (min(x for x, y in pts_stretto), max(x for x, y in pts_stretto))
    assert box_stretto[0] > box_largo[0] and box_stretto[1] < box_largo[1]


def test_un_tassello_troppo_piccolo_per_il_rientro_non_produce_punti():
    cfg = dataclasses.replace(tl.Config(), decoro_modello="greca continua",
                              decoro_continuo_rientro_mm=100.0)
    assert tl.punti_bordo_continuo(cfg, 0, 0, 20 * tl.mm, 20 * tl.mm) == []


def test_il_modulo_della_greca_si_adatta_al_lato_senza_tagliarlo_a_meta():
    """Il numero di moduli lungo ogni lato deve essere intero: nessun modulo
    tagliato a meta' in un angolo."""
    for larghezza in (30, 47, 63, 95, 101):        # lati non multipli esatti del modulo
        cfg = tl.Config(decoro_modello="greca continua")
        pts = tl.punti_bordo_continuo(cfg, 0, 0, larghezza * tl.mm, 32 * tl.mm)
        chiusi = pts + [pts[0]]
        salti = [math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(chiusi, chiusi[1:])]
        assert max(salti) < 8 * tl.mm, (larghezza, max(salti) / tl.mm)


@pytest.mark.parametrize("param, campo", [
    ("decoro_continuo_fascia_mm", None),       # la greca: piu' larga la fascia, piu' alto il motivo
    ("decoro_continuo_raggio_mm", None),       # il festone: raggio piu' grande, meno semicerchi
    ("decoro_continuo_altezza_mm", None),      # i dentelli: denti piu' alti
])
def test_i_parametri_dei_singoli_stili_hanno_effetto(param, campo):
    mappa = {"decoro_continuo_fascia_mm": "greca continua",
             "decoro_continuo_raggio_mm": "festone continuo",
             "decoro_continuo_altezza_mm": "dentelli continui"}
    stile = mappa[param]
    piccolo = tl.Config(decoro_modello=stile, **{param: 2.0})
    grande = tl.Config(decoro_modello=stile, **{param: 6.0})
    w, h = 95 * tl.mm, 32 * tl.mm
    pts_piccolo = tl.punti_bordo_continuo(piccolo, 0, 0, w, h)
    pts_grande = tl.punti_bordo_continuo(grande, 0, 0, w, h)
    esteso = lambda pts: max(y for x, y in pts) - min(y for x, y in pts)      # ingombro verticale
    assert esteso(pts_grande) != esteso(pts_piccolo) or len(pts_grande) != len(pts_piccolo)


def test_padding_utile_fa_scostare_il_testo_per_ogni_stile_continuo(config):
    """Ogni stile continuo occupa uno spessore diverso oltre il rientro (vedi
    padding_utile nel motore): qui verifichiamo il valore esatto, non solo che
    sia maggiore del caso senza decoro, perche' un ramo sbagliato di padding_utile
    potrebbe applicare per errore lo scostamento minimo dei filetti normali
    invece di quello giusto per lo stile continuo, e un confronto '>' non lo
    scoprirebbe (l'errato e' comunque positivo)."""
    t = config.tasselli[0]
    base = dataclasses.replace(config, decoro_modello="nessuno")
    attesi = {
        "greca continua": config.decoro_continuo_rientro_mm + config.decoro_continuo_fascia_mm,
        "festone continuo": config.decoro_continuo_rientro_mm + 2 * config.decoro_continuo_raggio_mm,
        "dentelli continui": config.decoro_continuo_rientro_mm + config.decoro_continuo_altezza_mm,
    }
    for stile, occupato in attesi.items():
        cfg = dataclasses.replace(config, decoro_modello=stile)
        assert tl.padding_utile(cfg, t) > tl.padding_utile(base, t), stile
        assert tl.padding_utile(cfg, t) == pytest.approx((occupato + 1.2) * tl.mm, abs=1e-6), stile


def test_padding_utile_cresce_con_i_parametri_dello_stile(config):
    t = config.tasselli[0]
    piccolo = dataclasses.replace(config, decoro_modello="dentelli continui", decoro_continuo_altezza_mm=1.0)
    grande = dataclasses.replace(config, decoro_modello="dentelli continui", decoro_continuo_altezza_mm=5.0)
    assert tl.padding_utile(grande, t) > tl.padding_utile(piccolo, t)


@pytest.mark.parametrize("stile", ["greca continua", "festone continuo", "dentelli continui"])
def test_il_pdf_disegna_davvero_qualcosa_vicino_al_bordo(config, tmp_path, stile):
    modello = config.tasselli[0]
    senza_testo = dataclasses.replace(config, decoro_modello=stile, bordo_stile="nessuno",
                                      decoro_spessore_mm=0.3,
                                      tasselli=[dataclasses.replace(modello, composizione=tl.VUOTO)])
    (t, x, y, _s, _o) = tl.disponi(senza_testo)[0]
    ph_mm = senza_testo.pagina_pt()[1] / tl.mm
    rientro = senza_testo.decoro_continuo_rientro_mm
    x_mm, y_mm = x / tl.mm, y / tl.mm
    pdf = tmp_path / "continuo.pdf"
    tl.build_pdf(senza_testo, str(pdf))
    # a meta' del bordo alto, alla distanza del rientro dal bordo del tassello
    punto = (x_mm + t.larghezza_mm / 2.0, y_mm + t.altezza_mm - rientro)
    assert _pixel_scuri(pdf, 0, *punto, ph_mm, raggio_mm=3.0) > 0, stile
    # al centro del tassello, senza testo, non deve esserci niente
    centro = (x_mm + t.larghezza_mm / 2.0, y_mm + t.altezza_mm / 2.0)
    assert _pixel_scuri(pdf, 0, *centro, ph_mm, raggio_mm=2.0) == 0, stile


def test_avvisi_doratura_funziona_anche_sui_bordi_continui():
    for stile in ("greca continua", "festone continuo", "dentelli continui"):
        cfg = dataclasses.replace(tl.Config(), decoro_modello=stile, decoro_spessore_mm=0.1)
        assert len(tl.avvisi_doratura(cfg)) == 1, stile
        assert tl.avvisi_doratura(dataclasses.replace(cfg, decoro_spessore_mm=0.4)) == [], stile


# ---------------------------------------------------------------------------
# Decoro "cornice bitmap": blocchetti PNG composti senza scalare
# ---------------------------------------------------------------------------

@pytest.fixture
def blocchetti(tmp_path):
    """Otto PNG di 40 x 40 px a 254 dpi (= 4 x 4 mm), con il suffisso dei ruoli."""
    from PIL import Image
    for r in tl.BITMAP_RUOLI:
        Image.new("RGBA", (40, 40), (0, 0, 0, 255)).save(tmp_path / ("fr_%s.png" % r), dpi=(254, 254))
    return str(tmp_path / "fr_")


def _cfg_bitmap(config, prefisso, **extra):
    return dataclasses.replace(config, decoro_modello=tl.DECORO_BITMAP, decoro_bitmap_prefisso=prefisso,
                               decoro_rientro_mm=0.0, **extra)


def test_la_cornice_bitmap_mette_angoli_e_tratti_senza_scalare(config, blocchetti):
    cfg = _cfg_bitmap(config, blocchetti, decoro_bitmap_taglio=False)
    pezzi, motivo = tl.pezzi_bitmap(cfg, 0, 0, 40 * tl.mm, 28 * tl.mm)          # 40 = 10 blocchetti, 28 = 7
    assert motivo is None
    ruoli = [p[0] for p in pezzi]
    assert {r: ruoli.count(r) for r in tl.BITMAP_RUOLI} == {
        "ul": 1, "ur": 1, "ll": 1, "lr": 1, "hu": 8, "hl": 8, "vl": 5, "vr": 5}
    assert all(abs(p[3] - 4 * tl.mm) < 1e-6 and abs(p[4] - 4 * tl.mm) < 1e-6 for p in pezzi)
    assert all(p[5] is None for p in pezzi)


def test_senza_taglio_il_vuoto_resta_ai_capi_con_il_taglio_si_riempie(config, blocchetti):
    w, h = 41 * tl.mm, 28 * tl.mm                      # fra gli angoli restano 33 mm = 8,25 blocchetti
    senza, _ = tl.pezzi_bitmap(_cfg_bitmap(config, blocchetti, decoro_bitmap_taglio=False), 0, 0, w, h)
    con, _ = tl.pezzi_bitmap(_cfg_bitmap(config, blocchetti, decoro_bitmap_taglio=True), 0, 0, w, h)
    assert [p[0] for p in senza].count("hu") == 8 and all(p[5] is None for p in senza)
    hu = [p for p in con if p[0] == "hu"]
    assert len(hu) == 9
    assert all(p[5] is not None for p in hu)           # ritaglio = vuoto fra i due angoli
    assert min(p[1] for p in hu) < 4 * tl.mm - 1e-6    # il primo sconfina sotto l'angolo, ma e' tagliato
    # il taglio e' simmetrico
    assert abs((min(p[1] for p in hu) - 4 * tl.mm) + (max(p[1] + p[3] for p in hu) - (w - 4 * tl.mm))) < 1e-6


def test_angoli_che_non_entrano_danno_un_avviso_e_nessun_disegno(config, blocchetti):
    cfg = _cfg_bitmap(config, blocchetti, decoro_bitmap_taglio=False, decoro_bitmap_riduci=False)
    pezzi, motivo = tl.pezzi_bitmap(cfg, 0, 0, 7 * tl.mm, 28 * tl.mm)
    assert pezzi == [] and motivo
    cfg = dataclasses.replace(cfg, tasselli=[dataclasses.replace(cfg.tasselli[0], larghezza_mm=7.0)])
    assert any("non viene disegnata" in f for f in tl.avvisi_doratura(cfg))


def test_il_dpi_cambia_la_misura_stampata_ma_non_i_pixel(config, blocchetti):
    a = tl.carica_blocchetti(_cfg_bitmap(config, blocchetti))["ul"]
    b = tl.carica_blocchetti(_cfg_bitmap(config, blocchetti, decoro_bitmap_dpi=508))["ul"]
    assert a[0].size == b[0].size == (40, 40)
    assert abs(a[1] / b[1] - 2.0) < 1e-6


def test_file_mancanti_fermano_la_generazione_con_un_messaggio_chiaro(config, blocchetti, tmp_path):
    os.remove(blocchetti + "hu.png")
    with pytest.raises(ValueError, match="hu.png"):
        tl.build_pdf(_cfg_bitmap(config, blocchetti), str(tmp_path / "x.pdf"))


def test_il_pdf_con_cornice_bitmap_ha_inchiostro_sul_bordo_e_il_testo_si_scosta(config, blocchetti, tmp_path):
    cfg = _cfg_bitmap(config, blocchetti, bordo_stile="nessuno")
    (t, x, y, _s, _o) = tl.disponi(cfg)[0]
    ph_mm = cfg.pagina_pt()[1] / tl.mm
    pdf = tmp_path / "bitmap.pdf"
    r = tl.build_pdf(cfg, str(pdf))
    assert r["pagine"] >= 1
    assert _pixel_scuri(pdf, 0, x / tl.mm + 2, y / tl.mm + 2, ph_mm, raggio_mm=1.0) > 0
    assert tl.padding_utile(cfg, t) >= 4 * tl.mm       # spessore dei tratti (4 mm) + respiro


def test_con_il_taglio_attivo_i_tratti_arrivano_sempre_agli_angoli(config, blocchetti):
    assert tl.Config().decoro_bitmap_taglio is True
    for larg in (41.3, 47.9, 55.0):
        pezzi, _ = tl.pezzi_bitmap(_cfg_bitmap(config, blocchetti), 0, 0, larg * tl.mm, 28 * tl.mm)
        hu = [p for p in pezzi if p[0] == "hu"]
        a, b = min(p[5][0] for p in hu), max(p[5][0] + p[5][2] for p in hu)
        assert abs(a - 4 * tl.mm) < 1e-6 and abs(b - (larg - 4) * tl.mm) < 1e-6
        assert min(p[1] for p in hu) <= a + 1e-6 and max(p[1] + p[3] for p in hu) >= b - 1e-6   # nessun buco


def test_angoli_troppo_grandi_vengono_tagliati_a_meta_con_il_taglio_attivo(config, blocchetti):
    cfg = _cfg_bitmap(config, blocchetti, decoro_bitmap_riduci=False)
    pezzi, motivo = tl.pezzi_bitmap(cfg, 0, 0, 6 * tl.mm, 20 * tl.mm)          # 2 angoli da 4 mm in 6 mm
    assert motivo is None
    angoli = {p[0]: p for p in pezzi if p[0] in ("ul", "ur", "ll", "lr")}
    assert len(angoli) == 4
    for r, p in angoli.items():
        rx, ry, rw, rh = p[5]
        assert abs(rw - 3 * tl.mm) < 1e-6                    # 6 mm / 2
    assert angoli["ul"][5][0] == 0 and abs(angoli["ur"][5][0] + angoli["ur"][5][2] - 6 * tl.mm) < 1e-6
    assert any("tagliati" in f for f in tl.avvisi_bitmap(dataclasses.replace(
        cfg, tasselli=[dataclasses.replace(cfg.tasselli[0], larghezza_mm=6.0, altezza_mm=20.0)])))


def test_la_riduzione_rimpicciolisce_tutti_i_blocchetti_dello_stesso_fattore(config, blocchetti):
    cfg = _cfg_bitmap(config, blocchetti)                       # blocchetti 4 mm, riduci attivo
    assert tl.Config().decoro_bitmap_riduci is True
    pezzi, motivo = tl.pezzi_bitmap(cfg, 0, 0, 6 * tl.mm, 20 * tl.mm)   # due angoli = 8 mm in 6 mm
    assert motivo is None
    assert all(abs(p[3] - 3 * tl.mm) < 1e-6 and abs(p[4] - 3 * tl.mm) < 1e-6 for p in pezzi)   # 4 -> 3 mm
    angoli = [p for p in pezzi if p[0] in ("ul", "ur", "ll", "lr")]
    assert all(p[5] is None for p in angoli)                    # nessun taglio degli angoli
    assert any("rimpiccioliti al 75%" in f for f in tl.avvisi_bitmap(dataclasses.replace(
        cfg, tasselli=[dataclasses.replace(cfg.tasselli[0], larghezza_mm=6.0, altezza_mm=20.0)])))


def test_la_riduzione_non_ingrandisce_mai(config, blocchetti):
    cfg = _cfg_bitmap(config, blocchetti)
    assert tl.scala_bitmap(cfg, 100 * tl.mm, 60 * tl.mm) == 1.0
    pezzi, _ = tl.pezzi_bitmap(cfg, 0, 0, 100 * tl.mm, 60 * tl.mm)
    assert all(abs(p[3] - 4 * tl.mm) < 1e-6 for p in pezzi)


@pytest.fixture
def blocchetti16(blocchetti):
    from PIL import Image
    for r in tl.BITMAP_RUOLI_EXTRA:
        Image.new("RGBA", (40, 40), (0, 0, 0, 255)).save(blocchetti + r + ".png", dpi=(254, 254))
    return blocchetti


def test_a_16_blocchetti_il_pezzo_di_mezzo_sta_al_centro_e_i_tratti_riempiono_le_meta(config, blocchetti16):
    cfg = _cfg_bitmap(config, blocchetti16, decoro_bitmap_taglio=False)
    assert set(tl.carica_blocchetti(cfg)) == set(tl.BITMAP_RUOLI_TUTTI)
    # 44 mm: fra gli angoli 36 mm = centro (4) + due meta' da 16 mm = 4 tratti ciascuna
    pezzi, motivo = tl.pezzi_bitmap(cfg, 0, 0, 44 * tl.mm, 28 * tl.mm)
    assert motivo is None
    ruoli = [p[0] for p in pezzi]
    assert ruoli.count("hu") == 1 and ruoli.count("hu1") == 4 and ruoli.count("hu2") == 4
    assert ruoli.count("vl") == 1 and ruoli.count("vl1") == 2 and ruoli.count("vl2") == 2
    centro = [p for p in pezzi if p[0] == "hu"][0]
    assert abs(centro[1] - 20 * tl.mm) < 1e-6                       # (44 - 4) / 2
    # hu1 a destra del centro, hu2 a sinistra
    assert min(p[1] for p in pezzi if p[0] == "hu1") >= 24 * tl.mm - 1e-6
    assert max(p[1] for p in pezzi if p[0] == "hu2") < 20 * tl.mm
    # vl1 in alto (y maggiore), vl2 in basso
    assert min(p[2] for p in pezzi if p[0] == "vl1") > max(p[2] for p in pezzi if p[0] == "vl2")


def test_a_16_con_taglio_si_parte_dal_centro_e_si_taglia_verso_l_angolo(config, blocchetti16):
    cfg = _cfg_bitmap(config, blocchetti16, decoro_bitmap_taglio=True)
    pezzi, _ = tl.pezzi_bitmap(cfg, 0, 0, 45 * tl.mm, 28 * tl.mm)   # meta' da 16,5 mm
    hu1 = sorted((p for p in pezzi if p[0] == "hu1"), key=lambda p: p[1])
    assert len(hu1) == 5 and all(p[5] is not None for p in hu1)
    centro = [p for p in pezzi if p[0] == "hu"][0]
    assert abs(hu1[0][1] - (centro[1] + centro[3])) < 1e-6           # il primo e' attaccato al centro
    assert hu1[-1][1] + hu1[-1][3] > 45 * tl.mm - 4 * tl.mm          # l'ultimo sconfina sotto l'angolo


def test_a_16_il_centro_che_non_sta_viene_omesso(config, blocchetti16):
    cfg = _cfg_bitmap(config, blocchetti16, decoro_bitmap_taglio=False)
    pezzi, motivo = tl.pezzi_bitmap(cfg, 0, 0, 10 * tl.mm, 28 * tl.mm)   # fra gli angoli 2 mm
    assert motivo is None
    assert "hu" not in [p[0] for p in pezzi]
    assert any("omesso" in f for f in tl.avvisi_bitmap(dataclasses.replace(
        cfg, tasselli=[dataclasses.replace(cfg.tasselli[0], larghezza_mm=10, altezza_mm=28)])))


def test_i_tratti_1_e_2_vanno_insieme(config, blocchetti):
    from PIL import Image
    Image.new("RGBA", (40, 40), (0, 0, 0, 255)).save(blocchetti + "hu1.png", dpi=(254, 254))
    with pytest.raises(ValueError, match="hu2"):
        tl.carica_blocchetti(_cfg_bitmap(config, blocchetti))
