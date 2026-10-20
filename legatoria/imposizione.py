"""Imposizione tipografica per rilegatura a filo (fascicoli/segnature).

Questo modulo contiene solo la logica: non stampa niente e non chiede niente.
Le funzioni restituiscono dati (elenchi, dizionari, oggetti semplici) che la
finestra e la riga di comando poi presentano ciascuna a modo suo.

Non richiede pdftk, pdfjam, TeX Live o Ghostscript: serve solo pypdf.

Funzioni principali:
    tabella_fascicolature  confronto fra 1 e 8 fogli per fascicolo
    piano                  numeri del lavoro (fascicoli, riempimento, spessore)
    tranche                intervalli di stampa che non spezzano un fascicolo
    impagina               impone il PDF e lo scrive
"""

import math
import re
import warnings
from pathlib import Path
from types import SimpleNamespace

from pypdf import PdfReader, PdfWriter, PageObject, Transformation
from pypdf.generic import DecodedStreamObject, DictionaryObject, IndirectObject, NameObject

from .errori import ErroreLegatoria

MM = 72.0 / 25.4          # millimetri -> punti PostScript
FORMATI = {               # formato del foglio di stampa, in millimetri (larghezza, altezza)
    "a4": (210.0, 297.0),
    "a3": (297.0, 420.0),
    "letter": (215.9, 279.4),
    "legal": (215.9, 355.6),
}


# ---------------------------------------------------------------------------
# Analisi della fascicolatura
# ---------------------------------------------------------------------------

def spessore_foglio_mm(grammatura):
    """Carta non patinata: densita' ~0,8 g/cm3, quindi spessore ~ grammatura/800."""
    return grammatura / 800.0


def consiglio_fogli(grammatura):
    """Massimo numero di fogli per fascicolo che rispetta i due vincoli fisici."""
    t = spessore_foglio_mm(grammatura)
    f_creep = int(0.45 / t) + 1          # scorrimento (F-1)*t <= 0,45 mm
    f_dorso = int(1.10 / (2 * t))        # dorso del fascicolo 2*F*t <= 1,10 mm
    return max(2, min(6, f_creep, f_dorso))


def sprechi(pagine_base, fogli):
    s = fogli * 4
    return math.ceil(pagine_base / s) * s - pagine_base


def tabella_fascicolature(grammatura, pagine_base):
    """Confronta da 1 a 8 fogli per fascicolo per una data grammatura.

    Restituisce un dizionario:
        spessore_foglio   spessore stimato di un foglio, mm
        consigliati       fogli per fascicolo consigliati per questa carta
        alternativa       fogli che sprecano meno carta (= consigliati se non c'e')
        spreco_consigliati, spreco_alternativa   pagine bianche di riempimento
        righe             una per numero di fogli, con: fogli, pagine, fascicoli,
                          bianche, scorrimento, dorso, giudizio
    """
    t = spessore_foglio_mm(grammatura)
    consigliati = consiglio_fogli(grammatura)
    alt = consigliati
    if consigliati > 2:
        cand = consigliati - 1
        if sprechi(pagine_base, consigliati) - sprechi(pagine_base, cand) >= 4:
            alt = cand
    righe = []
    for fogli in range(1, 9):
        s = fogli * 4
        n = math.ceil(pagine_base / s)
        creep = (fogli - 1) * t
        dorso = 2 * fogli * t
        if creep > 0.9 or dorso > 1.6:
            giudizio = "sconsigliato"
        elif creep > 0.45 or dorso > 1.10:
            giudizio = "limite"
        elif fogli == 1:
            giudizio = "ok (molte cuciture)"
        else:
            giudizio = "ok"
        righe.append({"fogli": fogli, "pagine": s, "fascicoli": n,
                      "bianche": n * s - pagine_base, "scorrimento": creep,
                      "dorso": dorso, "giudizio": giudizio})
    return {"spessore_foglio": t, "consigliati": consigliati, "alternativa": alt,
            "spreco_consigliati": sprechi(pagine_base, consigliati),
            "spreco_alternativa": sprechi(pagine_base, alt), "righe": righe}


def righe_tabella(tab, come_fogli="-f {}"):
    """La tabella di tabella_fascicolature() come righe di testo a larghezza fissa.

    come_fogli e' il modo di nominare i fogli nella frase sull'alternativa:
    "-f {}" per la riga di comando, "{} fogli per fascicolo" per la finestra.
    """
    r = [f"{'Fogli':<7}{'Pagine':<8}{'Fascicoli':<11}{'Bianche':<9}"
         f"{'Scorrim.':<10}{'Dorso fasc.':<13}{'Giudizio'}",
         f"{'/fasc':<7}{'/fasc':<8}{'totali':<11}{'riempim.':<9}"
         f"{'(mm)':<10}{'(mm)':<13}",
         "-" * 79]
    for x in tab["righe"]:
        nota = x["giudizio"]
        if x["fogli"] == tab["consigliati"]:
            nota += "  <== CONSIGLIATO"
        elif x["fogli"] == tab["alternativa"]:
            nota += "  <== meno carta sprecata"
        r.append(f"{x['fogli']:<7}{x['pagine']:<8}{x['fascicoli']:<11}{x['bianche']:<9}"
                 f"{x['scorrimento']:<10.2f}{x['dorso']:<13.2f}{nota}")
    r += ["-" * 79,
          "Scorrimento = quanto sporge il taglio davanti della pagina piu' interna del",
          "fascicolo: va rifilato dopo la piegatura, quindi conviene tenerlo basso.",
          "Dorso fasc. = spessore del fascicolo sulla piega: oltre ~1,1 mm forare dritto",
          "con l'ago e ottenere una piega netta diventa difficile."]
    if tab["alternativa"] != tab["consigliati"]:
        r += ["",
              f"Alternativa: con {come_fogli.format(tab['alternativa'])} sprecheresti "
              f"{tab['spreco_alternativa']} pagine bianche",
              f"invece di {tab['spreco_consigliati']}, a costo di qualche cucitura in piu'."]
    r.append("=" * 79)
    return r


# ---------------------------------------------------------------------------
# Costruzione del blocco libro
# ---------------------------------------------------------------------------

def costruisci_blocco(pagine_orig, posizioni, guardie, signature):
    """Restituisce la lista delle pagine del blocco.

    Ogni elemento e' l'indice (0-based) della pagina originale, oppure None
    per una pagina bianca.  Ordine:
        [guardie] [corpo con le bianche di correzione] [riempimento] [guardie]
    """
    corpo = []
    inserimenti = sorted(posizioni)
    prossima = 0
    for p in inserimenti:
        while prossima < p - 1:
            corpo.append(prossima)
            prossima += 1
        corpo.append(None)
    corpo.extend(range(prossima, pagine_orig))

    guardia = [None] * (guardie * 2)
    base = len(guardia) * 2 + len(corpo)
    riempimento = [None] * ((-base) % signature)
    return guardia + corpo + riempimento + guardia


def ordine_fascicolo(signature):
    """Ordine di imposizione di un fascicolo di `signature` pagine.

    Restituisce una lista di facciate; ogni facciata e' la coppia
    (pagina a sinistra, pagina a destra), numerate da 1 a signature.
    Le facciate si alternano fronte/retro, foglio dopo foglio.
    """
    facciate = []
    for i in range(signature // 4):
        facciate.append((signature - 2 * i, 1 + 2 * i))      # fronte del foglio i
        facciate.append((2 + 2 * i, signature - 1 - 2 * i))  # retro del foglio i
    return facciate


# Quanto ingrossa il dorso il filo di cucitura, per ogni fascicolo, in mm:
# (minimo, massimo).  Sta qui, in un posto solo, perche' la usano sia il riepilogo
# dell'imposizione sia la stima delle misure per la copertina.
#
# Da dove viene.  In prima approssimazione il rigonfiamento e' lo spessore del
# filo per il numero di fascicoli: i rilegatori lo visualizzano avvolgendo il filo
# attorno a una matita tante volte quanti sono i fascicoli.  I lini di uso comune
# misurano, secondo i cataloghi dei fornitori: 25/3 circa 0,50 mm, 30/3 circa
# 0,42-0,45 mm, 35/3 circa 0,38-0,40 mm.  Il massimo e' il 25/3, il filo piu'
# usato; il minimo e' un filo fine che la battitura schiaccia; il valore di mezzo
# (0,4) e' un 30/3-35/3, cioe' il filo che il manuale consiglia per i libri grossi,
# dove la stima conta di piu'.  Con un 18/3 (0,55-0,60 mm) o con filo molto cerato
# si sale sopra il massimo.
#
# Non esiste una formula esatta: dipende anche da carta, fogli per fascicolo, tipo
# di cucitura e tensione.  E' una stima per ordinare i materiali, non una misura.
# Fonti e ragionamento completo: docs/manuale.md, capitolo 13.  Se cambi questi
# numeri aggiorna anche il manuale: un test controlla che dicano la stessa cosa.
FILO_MM_PER_FASCICOLO = (0.3, 0.5)

# Il filo piu' grosso in commercio (un 12/3) misura circa 1 mm.  Oltre questa
# soglia, per UN fascicolo, quasi certamente si e' indicato lo spessore di tutto
# il filo del libro (per esempio l'intera fascia della prova della penna) senza
# dividerlo per i giri.
FILO_MM_MASSIMO_PLAUSIBILE = 1.5


def valida_filo(filo_mm):
    """Controlla il filo per fascicolo indicato dall'utente (None = non indicato)."""
    if filo_mm is not None and not filo_mm > 0:
        raise ErroreLegatoria("il filo per fascicolo deve essere maggiore di zero.")


def avviso_filo(filo_mm):
    """Un avviso se il filo per fascicolo indicato sembra sbagliato, altrimenti None."""
    if filo_mm is not None and filo_mm > FILO_MM_MASSIMO_PLAUSIBILE:
        return (f"Attenzione: {filo_mm:g} mm di filo per fascicolo sono piu' del filo piu' "
                "grosso in commercio (circa 1 mm). Il valore e' per UN fascicolo: nella prova "
                "della penna dividi la misura per il numero di giri.")
    return None


def piano(pagine_orig, posizioni, guardie, fogli, grammatura, filo_mm=None):
    """I numeri del lavoro, dato il PDF e i parametri di fascicolatura.

    filo_mm e' lo spessore del filo per ogni fascicolo, se lo si e' misurato (per
    esempio con la prova della penna: larghezza delle spire divisa per i giri).
    Se e' None si usa l'intervallo generico FILO_MM_PER_FASCICOLO.

    Restituisce un oggetto con: blocco (vedi costruisci_blocco), signature,
    fogli, n_fascicoli, riempimento (pagine bianche finali), pagine_blocco,
    fogli_da_stampare (fogli fisici, fronte/retro), pagine_pdf (facciate del
    file finale), spessore_carta_mm,
    filo_mm (minimo, massimo), dorso_mm (minimo, massimo: carta piu' filo),
    filo_indicato (True se il filo e' quello passato dall'utente) e
    filo_per_fascicolo (minimo, massimo).  Con il filo indicato minimo e massimo
    coincidono.
    """
    valida_filo(filo_mm)
    signature = fogli * 4
    blocco = costruisci_blocco(pagine_orig, posizioni, guardie, signature)
    n_fascicoli = len(blocco) // signature
    carta = (len(blocco) / 2) * spessore_foglio_mm(grammatura)
    per_fascicolo = FILO_MM_PER_FASCICOLO if filo_mm is None else (filo_mm, filo_mm)
    filo = (n_fascicoli * per_fascicolo[0], n_fascicoli * per_fascicolo[1])
    return SimpleNamespace(
        blocco=blocco, signature=signature, fogli=fogli, n_fascicoli=n_fascicoli,
        riempimento=blocco.count(None) - 4 * guardie - len(posizioni),
        pagine_blocco=len(blocco), fogli_da_stampare=n_fascicoli * fogli,
        pagine_pdf=n_fascicoli * fogli * 2,
        spessore_carta_mm=carta, filo_mm=filo,
        dorso_mm=(carta + filo[0], carta + filo[1]),
        filo_indicato=filo_mm is not None, filo_per_fascicolo=per_fascicolo)


def misure_blocco_stimate(p, carta="a4", rifilo_mm=3.0):
    """Altezza, larghezza e dorso del blocco finito, stimati dal piano di lavoro.

    p e' il risultato di piano().  L'altezza e' il lato corto del foglio di
    stampa, la larghezza e' meta' del lato lungo meno il rifilo previsto.  Il
    dorso e' il valore di mezzo fra dorso_mm[0] e dorso_mm[1], cioe' carta piu'
    filo secondo FILO_MM_PER_FASCICOLO; il campo possibile resta in dorso_min e
    dorso_max.  Sono stime per ordinare i materiali: le misure vere si prendono
    sul blocco cucito.
    """
    larghezza_mm, altezza_mm = FORMATI.get(carta, (210.0, 297.0))
    minimo, massimo = p.dorso_mm
    return SimpleNamespace(altezza=larghezza_mm, larghezza=altezza_mm / 2 - rifilo_mm,
                           dorso=(minimo + massimo) / 2, dorso_min=minimo, dorso_max=massimo)


def leggi_posizioni(valori, pagine_orig, rigido=True):
    """Legge le posizioni delle bianche di correzione.

    valori e' una lista di stringhe, ciascuna con uno o piu' numeri separati da
    virgole o spazi.  Restituisce (posizioni, fuori_intervallo).

    rigido=True (riga di comando): la prima posizione illeggibile o fuori
    dall'intervallo 1..pagine_orig+1 solleva ErroreLegatoria.
    rigido=False (finestra, mentre l'utente digita): le posizioni illeggibili
    si ignorano e quelle fuori intervallo si raccolgono in fuori_intervallo.
    """
    posizioni, fuori = [], []
    for v in valori or []:
        for pezzo in str(v).replace(",", " ").split():
            try:
                p = int(pezzo)
            except ValueError:
                if rigido:
                    raise ErroreLegatoria(f"posizione -p '{pezzo}' non valida.")
                continue
            if not 1 <= p <= pagine_orig + 1:
                if rigido:
                    raise ErroreLegatoria(
                        f"la posizione -p {p} e' fuori dall'intervallo 1-{pagine_orig + 1}.")
                fuori.append(p)
                continue
            posizioni.append(p)
    return posizioni, fuori


# ---------------------------------------------------------------------------
# Imposizione
# ---------------------------------------------------------------------------

def riquadro_sorgente(pagina):
    """Dimensioni utili della pagina sorgente, in punti, rotazione gia' applicata."""
    box = pagina.cropbox if pagina.cropbox else pagina.mediabox
    return float(box.width), float(box.height), float(box.left), float(box.bottom)


def piazza(destinazione, sorgente, cella_x, cella_y, cella_w, cella_h, scala_extra):
    """Scala la pagina sorgente dentro la cella e la fonde nella destinazione."""
    w, h, x0, y0 = riquadro_sorgente(sorgente)
    if w <= 0 or h <= 0:
        return
    s = min(cella_w / w, cella_h / h) * scala_extra
    tx = cella_x + (cella_w - w * s) / 2.0
    ty = cella_y + (cella_h - h * s) / 2.0
    ctm = (Transformation()
           .translate(-x0, -y0)
           .scale(s, s)
           .translate(tx, ty))
    destinazione.merge_transformed_page(sorgente, ctm, over=True)


def stream_segni(larghezza, altezza, etichetta, y_marca):
    """Content stream con i segni di piega, la marca di collazione e l'etichetta.

    Tutto viene disegnato sulla linea di piega o a ridosso di essa, cioe' in
    quella che dopo la piegatura e' la costola del fascicolo: a libro cucito
    non si vede.
    """
    x = larghezza / 2.0
    tacca = 6 * MM
    ops = [
        b"q 0.4 w 0.55 G [2 2] 0 d",
        f"{x:.2f} {altezza - tacca:.2f} m {x:.2f} {altezza:.2f} l S".encode(),
        f"{x:.2f} 0 m {x:.2f} {tacca:.2f} l S".encode(),
        b"Q",
    ]
    if y_marca is not None:
        ops.append(
            f"q 0.15 g {x - 3 * MM:.2f} {y_marca:.2f} {6 * MM:.2f} {3 * MM:.2f} re f Q".encode()
        )
    if etichetta:
        ops += [
            b"q BT /FSegni 6 Tf 0.5 g",
            f"{x + 3 * MM:.2f} {altezza - 12 * MM:.2f} Td ({etichetta}) Tj".encode(),
            b"ET Q",
        ]
    return b"\n".join(ops)


def aggiungi_segni(writer, pagina, larghezza, altezza, etichetta, y_marca):
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    risorse = pagina[NameObject("/Resources")]
    if NameObject("/Font") not in risorse:
        risorse[NameObject("/Font")] = DictionaryObject()
    risorse[NameObject("/Font")][NameObject("/FSegni")] = writer._add_object(font)

    stream = DecodedStreamObject()
    stream.set_data(stream_segni(larghezza, altezza, etichetta, y_marca))
    pagina.replace_contents(stream)


def imponi(reader, writer, blocco, args, signature, fogli):
    larghezza_mm, altezza_mm = FORMATI[args.carta]
    # foglio di stampa in orizzontale: il lato lungo diventa la larghezza
    W, H = altezza_mm * MM, larghezza_mm * MM
    meta = W / 2.0

    m_dorso = args.margine_dorso * MM
    m_est = args.margine_esterno * MM
    m_testa = args.margine_testa * MM
    m_piede = args.margine_piede * MM

    cella_w = meta - m_dorso - m_est
    cella_h = H - m_testa - m_piede
    if cella_w <= 0 or cella_h <= 0:
        raise ErroreLegatoria("i margini richiesti non lasciano spazio alla pagina.")

    passo = args.shingling * MM
    facciate = ordine_fascicolo(signature)
    n_fascicoli = len(blocco) // signature

    # Scaletta delle marche di collazione: ogni fascicolo porta la sua marca un
    # gradino piu' in basso, cosi' impilando i fascicoli si vede subito se ne
    # manca uno o se sono fuori ordine.
    utile = H - 24 * MM
    gradino = min(6 * MM, utile / max(1, n_fascicoli))
    # + 1e-9: utile / gradino puo' venire n - epsilon in virgola mobile (succede,
    # per esempio, con 52 fascicoli) e int() lo troncherebbe a n - 1, facendo
    # ricominciare dall'alto la scaletta proprio sull'ultimo fascicolo.
    per_scaletta = max(1, int(utile / gradino + 1e-9))

    for f_idx in range(n_fascicoli):
        base = f_idx * signature
        for n_facciata, (sinistra, destra) in enumerate(facciate):
            foglio = n_facciata // 2                    # 0 = foglio piu' esterno
            spinta = foglio * passo                     # verso il dorso
            pagina = PageObject.create_blank_page(width=W, height=H)
            writer.add_page(pagina)
            pagina = writer.pages[-1]

            if args.segni:
                fronte = n_facciata % 2 == 0
                etichetta = f"F{f_idx + 1}.{foglio + 1}" if fronte else ""
                y_marca = None
                if fronte and foglio == 0:
                    y_marca = H - 12 * MM - (f_idx % per_scaletta) * gradino
                aggiungi_segni(writer, pagina, W, H, etichetta, y_marca)

            for lato, numero in (("sx", sinistra), ("dx", destra)):
                indice = blocco[base + numero - 1]
                if indice is None:
                    continue
                sorgente = reader.pages[indice]
                if sorgente.rotation:
                    sorgente.transfer_rotation_to_content()
                if lato == "sx":
                    x = m_est + spinta            # il dorso e' a destra della cella
                else:
                    x = meta + m_dorso - spinta   # il dorso e' a sinistra della cella
                piazza(pagina, sorgente, x, m_piede, cella_w, cella_h, args.scala)

    return n_fascicoli, len(writer.pages)


# ---------------------------------------------------------------------------
# Tabella delle tranche di stampa
# ---------------------------------------------------------------------------

def tranche(target, fogli, n_fascicoli):
    """Intervalli di stampa che non spezzano mai un fascicolo a meta'.

    Restituisce un dizionario: target, per_blocco (fascicoli per tranche),
    pagine_per_tranche, totale (pagine del PDF finale) ed elenco, una voce per
    tranche con n, inizio, fine, f1, f2 (primo e ultimo fascicolo).
    """
    facciate = fogli * 2
    per_blocco = max(1, target // facciate)
    dim = per_blocco * facciate
    totale = n_fascicoli * facciate
    elenco = []
    k = 1
    while (k - 1) * dim < totale:
        inizio = (k - 1) * dim + 1
        fine = min(k * dim, totale)
        elenco.append({"n": k, "inizio": inizio, "fine": fine,
                       "f1": (inizio - 1) // facciate + 1,
                       "f2": (fine - 1) // facciate + 1})
        k += 1
    return {"target": target, "per_blocco": per_blocco, "pagine_per_tranche": dim,
            "totale": totale, "elenco": elenco}


def righe_tranche(tr, fogli):
    """La tabella di tranche() come righe di testo, per la riga di comando."""
    r = ["",
         "=== TABELLA INTERVALLI DI STAMPA " + "=" * 46,
         f"Target richiesto: massimo {tr['target']} pagine per tranche.",
         f"Ogni tranche contiene {tr['per_blocco']} fascicolo/i interi = "
         f"{tr['per_blocco'] * fogli} fogli fisici = {tr['pagine_per_tranche']} pagine del PDF.",
         "Impostazione stampante: FRONTE/RETRO -> CAPOVOLGI SUL LATO CORTO.",
         "-" * 79]
    for x in tr["elenco"]:
        intervallo = f"{x['inizio']}-{x['fine']}"
        r.append(f"Tranche {x['n']:<3} intervallo di stampa {intervallo:<13} "
                 f"(fascicoli F{x['f1']}-F{x['f2']})")
    r.append("=" * 79)
    return r


# ---------------------------------------------------------------------------
# File
# ---------------------------------------------------------------------------

def apri_pdf(percorso):
    """Apre un PDF; solleva ErroreLegatoria se manca o e' protetto da password."""
    if not Path(percorso).is_file():
        raise ErroreLegatoria(f"il file '{percorso}' non esiste.")
    reader = PdfReader(str(percorso))
    if reader.is_encrypted:
        try:
            aperto = reader.decrypt("")
        except Exception:
            aperto = 0
        if not aperto:
            raise ErroreLegatoria("il PDF e' protetto da password.")
    return reader


_RE_DO = re.compile(rb"(/[^\s/<>\[\]()]+)\s+Do\b")


def _byte_contenuto(pagina):
    """Contenuto della pagina come byte, senza analizzarlo."""
    def appiattisci(oggetto):
        oggetto = oggetto.get_object()
        if isinstance(oggetto, list):
            return b"\n".join(appiattisci(x) for x in oggetto)
        return oggetto.get_data()

    flussi = pagina.get("/Contents")
    return b"" if flussi is None else appiattisci(flussi)


def separa_immagini_ripetute(writer):
    """Dà una copia propria a ogni immagine che una pagina disegna piu' volte.

    Quando una pagina disegna due volte lo stesso oggetto immagine, con lo stesso
    nome o con nomi diversi, Cairo (cioe' Evince, quando stampa) scrive nel PDF
    che manda alla stampante un dizionario delle risorse con la stessa chiave
    ripetuta, ad esempio ``/XObject << /x65 65 0 R /x65 65 0 R >>``.  Poppler lo
    perdona, ma l'interprete PDF di certe stampanti (visto su un Lexmark MS415dn)
    non legge le risorse e stampa la pagina vuota.  Con oggetti distinti il PDF di
    Cairo e' valido.  Va chiamata dopo compress_identical_objects, che altrimenti
    riunirebbe le copie.  Restituisce quante copie ha creato.
    """
    create = 0
    for pagina in writer.pages:
        risorse = pagina.get("/Resources")
        xobj = risorse.get("/XObject") if risorse else None
        if not xobj:
            continue
        # prima un conteggio rapido sui byte: l'analisi completa del contenuto
        # costa piu' di tutto il resto del salvataggio
        usi = {}
        for nome in _RE_DO.findall(_byte_contenuto(pagina)):
            nome = NameObject(nome.decode("latin-1"))
            if nome in xobj:
                oggetto = xobj.raw_get(nome)
                chiave = oggetto.idnum if isinstance(oggetto, IndirectObject) else id(oggetto)
                usi[chiave] = usi.get(chiave, 0) + 1
        if all(k < 2 for k in usi.values()):
            continue
        contenuto = pagina.get_contents()
        # le risorse possono essere condivise con altre pagine: si lavora su copie
        xobj = DictionaryObject(xobj)
        risorse = DictionaryObject(risorse)
        risorse[NameObject("/XObject")] = xobj
        pagina[NameObject("/Resources")] = risorse
        viste = set()
        cambiato = False
        for operandi, operatore in contenuto.operations:
            if operatore != b"Do" or not operandi or operandi[0] not in xobj:
                continue
            nome = operandi[0]
            oggetto = xobj.raw_get(nome)
            chiave = oggetto.idnum if isinstance(oggetto, IndirectObject) else id(oggetto)
            originale = oggetto.get_object()
            if originale.get("/Subtype") != "/Image":
                continue
            if chiave not in viste:
                viste.add(chiave)
                continue
            copia = type(originale)()
            copia._data = originale._data
            copia.update(originale)
            n = len(xobj)
            nuovo = NameObject(f"/ImR{n}")
            while nuovo in xobj:
                n += 1
                nuovo = NameObject(f"/ImR{n}")
            xobj[nuovo] = writer._add_object(copia)
            operandi[0] = nuovo
            create += 1
            cambiato = True
        if cambiato:
            # un flusso nuovo: compress_identical_objects puo' aver fuso in uno
            # solo i contenuti uguali di piu' pagine, e modificarlo sul posto
            # cambierebbe anche quelle che non hanno le risorse nuove
            flusso = DecodedStreamObject()
            flusso.set_data(contenuto.get_data())
            pagina[NameObject("/Contents")] = writer._add_object(flusso)
    return create


def salva(writer, percorso):
    """Comprime, rende il PDF stampabile da Evince e lo scrive.

    Prima si comprimono i flussi, poi si fondono gli oggetti uguali: nell'ordine
    inverso pypdf lascia in /Contents di qualche pagina un riferimento a un
    oggetto eliminato, la compressione dei flussi si interrompe e il file
    risulta grande il doppio.  Se la compressione fallisce il file viene
    scritto comunque, con un avviso.
    """
    try:
        for pagina in writer.pages:
            pagina.compress_content_streams()
        writer.compress_identical_objects()
    except Exception as e:  # pragma: no cover - dipende dalla versione di pypdf
        warnings.warn(f"compressione del PDF non riuscita: {e}")
    try:
        separa_immagini_ripetute(writer)
    except Exception as e:  # pragma: no cover - dipende dalla versione di pypdf
        warnings.warn(f"separazione delle immagini ripetute non riuscita: {e}")
    with open(percorso, "wb") as fh:
        writer.write(fh)


def impagina(reader, blocco, args, fogli, percorso):
    """Impone il blocco e scrive il file.  Restituisce (n_fascicoli, n_pagine).

    Attenzione: imponendo, pypdf consuma le rotazioni delle pagine di reader.
    Per imporre due volte lo stesso PDF va riaperto.
    """
    writer = PdfWriter()
    n_fasc, n_pag = imponi(reader, writer, blocco, args, fogli * 4, fogli)
    salva(writer, percorso)
    return n_fasc, n_pag
