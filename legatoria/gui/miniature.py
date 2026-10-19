"""Miniature delle pagine del PDF per l'anteprima dell'imposizione.

Le pagine si rendono con pypdfium2 se e' installato, altrimenti con pdftoppm
(poppler-utils), che su Linux c'e' quasi sempre.  Serve comunque pillow, per
passare le immagini a tkinter.  Senza nessuno dei due motori l'anteprima resta
schematica.

Il rendering gira in un thread a parte, cosi' la finestra non si blocca mentre
si sfoglia un PDF pesante: chiedi() restituisce subito l'immagine se e' gia'
pronta, altrimenti None, e mette la pagina in coda.  Chi disegna controlla
pronte() di tanto in tanto e ridisegna quando cambia.
"""

import io
import shutil
import subprocess
import threading

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pypdfium2 as pdfium
except ImportError:
    pdfium = None


def motore():
    """Il motore di rendering disponibile: "pdfium", "pdftoppm" o None."""
    if Image is None:
        return None
    if pdfium is not None:
        return "pdfium"
    if shutil.which("pdftoppm"):
        return "pdftoppm"
    return None


# pdfium non e' thread-safe, nemmeno fra documenti diversi: due thread che lo usano
# insieme possono mandare in crash l'intero processo ("Fatal Python error: Aborted").
# Succede quando si apre un altro PDF mentre il thread del precedente sta ancora
# rendendo una pagina (chiudi() non aspetta che finisca), quindi il blocco e' uno
# solo per tutte le istanze di Miniature.
_PDFIUM = threading.Lock()

# Le pagine si rendono a lati "a gradini": ridimensionare un'immagine gia' pronta
# costa poco, rifarla a ogni pixel di differenza (trascinando il divisore, per
# esempio) costerebbe molto.
GRADINO_PX = 160
MASSIMO_PX = 1600
MASSIME_IN_CACHE = 120


def lato_a_gradini(lato_px):
    gradini = max(1, -(-int(lato_px) // GRADINO_PX))
    return min(MASSIMO_PX, gradini * GRADINO_PX)


class Miniature:
    def __init__(self, percorso, nome_motore="auto"):
        """nome_motore: "pdfium", "pdftoppm", None (nessuno) o "auto" (vedi motore())."""
        self.percorso = str(percorso)
        self.motore = motore() if nome_motore == "auto" else nome_motore
        self.cache = {}             # (indice, lato) -> immagine PIL
        self.coda = []              # (indice, lato), l'ultima richiesta in fondo
        self.contatore = 0          # cresce a ogni pagina pronta
        self._al_lavoro = False     # il thread sta rendendo una pagina
        self.chiuso = False
        self._cond = threading.Condition()
        self._thread = None
        if self.motore:
            self._thread = threading.Thread(target=self._lavora, daemon=True)
            self._thread.start()

    @property
    def disponibile(self):
        return self.motore is not None

    def chiedi(self, indice, lato_px):
        """L'immagine PIL della pagina `indice` (0-based) con il lato lungo di
        almeno `lato_px` pixel, o None se non e' ancora pronta."""
        if not self.disponibile:
            return None
        chiave = (indice, lato_a_gradini(lato_px))
        with self._cond:
            if chiave in self.cache:
                return self.cache[chiave]
            # ripiego: la stessa pagina a un'altra risoluzione, intanto
            ripiego = next((img for (i, _), img in self.cache.items() if i == indice), None)
            if chiave in self.coda:
                self.coda.remove(chiave)
            self.coda.append(chiave)
            self._cond.notify()
        return ripiego

    def in_attesa(self):
        """True finche' qualche pagina chiesta non e' pronta."""
        with self._cond:
            return bool(self.coda) or self._al_lavoro

    def pronte(self):
        """Un numero che cambia ogni volta che una nuova pagina e' pronta."""
        return self.contatore

    def dimentica_coda(self):
        """Lascia perdere le richieste non ancora servite (si e' cambiato fascicolo)."""
        with self._cond:
            self.coda.clear()

    def chiudi(self):
        with self._cond:
            self.chiuso = True
            self.coda.clear()
            self._cond.notify()

    # ------------------------------------------------------------ thread
    def _lavora(self):
        documento = None
        while True:
            with self._cond:
                while not self.coda and not self.chiuso:
                    self._cond.wait()
                if self.chiuso:
                    break
                chiave = self.coda.pop()          # prima le richieste piu' recenti
                self._al_lavoro = True
            indice, lato = chiave
            try:
                if self.motore == "pdfium":
                    with _PDFIUM:                 # vedi _PDFIUM
                        if documento is None:
                            documento = pdfium.PdfDocument(self.percorso)
                        immagine = self._rendi_pdfium(documento, indice, lato)
                else:
                    immagine = self._rendi_pdftoppm(indice, lato)
            except Exception:
                immagine = None
            with self._cond:
                if len(self.cache) >= MASSIME_IN_CACHE:
                    self.cache.clear()
                # anche un fallimento si ricorda, per non riprovare all'infinito
                self.cache[chiave] = immagine
                self.contatore += 1
                self._al_lavoro = False
        if documento is not None:
            with _PDFIUM:
                documento.close()

    @staticmethod
    def _rendi_pdfium(documento, indice, lato):
        pagina = documento[indice]
        scala = lato / max(pagina.get_width(), pagina.get_height())
        return pagina.render(scale=max(0.05, scala)).to_pil().convert("RGB")

    def _rendi_pdftoppm(self, indice, lato):
        n = str(indice + 1)
        uscita = subprocess.run(
            ["pdftoppm", "-f", n, "-l", n, "-scale-to", str(lato), "-png", self.percorso],
            capture_output=True, timeout=60, check=True).stdout
        immagine = Image.open(io.BytesIO(uscita))
        immagine.load()
        return immagine.convert("RGB")
