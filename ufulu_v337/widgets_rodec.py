# widgets_rodec.py
# UFULU RODEC EDITION - WIDGETS HARDWARE-LIKE v33.7
# =====================================================
# Knobs, faders y selectores rotatorios estética Rodec BX-9.
# Pintado custom para parecer potenciómetros físicos.
# =====================================================

from PyQt6.QtWidgets import QDial
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
import math


# -------------------------------------------------------
# RodecKnob: Potenciómetro analógico tipo BX-9
# -------------------------------------------------------
class RodecKnob(QDial):
    """
    Knob personalizado con cuerpo metalizado, ribete y testigo
    luminoso indicando la posición. Soporta estilos de color:
        - "red"   : LED rojo (sondas / inyección)
        - "cyan"  : LED turquesa (sealed / curaduría)
        - "amber" : LED ámbar (filtros)
    """

    def __init__(self, style: str = "red", parent=None):
        super().__init__(parent)
        self.setNotchesVisible(False)
        self.setWrapping(False)
        self._style = style
        self._color_led = self._led_for_style(style)

    def _led_for_style(self, name: str) -> QColor:
        return {
            "red":   QColor("#ff3333"),
            "cyan":  QColor("#00ffcc"),
            "amber": QColor("#ffaa00"),
            "white": QColor("#f0f0f0"),
        }.get(name, QColor("#ff3333"))

    def paintEvent(self, _):
        side = min(self.width(), self.height())
        cx, cy = self.width() / 2.0, self.height() / 2.0
        r = side / 2.0 - 4

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1) Anillo exterior anodizado oscuro
        grad_ring = QRadialGradient(cx, cy, r)
        grad_ring.setColorAt(0.0, QColor("#3b3b3b"))
        grad_ring.setColorAt(0.85, QColor("#1a1a1a"))
        grad_ring.setColorAt(1.0, QColor("#0a0a0a"))
        p.setPen(QPen(QColor("#000"), 1))
        p.setBrush(QBrush(grad_ring))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # 2) Cuerpo metalizado interior
        rb = r * 0.78
        grad_body = QRadialGradient(cx - rb * 0.3, cy - rb * 0.3, rb * 1.4)
        grad_body.setColorAt(0.0, QColor("#5a5a5a"))
        grad_body.setColorAt(0.55, QColor("#2c2c2c"))
        grad_body.setColorAt(1.0, QColor("#101010"))
        p.setBrush(QBrush(grad_body))
        p.setPen(QPen(QColor("#000"), 1))
        p.drawEllipse(QPointF(cx, cy), rb, rb)

        # 3) Ticks circulares (referencia visual)
        p.setPen(QPen(QColor("#888"), 1))
        for i in range(11):
            ang = math.radians(-225 + i * 27)  # -225..+45
            x1 = cx + math.cos(ang) * (r * 0.92)
            y1 = cy + math.sin(ang) * (r * 0.92)
            x2 = cx + math.cos(ang) * (r * 0.99)
            y2 = cy + math.sin(ang) * (r * 0.99)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # 4) Testigo LED en posición
        v_min, v_max = self.minimum(), self.maximum()
        rng = max(1, v_max - v_min)
        frac = (self.value() - v_min) / rng
        ang = math.radians(-225 + frac * 270)  # arco 270º

        led_r = rb * 0.18
        led_dist = rb * 0.65
        lx = cx + math.cos(ang) * led_dist
        ly = cy + math.sin(ang) * led_dist

        # halo
        halo = QRadialGradient(lx, ly, led_r * 2.5)
        halo.setColorAt(0.0, QColor(self._color_led.red(),
                                    self._color_led.green(),
                                    self._color_led.blue(), 180))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(halo))
        p.drawEllipse(QPointF(lx, ly), led_r * 2.5, led_r * 2.5)

        # núcleo LED
        p.setBrush(QBrush(self._color_led))
        p.drawEllipse(QPointF(lx, ly), led_r, led_r)

        # 5) Línea indicadora desde centro al LED
        p.setPen(QPen(QColor("#cfd2d4"), 2))
        p.drawLine(QPointF(cx, cy),
                   QPointF(cx + math.cos(ang) * (rb * 0.55),
                           cy + math.sin(ang) * (rb * 0.55)))

        p.end()


# -------------------------------------------------------
# RodecKnobSelector: selector rotatorio de N posiciones
# -------------------------------------------------------
class RodecKnobSelector(RodecKnob):
    """
    Selector de N posiciones discretas (e.g. selector de canal,
    selector de modo). Salta entre etiquetas con clic / rueda.
    """
    selected = pyqtSignal(int, str)

    def __init__(self, etiquetas, style: str = "amber", parent=None):
        super().__init__(style=style, parent=parent)
        self._etiquetas = list(etiquetas) if etiquetas else ["A"]
        self.setRange(0, max(0, len(self._etiquetas) - 1))
        self.setSingleStep(1)
        self.valueChanged.connect(self._emitir)

    def _emitir(self, v: int):
        v = max(0, min(len(self._etiquetas) - 1, int(v)))
        self.selected.emit(v, self._etiquetas[v])

    def etiqueta_actual(self) -> str:
        v = max(0, min(len(self._etiquetas) - 1, int(self.value())))
        return self._etiquetas[v]

    def paintEvent(self, ev):
        super().paintEvent(ev)
        # Dibujamos la etiqueta debajo del knob
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#00ffcc"), 1))
        f = QFont("Consolas", 8, QFont.Weight.Bold)
        p.setFont(f)
        rect = QRectF(0, self.height() - 16, self.width(), 14)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.etiqueta_actual())
        p.end()
