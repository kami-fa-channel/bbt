"""Estrattore dei blocchetti PNG per la cornice bitmap dei tasselli di bbt.

    python estrai_cornice.py

Programma a se': non dipende da bbt, serve solo a preparare i file che bbt poi
usa.  Parte da un SVG con la cornice intera, la renderizza alla misura in mm e
ai dpi scelti, e ritaglia i blocchetti (angoli e tratti) con il suffisso che bbt
si aspetta.  Finestra in PyQt5 (pip install PyQt5).

La cornice puo' essere anche un'immagine (png, jpg, ...) quando non si riesce a
vettorizzarla: viene ricampionata con interpolazione alla misura voluta.  Cosi'
la scalatura non e' lossless: ingrandendo oltre la risoluzione nativa
l'immagine sfoca (il programma avvisa di quanto).

Due modi: 8 blocchetti (4 angoli ul ur ll lr + 1 tratto ripetuto per lato
hu hl vl vr) oppure 16 (4 angoli + 3 per lato: il tratto di mezzo, che in bbt
sta al centro del lato, e due tratti ripetuti, hu1 hu2 ecc., numerati in senso
antiorario, che riempiono lo spazio fra il centro e i due angoli).  Con
"simmetrico" si prende solo il tratto 1 e il 2 viene scritto come suo specchio.
I pulsanti sono disposti come i pezzi nella cornice.
"""
import sys
import os
from PyQt5.QtSvg import QGraphicsSvgItem, QSvgRenderer
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
                             QGraphicsRectItem, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSpinBox, QCheckBox, QLabel,
                             QFileDialog, QListWidget, QMessageBox, QGraphicsItem, QDoubleSpinBox,
                             QGridLayout, QRadioButton, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSize, QTimer
from PyQt5.QtGui import QPen, QColor, QBrush, QPainter, QWheelEvent, QImage, QPixmap

try:                     # facoltativo: serve solo per lo snap al periodo del motivo
    import numpy as np
except ImportError:
    np = None

# La libreria delle cornici: una cartella accanto a questo script (e a bbt.py).
# E' qui che si salva di default e qui bbt.py va a cercare per prima.
CARTELLA_CORNICI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cornici")

# I 16 pezzi in senso antiorario a partire dall'angolo alto-sinistra:
# (suffisso, (riga, colonna) nella griglia 5x5 dei pulsanti, descrizione).
# Il suffisso senza numero e' il pezzo di mezzo del lato; 1 e 2 sono i due tratti
# ai suoi lati, nel verso antiorario (1 e' il piu' vicino all'angolo che viene prima).
ANELLO = [
    ('ul',  (0, 0), "Angolo alto-sinistra"),
    ('vl1', (1, 0), "Bordo sinistro, tratto 1 (verso l'alto)"),
    ('vl',  (2, 0), "Bordo sinistro, mezzo"),
    ('vl2', (3, 0), "Bordo sinistro, tratto 2 (verso il basso)"),
    ('ll',  (4, 0), "Angolo basso-sinistra"),
    ('hl1', (4, 1), "Bordo basso, tratto 1 (a sinistra)"),
    ('hl',  (4, 2), "Bordo basso, mezzo"),
    ('hl2', (4, 3), "Bordo basso, tratto 2 (a destra)"),
    ('lr',  (4, 4), "Angolo basso-destra"),
    ('vr1', (3, 4), "Bordo destro, tratto 1 (verso il basso)"),
    ('vr',  (2, 4), "Bordo destro, mezzo"),
    ('vr2', (1, 4), "Bordo destro, tratto 2 (verso l'alto)"),
    ('ur',  (0, 4), "Angolo alto-destra"),
    ('hu1', (0, 3), "Bordo alto, tratto 1 (a destra)"),
    ('hu',  (0, 2), "Bordo alto, mezzo"),
    ('hu2', (0, 1), "Bordo alto, tratto 2 (a sinistra)"),
]
# modo 8: angoli e un solo tratto per lato (ripetuto), nell'ordine di sempre
ORDINE_8 = ['ul', 'vl', 'll', 'hl', 'lr', 'vr', 'ur', 'hu']
# nel modo simmetrico il tratto 2 e' lo specchio del tratto 1: (da, specchio orizz., specchio vert.)
SPECCHIO = {'hu2': ('hu1', True, False), 'hl2': ('hl1', True, False),
            'vl2': ('vl1', False, True), 'vr2': ('vr1', False, True)}


def matrice_immagine(img):
    """L'immagine come matrice numpy (altezza, larghezza, 2) di luminosita' e alfa,
    con il colore pesato per l'alfa: i pixel trasparenti sono tutti uguali."""
    img = img.convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    ptr = img.constBits()
    ptr.setsize(img.byteCount())
    a = np.frombuffer(ptr, np.uint8).reshape(h, img.bytesPerLine() // 4, 4)[:, :w]
    alfa = a[..., 3:4].astype(np.float32)
    lum = (a[..., :3].astype(np.float32) * alfa / 255).mean(axis=2, keepdims=True)
    return np.concatenate([lum, alfa], axis=2)


def migliore_periodo(mat, asse, fisso, finale, banda, L0, raggio):
    """La lunghezza L (px), entro `raggio` da L0, per cui un tratto si ripete senza
    giunzione: quella per cui il disegno dopo il tratto e' piu' simile al tratto.

    mat: matrice_immagine; asse 'x' o 'y'; fisso: coordinata del bordo che non si
    muove; finale: True se il bordo trascinato e' quello finale (tratto
    [fisso, fisso+L)), False se e' quello iniziale ([fisso-L, fisso)); banda:
    (da, a) lo spessore del tratto.  Ritorna None se non c'e' un minimo netto
    (motivo non periodico, o zona uniforme)."""
    m = mat if asse == 'x' else mat.transpose(1, 0, 2)
    n = m.shape[1]
    b0, b1 = max(0, int(banda[0])), min(m.shape[0], int(banda[1]))
    if b1 - b0 < 2:
        return None
    band = m[b0:b1:max(1, (b1 - b0) // 64)]
    if not finale:      # specchio: il bordo fermo diventa quello iniziale
        band = band[:, ::-1]
        fisso = n - fisso
    W = int(min(max(L0, 16), 400))
    # la finestra di confronto si accorcia vicino al margine dell'immagine (minimo 16 px)
    lmin, lmax = max(4, L0 - raggio), min(L0 + raggio, n - fisso - 16)
    if fisso < 0 or lmax < lmin:
        return None
    lung = np.arange(lmin, lmax + 1)
    err = np.array([np.abs(band[:, fisso + L:fisso + L + w] - band[:, fisso:fisso + w]).mean()
                    for L in lung for w in [min(W, n - fisso - L)]])
    if err.mean() <= 1.0 or err.min() > 0.5 * err.mean():
        return None
    ok = err <= err.min() + 0.1 * (err.mean() - err.min())
    cand = lung[ok]
    return int(cand[np.argmin(np.abs(cand - L0))])


# Per ogni pezzo (due lettere del suffisso, i tratti 1 e 2 contano come il loro lato):
# da che lato si attacca al precedente e da quale al successivo, andando in senso
# antiorario a partire dall'angolo alto-sinistra.
LATI_ATTACCO = {'ul': ('right', 'bottom'), 'vl': ('top', 'bottom'), 'll': ('top', 'right'),
                'hl': ('left', 'right'), 'lr': ('left', 'top'), 'vr': ('bottom', 'top'),
                'ur': ('bottom', 'left'), 'hu': ('right', 'left')}


def tenue(pix):
    """La stessa immagine in grigio schiarito (alfa invariato): per le copie accanto al
    riquadro, che devono vedersi senza confondersi con il disegno."""
    img = pix.toImage().convertToFormat(QImage.Format_ARGB32)
    res = img.convertToFormat(QImage.Format_Grayscale8).convertToFormat(QImage.Format_ARGB32)
    p = QPainter(res)
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)   # l'alfa dell'originale
    p.drawImage(0, 0, img)
    p.setCompositionMode(QPainter.CompositionMode_SourceAtop)      # schiarisce il grigio
    p.fillRect(res.rect(), QColor(255, 255, 255, 150))
    p.end()
    return QPixmap.fromImage(res)


class NumberedBlockItem(QGraphicsRectItem):
    def __init__(self, rect, number):
        super().__init__(rect)
        self.number = number
        pen = QPen(QColor(0, 255, 0), 2, Qt.SolidLine)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(QColor(0, 255, 0, 20)))
        self.setZValue(4)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        
        font_size = max(12, int(min(self.rect().width(), self.rect().height()) / 3))
        font = painter.font()
        font.setPixelSize(font_size)
        font.setBold(True)
        painter.setFont(font)
        
        text = str(self.number)
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        text_height = fm.height()
        
        margin = max(2, font_size // 4)
        x = int(self.rect().left() + margin)
        y = int(self.rect().top() + margin + text_height)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
        bg_rect = QRectF(x - margin, y - text_height,
                         text_width + 2 * margin, text_height + margin)
        painter.drawRoundedRect(bg_rect, 4.0, 4.0)
        
        painter.setPen(QColor(0, 100, 0))
        painter.drawText(x, y, text)

class SelectionBox(QGraphicsRectItem):
    def __init__(self, x, y, size_w, size_h):
        super().__init__(x, y, size_w, size_h)
        pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(QColor(255, 0, 0, 30)))
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(5)
        # asse su cui si puo' trascinare un bordo per cambiare la lunghezza del
        # tratto: 'x' (orizzontali), 'y' (verticali), None (angoli)
        self.axis = None
        self.on_resize = None       # callback(rect) chiamata mentre si trascina un bordo
        # l'angolo (axis None) si ridimensiona solo finche' questa funzione dice di si'
        self.angolo_modificabile = lambda: False
        self.agganciato = False     # True se l'ultimo trascinamento e' scattato sul periodo
        self.vicini = []            # [(QPixmap, lato)]: i pezzi a cui si attacca, gia' presi
        self.lato_replica = None    # lato su cui disegnare la replica del tratto, o None
        self._bordi = None          # (ex, ey) i bordi che si stanno trascinando
        self._opposti = (0.0, 0.0)  # coordinate (scena) dei bordi opposti, che restano fermi
        self._ridimensiona = False  # True mentre lo spostamento viene dal ridimensionamento
        self.setAcceptHoverEvents(True)

    def _fantasmi(self):
        """[(rettangolo locale, pixmap)] dei pezzi accanto al riquadro, a cui il pezzo
        si attacchera': i vicini gia' presi (self.vicini) e, per i tratti che si
        ripetono, la propria replica (pixmap None) dal lato lato_replica."""
        r = self.rect()

        def dove(lato, w, h):
            return {'top': QRectF(r.left(), r.top() - h, w, h),
                    'bottom': QRectF(r.left(), r.bottom(), w, h),
                    'left': QRectF(r.left() - w, r.top(), w, h),
                    'right': QRectF(r.right(), r.top(), w, h)}[lato]

        out = [(dove(lato, pm.width(), pm.height()), pm) for pm, lato in self.vicini]
        if self.lato_replica:
            out.append((dove(self.lato_replica, r.width(), r.height()), None))
        return out

    def boundingRect(self):
        br = super().boundingRect()
        for f, _ in self._fantasmi():
            br = br.united(f.adjusted(-2, -2, 2, 2))
        return br

    def _bordi_sotto(self, p):
        """(ex, ey) i bordi trascinabili sotto il punto locale p: ex e' 'l', 'r' o None,
        ey e' 't', 'b' o None.  Un tratto ha liberi solo i bordi del suo asse; l'angolo
        tutti, ma solo finche' e' modificabile (prima di salvare il primo pezzo).
        La fascia e' di pochi pixel di schermo, mai piu' di un terzo del lato."""
        libero = self.axis or ('xy' if self.angolo_modificabile() else '')
        if not libero or not self.scene():
            return None, None
        view = self.scene().views()[0]
        r = self.rect()
        m = view.edge_pixels / max(view.transform().m11(), 1e-6)
        mx, my = min(m, r.width() / 3), min(m, r.height() / 3)
        ex = ey = None
        if 'x' in libero:
            ex = 'l' if abs(p.x() - r.left()) <= mx else 'r' if abs(p.x() - r.right()) <= mx else None
        if 'y' in libero:
            ey = 't' if abs(p.y() - r.top()) <= my else 'b' if abs(p.y() - r.bottom()) <= my else None
        return ex, ey

    def hoverMoveEvent(self, event):
        ex, ey = self._bordi_sotto(event.pos())
        if ex and ey:
            self.setCursor(Qt.SizeFDiagCursor if (ex, ey) in (('l', 't'), ('r', 'b'))
                           else Qt.SizeBDiagCursor)
        elif ex:
            self.setCursor(Qt.SizeHorCursor)
        elif ey:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        ex, ey = self._bordi_sotto(event.pos()) if event.button() == Qt.LeftButton else (None, None)
        if ex or ey:
            self._bordi = (ex, ey)
            sr = self.mapRectToScene(self.rect())  # senza lo spessore del contorno
            # i bordi opposti a quelli trascinati restano fermi
            self._opposti = (sr.right() if ex == 'l' else sr.left(),
                             sr.bottom() if ey == 't' else sr.top())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._bordi:
            super().mouseMoveEvent(event)
            return
        view = self.scene().views()[0]
        sr = self.mapRectToScene(self.rect())
        x0, y0, w, h = sr.x(), sr.y(), sr.width(), sr.height()

        def nuovo_bordo(v, ref, opposto, asse, finale, banda):
            if self.axis == asse and view.periodo_attivo():
                p = view.periodo_vicino(asse, v, opposto, finale, banda)
                if p is not None:
                    self.agganciato = True
                    a, b = sorted((round(p), round(opposto)))
                    return a, max(b - a, 1)
            if view.snap_attivo():
                v = view.aggancia(v, ref)
            a, b = sorted((round(v), round(opposto)))
            return a, max(b - a, 1)

        ex, ey = self._bordi
        rx, ry = view.riferimenti()
        self.agganciato = False
        if ex:
            x0, w = nuovo_bordo(event.scenePos().x(), rx, self._opposti[0],
                                'x', ex == 'r', (y0, y0 + h))
        if ey:
            y0, h = nuovo_bordo(event.scenePos().y(), ry, self._opposti[1],
                                'y', ey == 'b', (x0, x0 + w))
        self._ridimensiona = True
        self.setPos(x0, y0)
        self.setRect(0, 0, w, h)
        self._ridimensiona = False
        if self.on_resize:
            self.on_resize(self.rect())

    def mouseReleaseEvent(self, event):
        if self._bordi:
            self._bordi = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        
        rect = self.rect()
        cx = int(rect.center().x())
        cy = int(rect.center().y())
        
        pen_blue = QPen(QColor(0, 150, 255), 2, Qt.DashLine)
        pen_blue.setCosmetic(True)
        painter.setPen(pen_blue)
        painter.drawLine(cx, int(rect.top()), cx, int(rect.bottom()))
        painter.drawLine(int(rect.left()), cy, int(rect.right()), cy)
        
        pen_yellow = QPen(QColor(255, 255, 0), 1, Qt.DotLine)
        pen_yellow.setCosmetic(True)
        painter.setPen(pen_yellow)
        painter.drawRect(rect.adjusted(2, 2, -2, -2))

        self._paint_fantasma(painter)

    def _paint_fantasma(self, painter):
        """Disegna, accanto al riquadro, i pezzi a cui si attacchera' (pieni, con un
        bordo puntinato): si vede subito se la giunzione continua il motivo."""
        view = self.scene().views()[0] if self.scene() and self.scene().views() else None
        if not view or not view.bitmap_item:
            return
        pix = view.bitmap_item.pixmap()
        painter.save()
        painter.setClipRect(QRectF(pix.rect()).translated(-self.pos()))
        pen = QPen(QColor(255, 0, 0), 1, Qt.DotLine)
        pen.setCosmetic(True)
        for f, pm in self._fantasmi():
            if pm is None:      # la replica del tratto stesso, presa dal disegno
                src = QRectF(self.rect()).translated(self.pos()).toAlignedRect().intersected(pix.rect())
                if src.isEmpty():
                    continue
                pm = tenue(pix.copy(src))
                dest = QPointF(src.topLeft()) - self.pos() + (f.topLeft() - self.rect().topLeft())
            else:
                dest = f.topLeft()
            painter.drawPixmap(dest, pm)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(f)
        painter.restore()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene() and not self._ridimensiona:
            view = self.scene().views()[0]
            # il primo riquadro non ha nulla a cui allinearsi: niente calamita finche'
            # non c'e' un pezzo salvato
            if view.snap_attivo() and view.saved_blocks:
                W = self.rect().width()
                H = self.rect().height()

                center_x = value.x() + W / 2
                center_y = value.y() + H / 2

                ref_x, ref_y = view.riferimenti()
                snap_threshold = view.soglia_snap()

                best_dx = snap_threshold + 1
                best_snap_x = None
                for rx in ref_x:
                    dx = abs(center_x - rx)
                    if dx < best_dx:
                        best_dx = dx
                        best_snap_x = rx
                if best_snap_x is not None:
                    value = QPointF(best_snap_x - W / 2, value.y())
                    center_x = best_snap_x

                center_y = value.y() + H / 2
                best_dy = snap_threshold + 1
                best_snap_y = None
                for ry in ref_y:
                    dy = abs(center_y - ry)
                    if dy < best_dy:
                        best_dy = dy
                        best_snap_y = ry
                if best_snap_y is not None:
                    value = QPointF(value.x(), best_snap_y - H / 2)

                return value
        return super().itemChange(change, value)


class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.snap_enabled = True
        self.snap_pixels = 30  # raggio d'azione della calamita, in pixel di schermo
        self.periodo_enabled = np is not None   # snap al periodo del motivo (checkbox)
        self.work_image = None   # il bitmap di lavoro, da cui si ricava la matrice
        self._matrice = None
        self._matrice_di = None
        self.edge_pixels = 8   # larghezza della fascia di bordo trascinabile, in pixel di schermo
        self.bitmap_item = None
        self.saved_blocks = []

    def snap_attivo(self):
        """La calamita e' accesa, e non e' sospesa tenendo premuto Ctrl."""
        return self.snap_enabled and not (QApplication.keyboardModifiers() & Qt.ControlModifier)

    def periodo_attivo(self):
        """Lo snap al periodo e' acceso, possibile (numpy) e non sospeso da Ctrl."""
        return (np is not None and self.periodo_enabled
                and not (QApplication.keyboardModifiers() & Qt.ControlModifier))

    def matrice(self):
        if np is None or self.work_image is None:
            return None
        if self._matrice_di is not self.work_image:
            self._matrice, self._matrice_di = matrice_immagine(self.work_image), self.work_image
        return self._matrice

    def periodo_vicino(self, asse, v, opposto, finale, banda):
        """La coordinata a cui portare il bordo trascinato (in v) perche' il tratto
        si ripeta senza giunzione, o None se non c'e' un periodo chiaro."""
        mat = self.matrice()
        if mat is None or (v > opposto) != finale:
            return None
        L = migliore_periodo(mat, asse, int(round(opposto)), finale, banda,
                             int(round(abs(v - opposto))), int(min(self.soglia_snap(), 80)))
        if L is None:
            return None
        return opposto + L if finale else opposto - L

    def soglia_snap(self):
        """Raggio della calamita in pixel di scena: in pixel di schermo, non di scena,
        cosi' con DPI alti o zoom avanti la calamita resta forte uguale."""
        return self.snap_pixels / max(self.transform().m11(), 1e-6)

    def riferimenti(self):
        """Le coordinate (x, y) a cui il riquadro si aggancia: i bordi e il centro
        del bitmap e dei blocchi gia' presi."""
        ref_x, ref_y = [], []
        if self.bitmap_item:
            r = self.bitmap_item.boundingRect()
            ref_x.extend([r.left(), r.right(), r.center().x()])
            ref_y.extend([r.top(), r.bottom(), r.center().y()])
        for block in self.saved_blocks:
            r = block['rect']
            ref_x.extend([r.left(), r.right(), r.center().x()])
            ref_y.extend([r.top(), r.bottom(), r.center().y()])
        return ref_x, ref_y

    def aggancia(self, v, refs):
        """v spostato sul riferimento piu' vicino, se e' entro la soglia."""
        soglia = self.soglia_snap()
        best = min(refs, key=lambda r: abs(v - r), default=None)
        return best if best is not None and abs(v - best) <= soglia else v

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.25
        old_pos = self.mapToScene(event.pos())
        zoom_factor = zoom_in_factor if event.angleDelta().y() > 0 else 1 / zoom_in_factor
        self.scale(zoom_factor, zoom_factor)
        new_pos = self.mapToScene(event.pos())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

class SvgCutterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frame Block Extractor - Bitmap Mode")
        self.resize(1000, 700)
        
        self.svg_path = None
        self.src_image = None  # sorgente raster (None se la cornice e' un SVG)
        self.bitmap_item = None
        self.work_image = None
        self.selection_box = None
        self.saved_blocks = []
        self.pezzo_corrente = None  # il pezzo che il riquadro sta per prendere
        self._angolo_px = None  # misura esatta (px) dell'angolo trascinata col mouse
        self.lunghezze = {}  # ultima lunghezza (px) presa per i tratti 'h' e 'v'
        self.position_numbers = {}
        self.original_aspect = 1.0  # Rapporto larghezza/altezza originale
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self.render_svg)
        self.setup_ui()
        self.update_block_size()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        control_panel = QVBoxLayout()
        
        self.btn_load = QPushButton("1. Carica SVG o immagine")
        self.btn_load.clicked.connect(self.load_svg)
        control_panel.addWidget(self.btn_load)
        
        # DPI
        control_panel.addWidget(QLabel("Risoluzione (DPI):"))
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(72, 1200)
        self.spin_dpi.setValue(600)
        self.spin_dpi.valueChanged.connect(self.update_block_size)
        self.spin_dpi.valueChanged.connect(self.schedule_render)
        self.spin_dpi.setSuffix(" DPI")
        control_panel.addWidget(self.spin_dpi)
        
        # Checkbox per mantenere proporzioni
        self.chk_keep_aspect = QCheckBox("Mantieni proporzioni (consigliato)")
        self.chk_keep_aspect.setChecked(True)
        self.chk_keep_aspect.toggled.connect(self.toggle_aspect_lock)
        self.chk_keep_aspect.setStyleSheet("font-weight: bold; color: #006400;")
        control_panel.addWidget(self.chk_keep_aspect)
        
        # Dimensioni finali
        control_panel.addWidget(QLabel("Dimensioni finali cornice (mm):"))
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Largh:"))
        self.spin_w_mm = QDoubleSpinBox()
        self.spin_w_mm.setRange(10, 1000)
        self.spin_w_mm.setValue(100)
        self.spin_w_mm.setSuffix(" mm")
        self.spin_w_mm.valueChanged.connect(self.on_width_changed)
        self.spin_w_mm.valueChanged.connect(self.schedule_render)
        size_layout.addWidget(self.spin_w_mm)
        control_panel.addLayout(size_layout)
        
        size_layout2 = QHBoxLayout()
        size_layout2.addWidget(QLabel("Altezz:"))
        self.spin_h_mm = QDoubleSpinBox()
        self.spin_h_mm.setRange(10, 1000)
        self.spin_h_mm.setValue(150)
        self.spin_h_mm.setSuffix(" mm")
        self.spin_h_mm.valueChanged.connect(self.on_height_changed)
        self.spin_h_mm.valueChanged.connect(self.schedule_render)
        size_layout2.addWidget(self.spin_h_mm)
        control_panel.addLayout(size_layout2)
        
        self.lbl_info = QLabel("Proporzioni originali: -")
        self.lbl_info.setStyleSheet("color: gray; font-size: 10px;")
        control_panel.addWidget(self.lbl_info)
        
        # Dimensione blocchetto
        control_panel.addWidget(QLabel("Angolo (mm): i tratti ne ereditano lo spessore"))
        size_block_layout = QHBoxLayout()
        self.spin_w = QDoubleSpinBox()
        self.spin_w.setRange(0.5, 500)
        self.spin_w.setDecimals(2)
        self.spin_w.setSingleStep(0.5)
        self.spin_w.setSuffix(" mm")
        self.spin_w.setValue(8.0)
        self.spin_w.valueChanged.connect(self.update_block_size)
        size_block_layout.addWidget(QLabel("Largh:"))
        size_block_layout.addWidget(self.spin_w)
        
        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(0.5, 500)
        self.spin_h.setDecimals(2)
        self.spin_h.setSingleStep(0.5)
        self.spin_h.setSuffix(" mm")
        self.spin_h.setValue(8.0)
        self.spin_h.valueChanged.connect(self.update_block_size)
        size_block_layout.addWidget(QLabel("Altezz:"))
        size_block_layout.addWidget(self.spin_h)
        control_panel.addLayout(size_block_layout)
        # misura fisica del blocchetto: e' quella che avra' stampato in bbt
        self.lbl_block_mm = QLabel("")
        self.lbl_block_mm.setStyleSheet("color: gray; font-size: 10px;")
        control_panel.addWidget(self.lbl_block_mm)
        
        self.chk_snap = QCheckBox("Attiva Snap al Centro (Calamita)")
        self.chk_snap.setChecked(True)
        self.chk_snap.setToolTip("Tieni premuto Ctrl mentre trascini per sospenderla.")
        self.chk_snap.toggled.connect(self.toggle_snap)
        control_panel.addWidget(self.chk_snap)

        self.chk_periodo = QCheckBox("Snap al periodo del motivo (tratti)")
        self.chk_periodo.setChecked(np is not None)
        self.chk_periodo.setEnabled(np is not None)
        self.chk_periodo.setToolTip(
            "Trascinando il bordo di un tratto, la lunghezza scatta sul valore per cui il "
            "motivo si ripete senza giunzione. Ctrl lo sospende."
            if np is not None else "Richiede numpy (pip install numpy).")
        self.chk_periodo.toggled.connect(self.toggle_periodo)
        control_panel.addWidget(self.chk_periodo)
        
        control_panel.addWidget(QLabel("2. Modo e pezzi (ordine antiorario):"))
        mode_layout = QHBoxLayout()
        self.rad_8 = QRadioButton("8 blocchi")
        self.rad_16 = QRadioButton("16 blocchi")
        self.rad_8.setChecked(True)
        self.rad_8.toggled.connect(self.cambia_modo)
        mode_layout.addWidget(self.rad_8)
        mode_layout.addWidget(self.rad_16)
        control_panel.addLayout(mode_layout)
        self.chk_sym = QCheckBox("Simmetrico (il tratto 2 e' lo specchio dell'1)")
        self.chk_sym.setToolTip("Solo modo 16: si prendono i tratti 1 e il mezzo; i tratti 2 "
                                "vengono scritti all'esportazione come copia specchiata.")
        self.chk_sym.toggled.connect(self.cambia_modo)
        control_panel.addWidget(self.chk_sym)

        # i pulsanti sono disposti come i pezzi nella cornice
        grid = QGridLayout()
        grid.setSpacing(2)
        self.cell_buttons = {}
        self.cell_info = {}
        for suffix, (riga, col), descr in ANELLO:
            btn = QPushButton("")
            btn.setFixedSize(36, 36)
            btn.clicked.connect(lambda checked, s=suffix: self.add_selection(s))
            grid.addWidget(btn, riga, col)
            self.cell_buttons[suffix] = btn
            self.cell_info[suffix] = descr
        # la griglia sta in un widget di misura fissa, cosi' il layout del pannello
        # non puo' comprimerla (i pulsanti si sovrapporrebbero) quando manca spazio
        grid.setContentsMargins(0, 0, 0, 0)
        grid_box = QWidget()
        grid_box.setLayout(grid)
        grid_box.setFixedSize(5 * 36 + 4 * grid.spacing(), 5 * 36 + 4 * grid.spacing())
        grid_wrap = QHBoxLayout()
        grid_wrap.addStretch()
        grid_wrap.addWidget(grid_box)
        grid_wrap.addStretch()
        control_panel.addLayout(grid_wrap)
        self.aggiorna_modo()

        control_panel.addWidget(QLabel("Blocchi Salvati:"))
        self.list_blocks = QListWidget()
        control_panel.addWidget(self.list_blocks)
        
        self.btn_clear = QPushButton("Cancella Blocchi")
        self.btn_clear.clicked.connect(self.clear_blocks)
        control_panel.addWidget(self.btn_clear)
        
        self.btn_export_all = QPushButton("3. Esporta TUTTI in Cartella (PNG)")
        self.btn_export_all.setStyleSheet("background-color: #d4edda; font-weight: bold;")
        self.btn_export_all.clicked.connect(self.export_all)
        control_panel.addWidget(self.btn_export_all)
        
        control_panel.addStretch()
        
        lbl_help = QLabel("Istruzioni:\n"
                          "1. Carica l'SVG e scegli la modalità di scala.\n"
                          "2. Se 'Mantieni proporzioni' è attivo, basta la larghezza.\n"
                          "3. Posiziona i blocchetti (snap automatico) ed esporta in PNG.\n"
                          "Prima di prendere il primo pezzo l'angolo si ridimensiona trascinando "
                          "il riquadro rosso (o dagli spinbox); poi e' bloccato. I tratti hanno "
                          "lo spessore dell'angolo: se ne cambia la lunghezza trascinando i bordi.")
        lbl_help.setWordWrap(True)
        lbl_help.setStyleSheet("color: gray; font-size: 10px;")
        control_panel.addWidget(lbl_help)
        
        self.scene = QGraphicsScene()
        self.view = CustomGraphicsView(self.scene)
        # il pannello e' alto: in un'area scorrevole non dipende dall'altezza dello
        # schermo (senza, i pulsanti si sovrapporrebbero agli altri controlli)
        pannello = QWidget()
        pannello.setLayout(control_panel)
        scorri = QScrollArea()
        scorri.setWidget(pannello)
        scorri.setWidgetResizable(True)
        scorri.setFrameShape(QFrame.NoFrame)
        scorri.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scorri.setMinimumWidth(pannello.sizeHint().width() + scorri.verticalScrollBar().sizeHint().width() + 4)
        layout.addWidget(scorri, 1)
        layout.addWidget(self.view, 4)

    def toggle_aspect_lock(self, checked):
        """Blocca/sblocca l'altezza in base al checkbox proporzioni"""
        self.spin_h_mm.setEnabled(not checked)
        if checked and self.original_aspect > 0:
            # Ricalcola l'altezza in base alla larghezza corrente
            new_h = self.spin_w_mm.value() / self.original_aspect
            self.spin_h_mm.blockSignals(True)
            self.spin_h_mm.setValue(new_h)
            self.spin_h_mm.blockSignals(False)
            self.update_info_label()
            self.schedule_render()

    def on_width_changed(self):
        """Quando cambia la larghezza, ricalcola l'altezza se proporzioni bloccate"""
        if self.chk_keep_aspect.isChecked() and self.original_aspect > 0:
            new_h = self.spin_w_mm.value() / self.original_aspect
            self.spin_h_mm.blockSignals(True)
            self.spin_h_mm.setValue(new_h)
            self.spin_h_mm.blockSignals(False)
        self.update_info_label()

    def on_height_changed(self):
        """Quando cambia l'altezza (solo se proporzioni sbloccate)"""
        self.update_info_label()

    def update_info_label(self):
        w = self.spin_w_mm.value()
        h = self.spin_h_mm.value()
        if self.original_aspect > 0:
            current_aspect = w / h
            diff = abs(current_aspect - self.original_aspect) / self.original_aspect * 100
            if diff < 0.1:
                status = "✓ Proporzioni mantenute"
                color = "green"
            else:
                status = f"⚠ Deformazione: {diff:.1f}%"
                color = "orange"
            self.lbl_info.setText(f"Originale: 1:{self.original_aspect:.3f} | Corrente: 1:{current_aspect:.3f} | {status}")
            self.lbl_info.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")

    def load_svg(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona SVG o immagine", "",
            "Cornici (*.svg *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;SVG (*.svg)")
        if not file_path:
            return
        if file_path.lower().endswith((".svg", ".svgz")):
            src = None
            orig_size = QSvgRenderer(file_path).defaultSize()
        else:
            src = QImage(file_path)
            if src.isNull():
                QMessageBox.warning(self, "Attenzione", "Immagine non leggibile: " + file_path)
                return
            orig_size = src.size()
        self.svg_path = file_path
        self.src_image = src
        self.original_aspect = orig_size.width() / orig_size.height()

        # Aggiorna l'altezza in base alla larghezza corrente
        self.spin_h_mm.blockSignals(True)
        self.spin_h_mm.setValue(self.spin_w_mm.value() / self.original_aspect)
        self.spin_h_mm.blockSignals(False)
        self.update_info_label()

        self.render_svg(fit=True)
        w_mm, h_mm, dpi = self.spin_w_mm.value(), self.spin_h_mm.value(), self.spin_dpi.value()
        QMessageBox.information(self, "Bitmap Creato",
                               f"Immagine scalata a:\n"
                               f"{w_mm:.1f} x {h_mm:.1f} mm\n"
                               f"{self.work_image.width()} x {self.work_image.height()} pixel @ {dpi} DPI\n\n"
                               f"Proporzioni originali: 1:{self.original_aspect:.3f}"
                               + (f"\n\nImmagine raster {self.src_image.width()} x "
                                  f"{self.src_image.height()} px: la scalatura non e' lossless."
                                  if self.src_image else ""))

    def schedule_render(self):
        """Cambiati mm o DPI: rigenera l'immagine (con una piccola attesa, mentre si digita)."""
        if self.svg_path:
            self.render_timer.start(350)

    def render_svg(self, fit=False):
        """(Ri)crea il bitmap di lavoro dall'SVG alla dimensione in mm e ai DPI scelti.

        Senza fit la vista non viene adattata alla finestra: lo zoom resta quello
        di prima, cosi' una cornice piu' piccola si vede piu' piccola.  I blocchi
        gia' estratti sono in pixel del vecchio bitmap, quindi vengono scartati.
        """
        if not self.svg_path:
            return
        renderer = None if self.src_image else QSvgRenderer(self.svg_path)
        w_mm = self.spin_w_mm.value()
        h_mm = self.spin_h_mm.value()
        dpi = self.spin_dpi.value()
        target_w_px = max(1, int(w_mm * dpi / 25.4))
        target_h_px = max(1, int(h_mm * dpi / 25.4))

        scarta = bool(self.saved_blocks)
        self.clear_blocks()
        self.scene.clear()
        self.selection_box = None
        self.bitmap_item = None

        # Crea QImage con sfondo trasparente
        self.work_image = QImage(target_w_px, target_h_px, QImage.Format_ARGB32)
        self.work_image.fill(Qt.transparent)
        # i DPI finiscono nei PNG: bbt ne ricava la misura stampata del blocchetto
        dpm = int(round(dpi / 0.0254))
        self.work_image.setDotsPerMeterX(dpm)
        self.work_image.setDotsPerMeterY(dpm)

        if renderer:
            # Renderizza SVG scalato nel QImage
            painter = QPainter(self.work_image)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            renderer.render(painter)
            painter.end()
        else:
            # raster: ricampionamento con interpolazione (in due passi se si ingrandisce
            # molto, che sfoca meno di un salto solo)
            img = self.src_image.convertToFormat(QImage.Format_ARGB32)
            while img.width() * 2 < target_w_px:
                img = img.scaled(img.width() * 2, img.height() * 2, Qt.IgnoreAspectRatio,
                                 Qt.SmoothTransformation)
            img = img.scaled(target_w_px, target_h_px, Qt.IgnoreAspectRatio,
                             Qt.SmoothTransformation)
            painter = QPainter(self.work_image)
            painter.drawImage(0, 0, img)
            painter.end()

        self.bitmap_item = self.scene.addPixmap(QPixmap.fromImage(self.work_image))
        self.view.bitmap_item = self.bitmap_item
        self.view.work_image = self.work_image
        self.scene.setSceneRect(self.bitmap_item.boundingRect())
        if fit:
            self.view.fitInView(self.bitmap_item, Qt.KeepAspectRatio)
            self.view.scale(0.9, 0.9)

        self.create_selection_box()
        self.selection_box.setPos(self.bitmap_item.boundingRect().topLeft())
        self.imposta_corrente(self.prossimo_pezzo(), forza=True)
        extra = ""
        if self.src_image:
            nativi = self.src_image.width() * 25.4 / w_mm
            zoom = target_w_px / self.src_image.width()
            extra = f"  | immagine {self.src_image.width()} px = {nativi:.0f} DPI nativi"
            if zoom > 1.05:
                extra += f", ingrandita x{zoom:.2f} (sfocata: abbassa i DPI a ~{nativi:.0f})"
        self.statusBar().showMessage(
            f"{w_mm:.1f} x {h_mm:.1f} mm = {target_w_px} x {target_h_px} px @ {dpi} DPI"
            + extra + ("  (blocchi gia' estratti scartati)" if scarta else ""))

    def create_selection_box(self):
        if self.selection_box:
            self.scene.removeItem(self.selection_box)
        w, h = self.block_px()
        self.selection_box = SelectionBox(0, 0, w, h)
        self.selection_box.on_resize = self.mostra_misura
        self.selection_box.angolo_modificabile = lambda: not self.saved_blocks
        self.scene.addItem(self.selection_box)

    @staticmethod
    def tipo_pezzo(suffix):
        """'h' e 'v' per i tratti orizzontali e verticali, None per gli angoli."""
        return suffix[0] if suffix[0] in "hv" else None

    def forma_box(self, tipo):
        """(larghezza, altezza, asse libero) del riquadro per un tipo di pezzo.  Gli
        angoli hanno la misura impostata; un tratto ne eredita lo spessore e ha per
        lunghezza quella dell'ultimo tratto dello stesso tipo (o dell'angolo)."""
        cw, ch = self.block_px()
        if tipo == 'h':
            return self.lunghezze.get('h', cw), ch, 'x'
        if tipo == 'v':
            return cw, self.lunghezze.get('v', ch), 'y'
        return cw, ch, None

    def box_va_bene(self, suffix):
        """Il riquadro ha gia' la forma giusta per questo pezzo?"""
        tipo = self.tipo_pezzo(suffix)
        cw, ch = self.block_px()
        r = self.selection_box.rect()
        if self.selection_box.axis != self.forma_box(tipo)[2]:
            return False
        if tipo == 'h':
            return round(r.height()) == ch
        if tipo == 'v':
            return round(r.width()) == cw
        return round(r.width()) == cw and round(r.height()) == ch

    def adatta_box(self, tipo):
        """Da' al riquadro la forma del tipo di pezzo, restando centrato dove e'."""
        box = self.selection_box
        w, h, asse = self.forma_box(tipo)
        c = box.mapRectToScene(box.rect()).center()
        box.axis = asse
        box._ridimensiona = True
        box.setRect(0, 0, w, h)
        box.setPos(round(c.x() - w / 2), round(c.y() - h / 2))
        box._ridimensiona = False

    def cambia_modo(self, *_):
        """Cambiato modo (8/16/simmetrico): si riparte dal primo pezzo ancora da prendere."""
        if getattr(self, "selection_box", None):
            self.imposta_corrente(self.prossimo_pezzo(), forza=True)
        else:
            self.aggiorna_modo()

    def imposta_corrente(self, suffix, forza=False):
        """Il riquadro passa a prendere il pezzo suffix: ne prende la forma (se non ce
        l'ha, o se forza), si evidenzia il pulsante e si ridisegnano i vicini."""
        self.pezzo_corrente = suffix
        if suffix and self.selection_box and (forza or not self.box_va_bene(suffix)):
            self.adatta_box(self.tipo_pezzo(suffix))
        self.aggiorna_modo()

    def anello_modo(self):
        """I pezzi del modo corrente, in ordine antiorario, come cornice chiusa."""
        if self.rad_16.isChecked():
            return [x for x, _, _ in ANELLO]
        return list(ORDINE_8)

    def pixmap_pezzo(self, suffix):
        """L'immagine del pezzo gia' preso (anche del tratto 2 del modo simmetrico, che
        e' lo specchio del tratto 1), o None se non e' stato preso."""
        per = {b['suffix']: b for b in self.saved_blocks}
        specchio = None
        if suffix in per:
            rect = per[suffix]['rect']
        elif (suffix in SPECCHIO and self.rad_16.isChecked() and self.chk_sym.isChecked()
              and SPECCHIO[suffix][0] in per):
            rect = per[SPECCHIO[suffix][0]]['rect']
            specchio = SPECCHIO[suffix][1:]
        else:
            return None
        img = self.work_image.copy(int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()))
        if specchio:
            img = img.mirrored(*specchio)
        return tenue(QPixmap.fromImage(img))

    def aggiorna_vicini(self):
        """Dice al riquadro a cosa si attacchera' il pezzo corrente: il precedente
        (dal lato da cui si arriva) e, per i tratti che si ripetono, la replica di
        se stesso dall'altra parte, altrimenti il successivo se e' gia' stato preso."""
        box = self.selection_box
        if not box:
            return
        box.vicini, box.lato_replica = [], None
        s = self.pezzo_corrente
        if s and self.work_image:
            anello = self.anello_modo()
            if s in anello:
                i = anello.index(s)
                prima, dopo = LATI_ATTACCO[s[:2]]
                pm = self.pixmap_pezzo(anello[i - 1])
                if pm:
                    box.vicini.append((pm, prima))
                # i tratti si ripetono: tutti nel modo 8, i soli 1 e 2 nel modo 16
                if self.tipo_pezzo(s) and (self.rad_8.isChecked() or s[-1] in "12"):
                    box.lato_replica = dopo
                else:
                    pm = self.pixmap_pezzo(anello[(i + 1) % len(anello)])
                    if pm:
                        box.vicini.append((pm, dopo))
        box.prepareGeometryChange()
        box.update()

    def mostra_misura(self, rect):
        dpi = self.spin_dpi.value()
        if self.selection_box.axis is None and not self.saved_blocks:
            # l'angolo e' stato ridimensionato col mouse: i mm negli spinbox lo seguono
            w, h = int(rect.width()), int(rect.height())
            for spin, px in ((self.spin_w, w), (self.spin_h, h)):
                spin.blockSignals(True)
                spin.setValue(px * 25.4 / dpi)
                spin.blockSignals(False)
            self._angolo_px = (w, h, (self.spin_w.value(), self.spin_h.value(), dpi))
            self.aggiorna_etichetta_angolo()
        self.statusBar().showMessage("Riquadro %d x %d px = %.2f x %.2f mm%s"
                                     % (rect.width(), rect.height(),
                                        rect.width() * 25.4 / dpi, rect.height() * 25.4 / dpi,
                                        "  |  agganciato al periodo del motivo"
                                        if self.selection_box.agganciato else ""))

    def prossimo_pezzo(self):
        """Il primo pezzo del modo corrente (in ordine) non ancora preso, o None."""
        presi = {b['suffix'] for b in self.saved_blocks}
        ordine = ([x for x, _, _ in ANELLO] if self.rad_16.isChecked() else ORDINE_8)
        attivi = set(self.suffissi_attivi())
        return next((x for x in ordine if x in attivi and x not in presi), None)

    def block_px(self):
        """Il blocchetto e' impostato in mm: i pixel sono mm * dpi / 25,4."""
        dpi = self.spin_dpi.value()
        if self._angolo_px and self._angolo_px[2] == (self.spin_w.value(), self.spin_h.value(), dpi):
            return self._angolo_px[:2]  # trascinato col mouse, senza l'arrotondamento dei mm
        return (max(1, round(self.spin_w.value() * dpi / 25.4)),
                max(1, round(self.spin_h.value() * dpi / 25.4)))

    def aggiorna_etichetta_angolo(self):
        w, h = self.block_px()
        self.lbl_block_mm.setText("= %d x %d pixel a %d DPI (il PNG non viene scalato)"
                                  % (w, h, self.spin_dpi.value()))

    def blocca_angolo(self):
        """L'angolo si cambia solo finche' non c'e' nessun pezzo salvato: gli altri
        pezzi ne ereditano la misura."""
        libero = not self.saved_blocks
        for spin in (self.spin_w, self.spin_h):
            spin.setEnabled(libero)
            spin.setToolTip("" if libero else "Bloccato: ci sono pezzi gia' presi. "
                            "Cancella i blocchi per cambiare la misura dell'angolo.")

    def update_block_size(self):
        w, h = self.block_px()
        self.aggiorna_etichetta_angolo()
        if self.selection_box:
            # l'angolo e' cambiato: il riquadro si rifa' con la misura nuova, restando
            # del tipo che aveva (angolo, tratto orizzontale o verticale)
            self.adatta_box({'x': 'h', 'y': 'v'}.get(self.selection_box.axis))

    def toggle_periodo(self, checked):
        self.view.periodo_enabled = checked

    def toggle_snap(self, checked):
        self.view.snap_enabled = checked

    def suffissi_attivi(self):
        """I suffissi che l'utente deve prendere nel modo corrente."""
        if self.rad_16.isChecked():
            fuori = set(SPECCHIO) if self.chk_sym.isChecked() else set()
            return [s for s, _, _ in ANELLO if s not in fuori]
        return list(ORDINE_8)

    def aggiorna_modo(self, *_):
        """Abilita i pulsanti del modo scelto, rinumera, colora quelli gia' presi."""
        self.chk_sym.setEnabled(self.rad_16.isChecked())
        attivi = self.suffissi_attivi()
        self.position_numbers = {s: i + 1 for i, s in enumerate(
            attivi if self.rad_8.isChecked() else [x for x, _, _ in ANELLO])}
        presi = {b['suffix'] for b in self.saved_blocks}
        if getattr(self, "selection_box", None) and self.pezzo_corrente not in attivi:
            # il modo e' cambiato e il pezzo corrente non c'e' piu': si riparte dal primo libero
            self.pezzo_corrente = self.prossimo_pezzo()
            if self.pezzo_corrente and not self.box_va_bene(self.pezzo_corrente):
                self.adatta_box(self.tipo_pezzo(self.pezzo_corrente))
        for suffix, btn in self.cell_buttons.items():
            on = suffix in attivi
            btn.setEnabled(on)
            n = self.position_numbers.get(suffix)
            btn.setText(str(n) if (on and n) else "")
            tip = "%s  (_%s)" % (self.cell_info[suffix], suffix)
            if not on:
                tip += "\nnon usato in questo modo"
            btn.setToolTip(tip)
            corrente = "border: 3px solid #0d6efd; " if on and suffix == self.pezzo_corrente else ""
            if on and suffix in presi:
                btn.setStyleSheet(corrente + "background-color: #b7e1c1; font-weight: bold;")
            elif on:
                btn.setStyleSheet(corrente + "background-color: #e2e3e5; font-weight: bold;")
            else:
                btn.setStyleSheet("")
        # i blocchi disegnati: solo quelli del modo corrente, con il numero giusto
        if hasattr(self, "scene"):
            for item in self.scene.items():
                tag = str(item.data(0))
                if isinstance(item, NumberedBlockItem) and tag.startswith("saved_"):
                    suffix = tag[len("saved_"):]
                    item.setVisible(suffix in attivi)
                    item.number = self.position_numbers.get(suffix, 0)
                    item.update()
        if getattr(self, "selection_box", None):
            self.aggiorna_vicini()

    def add_selection(self, suffix):
        if not self.selection_box or not self.bitmap_item:
            QMessageBox.warning(self, "Attenzione", "Carica prima un'immagine SVG!")
            return

        if suffix != self.pezzo_corrente or not self.box_va_bene(suffix):
            # non e' il pezzo che il riquadro sta per prendere (o non ne ha la forma): lo
            # si seleziona, con i vicini a cui si attacchera', e si lascia all'utente il
            # tempo di regolare la lunghezza e posizionarlo
            self.imposta_corrente(suffix)
            self.statusBar().showMessage(
                "Selezionato: %s. %sPosizionalo e premi di nuovo il pulsante per prenderlo."
                % (self.cell_info[suffix],
                   "Trascina i bordi per la lunghezza. " if self.tipo_pezzo(suffix) else ""))
            return

        rect = self.selection_box.mapRectToScene(self.selection_box.rect())
        rect = QRectF(int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()))
        
        base_name = os.path.splitext(os.path.basename(self.svg_path))[0]
        name = f"{base_name}_{suffix}"
        
        existing = [b for b in self.saved_blocks if b['suffix'] == suffix]
        if existing:
            reply = QMessageBox.question(self, "Sovrascrivi?",
                                         f"Hai già estratto un pezzo '{suffix}'. Sovrascrivere?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
            self.saved_blocks = [b for b in self.saved_blocks if b['suffix'] != suffix]
            for i in range(self.list_blocks.count()):
                if self.list_blocks.item(i).text().endswith(f"_{suffix}"):
                    self.list_blocks.takeItem(i)
                    break
            for item in self.scene.items():
                if isinstance(item, QGraphicsRectItem) and item.data(0) == f"saved_{suffix}":
                    self.scene.removeItem(item)
                    break

        self.saved_blocks.append({'name': name, 'rect': rect, 'suffix': suffix})
        self.view.saved_blocks = self.saved_blocks
        self.list_blocks.addItem(name)
        
        number = self.position_numbers.get(suffix, 0)
        saved_rect_item = NumberedBlockItem(rect, number)
        saved_rect_item.setData(0, f"saved_{suffix}")
        self.scene.addItem(saved_rect_item)
        
        tipo = self.tipo_pezzo(suffix)
        if tipo:
            self.lunghezze[tipo] = int(rect.width() if tipo == 'h' else rect.height())

        self.aggiorna_modo()
        self.blocca_angolo()
        # il riquadro passa subito alla forma del prossimo pezzo da prendere
        prossimo = self.prossimo_pezzo()
        self.imposta_corrente(prossimo or suffix, forza=True)
        self.statusBar().showMessage(f"Estratto: {name} (n. {number}): posizionati sul prossimo pezzo"
                                     + (f" ({self.cell_info[prossimo]})" if prossimo else ""))

    def clear_blocks(self):
        self.saved_blocks = []
        self.lunghezze = {}
        self.view.saved_blocks = []
        self.list_blocks.clear()
        for item in self.scene.items():
            if isinstance(item, QGraphicsRectItem) and str(item.data(0)).startswith("saved_"):
                self.scene.removeItem(item)
        if hasattr(self, "cell_buttons"):
            if getattr(self, "selection_box", None):
                self.imposta_corrente(self.prossimo_pezzo(), forza=True)
            else:
                self.aggiorna_modo()
        if hasattr(self, "spin_h"):
            self.blocca_angolo()

    def da_esportare(self):
        """[(nome, rettangolo, specchio)] del modo corrente; specchio e' None oppure
        (orizzontale, verticale) per i tratti 2 del modo simmetrico."""
        attivi = set(self.suffissi_attivi())
        base = os.path.splitext(os.path.basename(self.svg_path))[0]
        per_suffisso = {b['suffix']: b for b in self.saved_blocks}
        out = [(b['name'], b['rect'], None) for b in self.saved_blocks if b['suffix'] in attivi]
        if self.rad_16.isChecked() and self.chk_sym.isChecked():
            for s2, (da, mh, mv) in SPECCHIO.items():
                if da in per_suffisso:
                    out.append((f"{base}_{s2}", per_suffisso[da]['rect'], (mh, mv)))
        return out

    def export_all(self):
        if not self.saved_blocks:
            QMessageBox.warning(self, "Attenzione", "Nessun blocco da esportare!")
            return
        pezzi = self.da_esportare()
        presenti = {n.rsplit("_", 1)[1] for n, _, _ in pezzi}
        richiesti = set(self.suffissi_attivi())
        if self.rad_16.isChecked() and self.chk_sym.isChecked():
            richiesti |= set(SPECCHIO)
        mancano = [s for s, _, _ in ANELLO if s in richiesti and s not in presenti]
        if mancano:
            r = QMessageBox.question(self, "Pezzi mancanti",
                                     "Mancano: %s.\nUna cornice incompleta in bbt non funziona. "
                                     "Esportare lo stesso?" % ", ".join("_" + m for m in mancano),
                                     QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.No:
                return
        os.makedirs(CARTELLA_CORNICI, exist_ok=True)
        folder_path = QFileDialog.getExistingDirectory(
            self, "Cartella di esportazione (di default la libreria 'cornici')", CARTELLA_CORNICI)
        if folder_path:
            for nome, rect, specchio in pezzi:
                self.save_block_to_png(rect, os.path.join(folder_path, f"{nome}.png"), specchio)
            QMessageBox.information(self, "Completato",
                                    f"Esportati {len(pezzi)} blocchi PNG in {folder_path}")

    def save_block_to_png(self, rect, file_path, specchio=None):
        """Estrae un rettangolo dal bitmap di lavoro e lo salva come PNG
        (specchio = (orizzontale, verticale) per salvarlo ribaltato)"""
        if not self.work_image:
            return
            
        cropped = self.work_image.copy(int(rect.x()), int(rect.y()), 
                                       int(rect.width()), int(rect.height()))
        if specchio:
            cropped = cropped.mirrored(*specchio)
        dpm = int(round(self.spin_dpi.value() / 0.0254))
        cropped.setDotsPerMeterX(dpm)
        cropped.setDotsPerMeterY(dpm)
        cropped.save(file_path, "PNG")

def main():
    app = QApplication(sys.argv[:1])
    window = SvgCutterApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
