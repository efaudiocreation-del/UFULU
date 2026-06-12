# widgets_rodec.py
# UFULU RODEC EDITION - WIDGETS HARDWARE-LIKE v33.7
# =====================================================
# RodecKnob          - potenciómetro analógico BX-9
# RodecKnobSelector  - selector rotatorio (drop-in QComboBox)
# RodecLCD           - display LCD verde fósforo
# RodecVUMeter       - barra LED vertical green/amber/red
# RodecFader         - fader vertical estilo mezclador Rodec
# =====================================================

from PyQt6.QtWidgets import QDial, QWidget, QLabel, QVBoxLayout, QSizePolicy, QSlider
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient, QLinearGradient,
    QFont, QPainterPath
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QSize
import math


# === Paleta hardware Rodec ===
PANEL_DARK   = QColor("#384048")
PANEL        = QColor("#485059")
PANEL_LIGHT  = QColor("#5a626b")
RING_SILVER  = QColor("#a8aeb5")
RING_DARK    = QColor("#1a1d20")
KNOB_BLACK   = QColor("#181a1c")
TEXT_WHITE   = QColor("#ecedee")
LCD_BG       = QColor("#0a1410")
LCD_FG       = QColor("#3dff7a")


# -------------------------------------------------------
# RodecKnob: potenciómetro hardware
# -------------------------------------------------------
class RodecKnob(QDial):
    """
    Knob estética Rodec BX-9:
      - Anillo plateado cepillado exterior
      - Cuerpo negro mate con sutil reflejo cenital
      - Aguja indicadora blanca / roja según estilo
      - Tics de referencia en serigrafía clara
      - Halo LED en la posición seleccionada
    """

    def __init__(self, style: str = "red", parent=None):
        super().__init__(parent)
        self.setNotchesVisible(False)
        self.setWrapping(False)
        self._style = style
        self._needle_color, self._led_color = self._palette_for(style)

    def _palette_for(self, name: str):
        # Devuelve (color de aguja, color del LED de halo)
        return {
            "red":    (QColor("#ff3333"), QColor("#ff3333")),
            "yellow": (QColor("#ffd100"), QColor("#ffd100")),
            "amber":  (QColor("#ffc000"), QColor("#ffc000")),
            "cyan":   (QColor("#00ffcc"), QColor("#00ffcc")),
            "green":  (QColor("#00ff66"), QColor("#00ff66")),
            "white":  (QColor("#f0f0f0"), QColor("#a0a8b0")),
        }.get(name, (QColor("#ff3333"), QColor("#ff3333")))

    def paintEvent(self, _):
        side = min(self.width(), self.height())
        cx, cy = self.width() / 2.0, self.height() / 2.0
        r = side / 2.0 - 3

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1) Zócalo profundo (sombra)
        p.setBrush(QBrush(RING_DARK))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # 2) Anillo plateado cepillado
        ring = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.6)
        ring.setColorAt(0.0, QColor("#cdd2d8"))
        ring.setColorAt(0.5, RING_SILVER)
        ring.setColorAt(1.0, QColor("#5a5e63"))
        p.setBrush(QBrush(ring))
        p.setPen(QPen(RING_DARK, 1))
        p.drawEllipse(QPointF(cx, cy), r * 0.95, r * 0.95)

        # 3) Cuerpo negro mate del knob
        rb = r * 0.74
        body = QRadialGradient(cx - rb * 0.35, cy - rb * 0.45, rb * 1.6)
        body.setColorAt(0.0, QColor("#3a3d40"))
        body.setColorAt(0.55, KNOB_BLACK)
        body.setColorAt(1.0, QColor("#0a0c0e"))
        p.setBrush(QBrush(body))
        p.setPen(QPen(QColor("#000"), 1))
        p.drawEllipse(QPointF(cx, cy), rb, rb)

        # 4) Tics serigrafiados (11 marcas, arco -225º .. +45º)
        p.setPen(QPen(QColor("#cfd2d4"), 1))
        for i in range(11):
            ang = math.radians(-225 + i * 27)
            x1 = cx + math.cos(ang) * (r * 0.92)
            y1 = cy + math.sin(ang) * (r * 0.92)
            x2 = cx + math.cos(ang) * (r * 0.99)
            y2 = cy + math.sin(ang) * (r * 0.99)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # 5) Posición actual
        v_min, v_max = self.minimum(), self.maximum()
        rng = max(1, v_max - v_min)
        frac = (self.value() - v_min) / rng
        ang = math.radians(-225 + frac * 270)

        # 6) LED de halo en la posición
        led_r = rb * 0.16
        led_dist = rb * 0.62
        lx = cx + math.cos(ang) * led_dist
        ly = cy + math.sin(ang) * led_dist

        halo = QRadialGradient(lx, ly, led_r * 3)
        halo.setColorAt(0.0, QColor(self._led_color.red(),
                                    self._led_color.green(),
                                    self._led_color.blue(), 200))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(halo))
        p.drawEllipse(QPointF(lx, ly), led_r * 3, led_r * 3)

        p.setBrush(QBrush(self._led_color))
        p.drawEllipse(QPointF(lx, ly), led_r, led_r)

        # 7) Aguja indicadora flecha (centro -> borde) tipo Rodec
        path = QPainterPath()
        ang_perp = ang + math.pi / 2
        base_w = max(2.0, rb * 0.10)
        # Punta
        x_tip = cx + math.cos(ang) * (rb * 0.85)
        y_tip = cy + math.sin(ang) * (rb * 0.85)
        # Base izquierda
        x_bl = cx + math.cos(ang) * (rb * 0.20) + math.cos(ang_perp) * base_w
        y_bl = cy + math.sin(ang) * (rb * 0.20) + math.sin(ang_perp) * base_w
        # Base derecha
        x_br = cx + math.cos(ang) * (rb * 0.20) - math.cos(ang_perp) * base_w
        y_br = cy + math.sin(ang) * (rb * 0.20) - math.sin(ang_perp) * base_w
        path.moveTo(x_tip, y_tip)
        path.lineTo(x_bl, y_bl)
        path.lineTo(x_br, y_br)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._needle_color))
        p.drawPath(path)

        # 8) Reflejo cenital sutil sobre el cuerpo
        gloss = QRadialGradient(cx, cy - rb * 0.7, rb * 1.2)
        gloss.setColorAt(0.0, QColor(255, 255, 255, 35))
        gloss.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(gloss))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), rb, rb)

        p.end()


# -------------------------------------------------------
# RodecKnobSelector — drop-in replacement de QComboBox
# -------------------------------------------------------
class RodecKnobSelector(QWidget):
    """
    Selector rotatorio de N posiciones discretas.
    Compatible con la API de QComboBox usada en main.py:
        - addItems(lista)
        - currentText() / currentIndex()
        - setCurrentText(txt) / setCurrentIndex(i)
        - currentTextChanged (señal)
    Visualmente: knob hardware + LCD verde fósforo con la etiqueta.
    """
    currentTextChanged = pyqtSignal(str)
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, items=None, style: str = "amber", parent=None,
                 size: int = 64):
        super().__init__(parent)
        self._items = list(items) if items else []
        self._knob_size = size

        ly = QVBoxLayout(self)
        ly.setContentsMargins(0, 0, 0, 0)
        ly.setSpacing(3)

        self._knob = RodecKnob(style=style)
        self._knob.setFixedSize(size, size)
        self._knob.setRange(0, max(0, len(self._items) - 1))
        self._knob.setSingleStep(1)
        self._knob.setPageStep(1)
        self._knob.valueChanged.connect(self._on_changed)

        self._lcd = QLabel(self._items[0] if self._items else "—")
        self._lcd.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lcd.setObjectName("lcdSmall")
        self._lcd.setStyleSheet(
            "background:#0a1410; color:#3dff7a; "
            "border:1px solid #1a1d20; border-radius:2px; "
            "padding:3px 6px; font-family:Consolas; "
            "font-size:9px; font-weight:bold; letter-spacing:1px;"
        )
        self._lcd.setMinimumWidth(size + 20)

        ly.addWidget(self._knob, 0, Qt.AlignmentFlag.AlignHCenter)
        ly.addWidget(self._lcd)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    # ---- API drop-in QComboBox ----
    def addItems(self, items):
        self._items = list(items) if items else []
        self._knob.setRange(0, max(0, len(self._items) - 1))
        if self._items:
            self._lcd.setText(self._items[0])

    def currentText(self) -> str:
        if not self._items: return ""
        i = max(0, min(len(self._items) - 1, int(self._knob.value())))
        return self._items[i]

    def currentIndex(self) -> int:
        return int(self._knob.value())

    def setCurrentText(self, text: str):
        if text in self._items:
            self.setCurrentIndex(self._items.index(text))

    def setCurrentIndex(self, idx: int):
        idx = max(0, min(len(self._items) - 1, int(idx)))
        self._knob.setValue(idx)

    # ---- internos ----
    def _on_changed(self, v: int):
        if not self._items: return
        v = max(0, min(len(self._items) - 1, int(v)))
        txt = self._items[v]
        self._lcd.setText(txt)
        self.currentIndexChanged.emit(v)
        self.currentTextChanged.emit(txt)


# -------------------------------------------------------
# RodecLCD — display informativo verde fósforo
# -------------------------------------------------------
class RodecLCD(QLabel):
    """Pantalla LCD verde tipo display Rodec (lecturas: BPM, KEY, etc)."""
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background:#0a1410; color:#3dff7a; "
            "border:1px solid #1a1d20; border-radius:2px; "
            "padding:4px 10px; font-family:Consolas; "
            "font-size:11px; font-weight:bold; letter-spacing:2px;"
        )


# -------------------------------------------------------
# RodecVUMeter — barra LED vertical green/amber/red
# -------------------------------------------------------
class RodecVUMeter(QWidget):
    """VU vertical 12 segmentos con tres zonas (verde/ámbar/rojo)."""
    def __init__(self, segments: int = 12, parent=None):
        super().__init__(parent)
        self._n = max(6, segments)
        self._level = 0.0  # 0..1
        self.setFixedWidth(14)
        self.setMinimumHeight(120)

    def setLevel(self, v: float):
        self._level = max(0.0, min(1.0, float(v)))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height(); w = self.width()
        p.fillRect(0, 0, w, h, RING_DARK)
        seg_h = (h - 4) / self._n
        encendidos = int(round(self._level * self._n))
        for i in range(self._n):
            y = h - 2 - (i + 1) * seg_h
            # Zonas
            if i < self._n * 0.6:
                col_on, col_off = QColor("#00ff66"), QColor("#0a2a14")
            elif i < self._n * 0.85:
                col_on, col_off = QColor("#ffc000"), QColor("#2a1f00")
            else:
                col_on, col_off = QColor("#ff3030"), QColor("#2a0808")
            p.fillRect(QRectF(2, y, w - 4, seg_h - 2),
                       col_on if i < encendidos else col_off)
        p.end()


# -------------------------------------------------------
# RodecFader — fader vertical estilo mezclador Rodec
# -------------------------------------------------------
class RodecFader(QSlider):
    """Fader vertical con marcas de graduación y estética Rodec BX-9."""
    def __init__(self, minimum=0, maximum=100, style="amber", parent=None):
        super().__init__(Qt.Orientation.Vertical, parent)
        self.setRange(minimum, maximum)
        self.setSingleStep(1)
        self.setPageStep(1)
        self.setFixedWidth(30)
        self.setMinimumHeight(100)
        self._color = {
            "amber": QColor("#E0A83A"),
            "green": QColor("#3CFF7A"),
            "red":   QColor("#D94B3D"),
            "cyan":  QColor("#00ffcc"),
            "white": QColor("#CCCCCC"),
        }.get(style, QColor("#E0A83A"))
        self.valueChanged.connect(self.update)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        track_w, track_x = 4, w // 2 - 2
        handle_w, handle_h = 18, 12
        handle_x = w // 2 - handle_w // 2
        val_range = self.maximum() - self.minimum() or 1
        val_ratio = (self.value() - self.minimum()) / val_range
        handle_y = int((1 - val_ratio) * (h - handle_h))

        # Marcas de graduación
        p.setPen(QPen(QColor("#8E98A3"), 1))
        step = max(1, val_range // 10)
        for i in range(self.minimum(), self.maximum() + 1, step):
            y = int((1 - (i - self.minimum()) / val_range) * (h - 2)) + 1
            p.drawLine(track_x + track_w + 2, y, track_x + track_w + 6, y)
            p.drawLine(track_x - 6, y, track_x - 2, y)

        # Ranura (track)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#1a1d20"))
        p.drawRect(track_x, 0, track_w, h)

        # Handle (knob negro alargado)
        gradient = QLinearGradient(handle_x, handle_y, handle_x + handle_w, handle_y + handle_h)
        gradient.setColorAt(0, QColor("#2a2d30"))
        gradient.setColorAt(0.5, QColor("#181a1c"))
        gradient.setColorAt(1, QColor("#0a0c0e"))
        p.setBrush(QBrush(gradient))
        p.setPen(QPen(QColor("#D6D2C4"), 1))
        p.drawRoundedRect(handle_x, handle_y, handle_w, handle_h, 3, 3)

        # Indicador de color central
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._color))
        p.drawRect(handle_x + 6, handle_y + 4, handle_w - 12, handle_h - 8)
        p.end()