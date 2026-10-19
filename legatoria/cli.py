"""Riga di comando.

    python -m legatoria                    apre la finestra
    python -m legatoria imposizione ...    impone un PDF in fascicoli
    python -m legatoria copertina ...      misure dei pezzi della copertina

Ogni sottocomando ha il suo -h.  Tutto quello che si fa da qui si fa anche dalla
finestra; la riga di comando serve per gli script e per le macchine senza
schermo.
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from . import copertina as cop
from . import imposizione as imp
from .errori import ErroreLegatoria


# ---------------------------------------------------------------------------
# Imposizione
# ---------------------------------------------------------------------------

def parser_imposizione(sub):
    ap = sub.add_parser(
        "imposizione",
        help="impone un PDF in fascicoli per la stampa fronte/retro",
        description="Impone un PDF in fascicoli pronti per la stampa fronte/retro "
                    "e la rilegatura a filo.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("-i", "--input", required=True, help="PDF originale")
    ap.add_argument("-f", "--fogli", type=int,
                    help="fogli fisici per fascicolo (1 foglio = 4 pagine); "
                         "se omesso usa il valore consigliato")
    ap.add_argument("-w", "--grammatura", type=int, default=80,
                    help="grammatura della carta in g/m2")
    ap.add_argument("-g", "--guardie", type=int, default=0,
                    help="fogli di guardia per lato, nella carta del testo")
    ap.add_argument("--filo", type=float, metavar="MM",
                    help="spessore del filo di cucitura per ogni fascicolo, in mm, per esempio "
                         "misurato con la prova della penna (larghezza delle spire divisa per "
                         "i giri); serve solo alla stima dello spessore del blocco, se omesso "
                         "si stima 0,3-0,5 mm")
    ap.add_argument("-p", "--posizione", action="append", metavar="N",
                    help="posizione in cui inserire una pagina bianca di correzione "
                         "(ripetibile, oppure elenco separato da virgole)")
    ap.add_argument("-t", "--tranche", type=int, default=50,
                    help="pagine indicative per ogni tranche di stampa")
    ap.add_argument("-o", "--output", help="file PDF di output")
    ap.add_argument("-n", "--analisi", action="store_true",
                    help="solo analisi, non genera nulla")

    g = ap.add_argument_group("impaginazione")
    g.add_argument("--carta", choices=sorted(imp.FORMATI), default="a4",
                   help="formato del foglio di stampa")
    g.add_argument("--margine-dorso", type=float, default=15.0, metavar="MM",
                   help="margine interno, lato piega")
    g.add_argument("--margine-esterno", type=float, default=10.0, metavar="MM",
                   help="margine esterno, lato taglio")
    g.add_argument("--margine-testa", type=float, default=10.0, metavar="MM")
    g.add_argument("--margine-piede", type=float, default=10.0, metavar="MM")
    g.add_argument("--scala", type=float, default=1.0, metavar="K",
                   help="ingrandimento aggiuntivo dopo l'adattamento ai margini "
                        "(1.05 sborda leggermente e mangia i margini bianchi dell'originale)")
    g.add_argument("--shingling", type=float, default=0.0, metavar="MM",
                   help="compensazione dello scorrimento, in mm per foglio: ogni foglio "
                        "piu' interno viene spostato di questo valore verso il dorso. "
                        "Usa 'auto' con -w oppure misura il gradino e dividi per (fogli-1)")
    g.add_argument("--shingling-auto", action="store_true",
                   help="calcola lo shingling dalla grammatura (-w)")
    g.add_argument("--segni", action="store_true",
                   help="stampa i segni di piega e il numero del fascicolo nel margine")
    return ap


def esegui_imposizione(ns):
    imp.valida_filo(ns.filo)
    reader = imp.apri_pdf(ns.input)
    pagine_orig = len(reader.pages)
    posizioni, _ = imp.leggi_posizioni(ns.posizione, pagine_orig)
    pagine_base = pagine_orig + len(posizioni) + 4 * ns.guardie

    tab = imp.tabella_fascicolature(ns.grammatura, pagine_base)
    consigliati = tab["consigliati"]
    righe = ["", "=== ANALISI DELLA FASCICOLATURA " + "=" * 47,
             f"File:                   {ns.input}",
             f"Pagine originali:       {pagine_orig}"]
    if posizioni:
        righe.append(f"Pagine bianche interne: {len(posizioni)} "
                     f"(posizioni: {', '.join(map(str, posizioni))})")
    if ns.guardie:
        righe.append(f"Fogli di guardia:       {ns.guardie} per lato "
                     f"-> {ns.guardie * 2} facciate davanti e {ns.guardie * 2} dietro")
    righe += [f"Pagine da impaginare:   {pagine_base} (prima del riempimento finale)",
              f"Carta dichiarata:       {ns.grammatura} g/m2 -> spessore stimato "
              f"{tab['spessore_foglio']:.3f} mm/foglio",
              ""]
    righe += imp.righe_tabella(tab)
    print("\n".join(righe))

    if ns.fogli is None:
        ns.fogli = consigliati
        print(f"\n>> Nessun -f indicato: uso il valore consigliato di {ns.fogli} fogli per fascicolo.")
    elif ns.fogli < 1:
        raise ErroreLegatoria("-f deve essere almeno 1.")
    elif ns.fogli != consigliati:
        print(f"\n>> Richiesti {ns.fogli} fogli per fascicolo "
              f"(per {ns.grammatura} g/m2 il consiglio sarebbe {consigliati}). Procedo comunque.")

    if ns.shingling_auto:
        ns.shingling = imp.spessore_foglio_mm(ns.grammatura)

    p = imp.piano(pagine_orig, posizioni, ns.guardie, ns.fogli, ns.grammatura, ns.filo)
    righe = ["", "=== PIANO DI LAVORO " + "=" * 59,
             f"Fogli per fascicolo:          {ns.fogli}  ({p.signature} pagine logiche)",
             f"Pagine di riempimento finale: {p.riempimento}",
             f"Pagine totali del blocco:     {p.pagine_blocco}",
             f"Fascicoli: {p.n_fascicoli}    Fogli da stampare: {p.fogli_da_stampare} (fronte/retro)",
             f"Pagine del PDF finale:        {p.pagine_pdf}"]
    if ns.shingling:
        massimo = (ns.fogli - 1) * ns.shingling
        righe.append(f"Shingling: {ns.shingling:.3f} mm per foglio "
                     f"(spostamento massimo {massimo:.2f} mm sul foglio piu' interno)")
    if p.filo_indicato:
        filo = f"piu' {p.filo_mm[0]:.1f} mm di filo ({ns.filo:g} mm per fascicolo, indicati da te)"
    else:
        filo = f"piu' {p.filo_mm[0]:.1f}-{p.filo_mm[1]:.1f} mm di filo"
    righe.append(f"Spessore del blocco (stima):  {p.spessore_carta_mm:.1f} mm di carta, {filo}")
    if imp.avviso_filo(ns.filo):
        righe.append(imp.avviso_filo(ns.filo))
    righe.append("=" * 79)
    print("\n".join(righe))

    tr = imp.tranche(ns.tranche, ns.fogli, p.n_fascicoli)
    if ns.analisi:
        print("\n".join(imp.righe_tranche(tr, ns.fogli)))
        print("\n(Modalita' -n: nessun file generato.)")
        return

    percorso = Path(ns.input)
    uscita = Path(ns.output) if ns.output else percorso.with_name(percorso.stem + "_booklet.pdf")
    print("\nImposizione in corso...")
    n_fasc, n_pagine = imp.impagina(reader, p.blocco, ns, ns.fogli, uscita)
    print(f"Fatto: {uscita} ({n_pagine} pagine orizzontali, {n_fasc} fascicoli).")
    print("\n".join(imp.righe_tranche(tr, ns.fogli)))


# ---------------------------------------------------------------------------
# Copertina
# ---------------------------------------------------------------------------

def chiedi(testo, default=None):
    suffisso = f" [{default}]" if default is not None else ""
    while True:
        risposta = input(f"{testo}{suffisso}: ").strip().replace(",", ".")
        if not risposta and default is not None:
            return default
        try:
            return float(risposta)
        except ValueError:
            print("  valore non valido")


def chiedi_si_no(testo, default):
    risposta = input(f"{testo} [{'S/n' if default else 's/N'}]: ").strip().lower()
    return default if not risposta else risposta.startswith("s")


def interattivo():
    print("Misure del blocco libro FINITO (cucito, collato, rifilato, arrotondato).")
    print("Tutte in millimetri.\n")
    H = chiedi("Altezza del blocco")
    L = chiedi("Larghezza del blocco, dopo il rifilo")
    D = chiedi("Spessore del dorso (sulla curva, con una strisciolina di carta)")
    print(f"\n  Per {cop.fmt(D)} mm di dorso: {cop.consiglio_legatura(D)}.\n")
    if chiedi_si_no("Copertina rigida?", D > 10):
        c = chiedi("Spessore del cartone dei piatti", cop.default_cartone(D))
        u = chiedi("Unghia", cop.default_unghia(D))
        ind = chiedi_si_no("Hai formato le cerniere col martello (indorsatura)?", False)
        cavo = chiedi_si_no("Dorso cavo (tubo di carta)?", True)
        print()
        return cop.opzioni(H, L, D, "rigida", unghia=u, cartone=c, indorsato=ind, dorso_cavo=cavo)
    u = chiedi("Unghia", 2.5)
    h = chiedi("Larghezza delle cerniere francesi", 7.0)
    print()
    return cop.opzioni(H, L, D, "brossura", unghia=u, cerniera=h)


def parser_copertina(sub):
    ap = sub.add_parser(
        "copertina",
        help="misure dei pezzi della copertina dal blocco finito",
        description="Calcola le dimensioni della copertina dal blocco libro finito. "
                    "Senza argomenti parte in modalita' interattiva.")
    ap.add_argument("-H", "--altezza", type=float)
    ap.add_argument("-L", "--larghezza", type=float)
    ap.add_argument("-D", "--dorso", type=float)
    ap.add_argument("--legatura", choices=("rigida", "brossura"), default="rigida")
    ap.add_argument("-u", "--unghia", type=float)
    ap.add_argument("-c", "--cartone", type=float)
    ap.add_argument("-g", "--gola", type=float)
    ap.add_argument("--indorsato", action="store_true")
    ap.add_argument("--dorso-incollato", dest="dorso_cavo", action="store_false")
    ap.add_argument("--cerniera", type=float, default=7.0)
    ap.add_argument("--rimbocco", type=float, default=15.0)
    ap.set_defaults(dorso_cavo=True)
    return ap


def esegui_copertina(ns, ap, senza_argomenti):
    if ns.altezza is None or ns.larghezza is None or ns.dorso is None:
        if not senza_argomenti:
            ap.error("servono -H, -L e -D (oppure lancia il sottocomando senza argomenti)")
        a = interattivo()
    else:
        for nome, v in (("altezza", ns.altezza), ("larghezza", ns.larghezza), ("dorso", ns.dorso)):
            if v <= 0:
                raise ErroreLegatoria(f"{nome} deve essere maggiore di zero.")
        a = cop.opzioni(ns.altezza, ns.larghezza, ns.dorso, ns.legatura, ns.unghia, ns.cartone,
                        ns.gola, ns.indorsato, ns.dorso_cavo, ns.cerniera, ns.rimbocco)
    print("\n".join(cop.righe_testo(a, cop.calcola(a))))


# ---------------------------------------------------------------------------
# Ingresso
# ---------------------------------------------------------------------------

def avvia_gui():
    try:
        from .gui.app import main as main_gui
    except ImportError as e:
        sys.exit(f"Errore: non riesco ad aprire la finestra ({e}).\n"
                 "Serve tkinter, che non si installa con pip: su Debian/Ubuntu "
                 "sudo apt install python3-tk, su Arch/Manjaro sudo pacman -S tk, "
                 "su Fedora sudo dnf install python3-tkinter.")
    main_gui()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    ap = argparse.ArgumentParser(
        prog="legatoria",
        description="Dal PDF al libro cucito. Senza argomenti apre la finestra.")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="comando", metavar="comando")
    sub.add_parser("gui", help="apre la finestra (e' quello che succede senza argomenti)")
    parser_imposizione(sub)
    ap_copertina = parser_copertina(sub)

    if not argv:
        return avvia_gui()
    ns = ap.parse_args(argv)
    try:
        if ns.comando == "imposizione":
            esegui_imposizione(ns)
        elif ns.comando == "copertina":
            esegui_copertina(ns, ap_copertina, senza_argomenti=len(argv) == 1)
        else:
            avvia_gui()
    except ErroreLegatoria as e:
        sys.exit(f"Errore: {e}")
