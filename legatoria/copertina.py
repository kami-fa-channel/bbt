"""Misure dei pezzi della copertina, a partire dal blocco libro finito.

Tutte le misure sono in millimetri.  Solo logica: niente input ne' print.

    opzioni()        costruisce i parametri, riempiendo i valori automatici
    calcola()        restituisce pezzi, fasce, cordonature e promemoria
    righe_testo()    la stessa cosa come testo, per il terminale o gli appunti
    esporta_sagoma() sagoma PDF 1:1 (richiede reportlab)
"""

from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Regole di base
# ---------------------------------------------------------------------------

def arrotonda(v):
    """Mezzo millimetro: sotto non ha senso con una riga e un cutter."""
    return round(v * 2) / 2


def fmt(v):
    return f"{arrotonda(v):g}"


def consiglio_legatura(D):
    if D <= 3:
        return "fascicolo unico, cucitura a sella"
    if D <= 10:
        return "brossura cucita"
    if D <= 25:
        return "brossura cucita, oppure cassa rigida se il libro deve durare"
    if D <= 40:
        return "cassa rigida"
    return "cassa rigida, con arrotondatura del dorso"


def default_cartone(D):
    return 2.0 if D < 10 else (2.5 if D < 25 else 3.0)


def default_unghia(D):
    return 2.5 if D < 10 else (3.0 if D < 25 else 3.5)


def default_gola(cartone, indorsato):
    g = 2 * cartone if indorsato else 1.5 * cartone
    return max(g, 6.0 if indorsato else 4.0)


def opzioni(altezza, larghezza, dorso, legatura="rigida", unghia=None, cartone=None,
            gola=None, indorsato=False, dorso_cavo=True, cerniera=7.0, rimbocco=15.0):
    """Costruisce l'oggetto delle opzioni, riempiendo i valori automatici."""
    cartone = default_cartone(dorso) if cartone is None else cartone
    unghia = default_unghia(dorso) if unghia is None else unghia
    gola = default_gola(cartone, indorsato) if gola is None else gola
    return SimpleNamespace(altezza=altezza, larghezza=larghezza, dorso=dorso,
                           legatura=legatura, unghia=unghia, cartone=cartone,
                           gola=gola, indorsato=indorsato, dorso_cavo=dorso_cavo,
                           cerniera=cerniera, rimbocco=rimbocco)


# ---------------------------------------------------------------------------
# Calcolo
# ---------------------------------------------------------------------------

def calcola(a):
    """Restituisce un dizionario con pezzi, fasce, cordonature e promemoria.

    pezzi: lista di (nome, altezza, larghezza, nota); larghezza None per i pezzi
    lineari come il capitello.
    """
    H, L, D, u = a.altezza, a.larghezza, a.dorso, a.unghia
    r = {"legatura": a.legatura, "consiglio": consiglio_legatura(D),
         "pezzi": [], "promemoria": ["Fibra parallela al dorso su TUTTI i pezzi."]}

    if a.legatura == "rigida":
        c, g = a.cartone, a.gola
        piatto_h = H + 2 * u
        piatto_l = L + u - g
        dorso_l = D + 2 * c + (2 if a.dorso_cavo else 0)
        disteso_l = 2 * piatto_l + 2 * g + dorso_l

        r["scelte"] = [
            f"Unghia {fmt(u)} · cartone {fmt(c)} · gola {fmt(g)} mm "
            f"({'con' if a.indorsato else 'senza'} indorsatura)",
            f"Dorso {'cavo' if a.dorso_cavo else 'incollato'} · rimbocco {fmt(a.rimbocco)} mm",
        ]
        r["pezzi"] = [
            ("Piatti (x2), cartone", piatto_h, piatto_l, f"cartone da {fmt(c)} mm"),
            ("Dorso, cartoncino", piatto_h, dorso_l, "cartoncino 0,3-0,5 mm"),
            ("Rivestimento", piatto_h + 2 * a.rimbocco, disteso_l + 2 * a.rimbocco,
             "tela o carta 120-160 g"),
        ]
        if a.dorso_cavo:
            r["pezzi"].append(("Striscia per il tubo", D, 3 * D, "carta kraft 100-120 g"))
        r["pezzi"].append(("Capitelli (x2)", D, None, "nastro, o cuciti a mano"))

        fasce, x = [], 0.0
        for nome, larg in (("rimbocco", a.rimbocco), ("piatto posteriore", piatto_l),
                           ("gola", g), ("DORSO", dorso_l), ("gola", g),
                           ("piatto anteriore", piatto_l), ("rimbocco", a.rimbocco)):
            fasce.append((nome, x, x + larg))
            x += larg
        r["fasce"] = fasce
        r["piatto"] = (piatto_h, piatto_l)
        r["dorso_cartoncino"] = dorso_l
        r["gola"] = g
        r["rivestimento"] = (piatto_h + 2 * a.rimbocco, disteso_l + 2 * a.rimbocco)
        r["promemoria"].append("Taglia il primo piatto e usalo come dima per il secondo.")
        if a.dorso_cavo:
            r["promemoria"].append("Precurva il cartoncino del dorso attorno a un tubo.")
        if D > 25 and not a.indorsato:
            r["promemoria"].append("Dorso spesso: arrotondalo col martello.")
    else:
        h = a.cerniera
        piatto_l = L + u
        cop_h = H + 2 * u
        cop_l = 2 * (piatto_l + h) + D
        r["scelte"] = [f"Unghia {fmt(u)} mm · cerniere francesi {fmt(h)} mm"]
        r["pezzi"] = [("Copertina, cartoncino", cop_h, cop_l, "cartoncino 250-300 g")]
        r["cordonature"] = [
            (piatto_l, "cerniera posteriore"),
            (piatto_l + h, "inizio dorso"),
            (piatto_l + h + D, "fine dorso"),
            (piatto_l + 2 * h + D, "cerniera anteriore"),
        ]
        r["copertina"] = (cop_h, cop_l)
        r["piatto"] = (cop_h, piatto_l)
        r["promemoria"] += [
            "Incidi le cordonature con la stecca, senza tagliare.",
            "La colla va solo sulla fascia del dorso, fra le due cordonature interne.",
        ]
        if D > 25:
            r["promemoria"].append(
                f"{fmt(D)} mm di dorso sono molti per una brossura: {consiglio_legatura(D)}.")
    return r


# ---------------------------------------------------------------------------
# Testo
# ---------------------------------------------------------------------------

def righe_testo(a, r):
    out = []
    out.append("=" * 70)
    out.append(f"BLOCCO: {fmt(a.altezza)} x {fmt(a.larghezza)} mm, dorso {fmt(a.dorso)} mm")
    out.append(f"Per questo spessore: {r['consiglio']}")
    out.append("=" * 70)
    out.append("")
    out.append("SCELTE")
    out += ["  " + s for s in r["scelte"]]
    out.append("")
    out.append("PEZZI DA TAGLIARE")
    for nome, h, l, nota in r["pezzi"]:
        if l is None:
            out.append(f"  {nome:<26} {fmt(h):>7} mm di nastro   {nota}")
        else:
            out.append(f"  {nome:<26} {fmt(h):>7} x {fmt(l):<7} mm   {nota}")
    if "fasce" in r:
        out.append("")
        out.append("FASCE DEL RIVESTIMENTO (dal bordo sinistro)")
        for nome, x0, x1 in r["fasce"]:
            out.append(f"  {fmt(x0):>7} - {fmt(x1):<7}  {nome}")
    if "cordonature" in r:
        out.append("")
        out.append("CORDONATURE (dal bordo sinistro, sul lato interno)")
        for x, nome in r["cordonature"]:
            out.append(f"  {fmt(x):>7} mm   {nome}")
    out.append("")
    out.append("PROMEMORIA")
    out += ["  " + p for p in r["promemoria"]]
    out.append("")
    out.append("Misura il blocco DOPO cucitura, collatura, rifilo e arrotondatura.")
    return out


def esporta_sagoma(a, r, percorso):
    """Scrive un PDF in scala 1:1 con i contorni dei pezzi (richiede reportlab).

    Per la cassa rigida la pagina ha le dimensioni del rivestimento e contiene i
    contorni dei piatti, delle gole e del dorso; per la brossura, le cordonature
    tratteggiate.  Solleva ImportError se manca reportlab.
    """
    from reportlab.pdfgen import canvas as rlcanvas
    MM = 72 / 25.4
    tot_h, tot_l = r["rivestimento"] if a.legatura == "rigida" else r["copertina"]
    cv = rlcanvas.Canvas(str(percorso), pagesize=(tot_l * MM, tot_h * MM))
    cv.setLineWidth(0.5)
    cv.rect(0, 0, tot_l * MM, tot_h * MM)
    if a.legatura == "rigida":
        piatto_h, piatto_l = r["piatto"]
        x = a.rimbocco
        for larg in (piatto_l, r["gola"], r["dorso_cartoncino"], r["gola"], piatto_l):
            cv.rect(x * MM, a.rimbocco * MM, larg * MM, piatto_h * MM)
            x += larg
    else:
        cv.setDash(4, 3)
        for x, _ in r["cordonature"]:
            cv.line(x * MM, 0, x * MM, tot_h * MM)
        cv.setDash()
    cv.setFont("Helvetica", 6)
    cv.drawString(4 * MM, 4 * MM, "Sagoma 1:1 - fibra parallela al dorso")
    cv.showPage()
    cv.save()
