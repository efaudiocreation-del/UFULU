# widgets_ufulu.py
# UFULU RODEC EDITION - WIDGETS DE FLUJO v33.7
# =====================================================
# SplashWelcome  -> diálogo inicial (selección de raíz)
# SplashForense  -> diálogo de progreso del análisis
# RatingWidget   -> 5 estrellas para histórico de sesión
# =====================================================

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QProgressBar, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QColor, QPalette


# -------------------------------------------------------
# SplashWelcome: pantalla de arranque
# -------------------------------------------------------
class SplashWelcome(QDialog):
    """
    Diálogo de bienvenida UFULU RODEC EDITION.
    Permite seleccionar la maleta raíz (carpeta con audios).
    Recuerda la última raíz usada (parametro default).
    """

    def __init__(self, default_path: str = "", parent=None):
        super().__init__(parent)
        self.selected_path = default_path or ""
        self.setWindowTitle("UFULU RODEC EDITION")
        self.setFixedSize(560, 320)
        self.setModal(True)

        # Fondo grafito
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#161616"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        ly = QVBoxLayout(self)
        ly.setContentsMargins(30, 25, 30, 25)
        ly.setSpacing(15)

        # Cabecera
        titulo = QLabel("UFULU · RODEC EDITION")
        titulo.setStyleSheet(
            "color:#00ffcc; font-size:22px; font-weight:bold; "
            "letter-spacing:6px;"
        )
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitulo = QLabel("CONSOLA FORENSE DE PROCESADO ANALÓGICO  ·  v33.7")
        subtitulo.setStyleSheet(
            "color:#888; font-size:10px; letter-spacing:3px;"
        )
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ly.addWidget(titulo)
        ly.addWidget(subtitulo)
        ly.addSpacing(20)

        # Caja de selección
        lbl = QLabel("MALETA RAÍZ (CARPETA DE SUMINISTRO)")
        lbl.setStyleSheet("color:#cfd2d4; font-weight:bold; letter-spacing:2px;")

        ruta_ly = QHBoxLayout()
        self.in_ruta = QLineEdit(self.selected_path)
        self.in_ruta.setStyleSheet(
            "background:#050505; color:#00ffcc; border:1px solid #00ffcc; "
            "padding:8px; font-family:Consolas; font-size:11px;"
        )
        btn_browse = QPushButton("EXAMINAR…")
        btn_browse.clicked.connect(self._examinar)
        btn_browse.setFixedWidth(110)
        btn_browse.setStyleSheet(
            "background:#2c2c2c; color:#cfd2d4; border:1px solid #555; "
            "padding:7px; font-weight:bold;"
        )

        ruta_ly.addWidget(self.in_ruta)
        ruta_ly.addWidget(btn_browse)

        ly.addWidget(lbl)
        ly.addLayout(ruta_ly)
        ly.addStretch()

        # Botonera inferior
        botones = QHBoxLayout()
        botones.addStretch()

        btn_cancel = QPushButton("CANCELAR")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setFixedWidth(110)

        btn_ok = QPushButton("ENCENDER CONSOLA")
        btn_ok.clicked.connect(self._aceptar)
        btn_ok.setFixedWidth(180)
        btn_ok.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #b00000, stop:1 #6a0000); color:white; "
            "border:1px solid #ff5555; padding:8px; font-weight:bold;"
        )

        botones.addWidget(btn_cancel)
        botones.addWidget(btn_ok)
        ly.addLayout(botones)

    def _examinar(self):
        ini = self.in_ruta.text() or os.path.expanduser("~")
        ruta = QFileDialog.getExistingDirectory(self, "Selecciona la maleta raíz", ini)
        if ruta:
            self.in_ruta.setText(ruta)

    def _aceptar(self):
        ruta = self.in_ruta.text().strip()
        if not ruta or not os.path.isdir(ruta):
            QMessageBox.warning(self, "RUTA INVÁLIDA",
                                "Selecciona una carpeta válida que contenga audios.")
            return
        self.selected_path = ruta
        self.accept()


# -------------------------------------------------------
# SplashForense: progreso del análisis
# -------------------------------------------------------
class SplashForense(QDialog):
    """
    Diálogo modal con barra de progreso usado durante la
    extracción de ADN (motor EngineUfulu). Se actualiza vía
    update_prog(actual, total).
    """

    def __init__(self, total_archivos: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EXTRACCIÓN DE ADN")
        self.setFixedSize(460, 160)
        self.setModal(True)

        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#161616"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        ly = QVBoxLayout(self)
        ly.setContentsMargins(25, 20, 25, 20)
        ly.setSpacing(12)

        self.lbl_estado = QLabel(
            f"PROCESANDO 0 / {total_archivos} ARCHIVOS…"
        )
        self.lbl_estado.setStyleSheet(
            "color:#00ffcc; font-weight:bold; letter-spacing:2px; font-size:12px;"
        )
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.bar = QProgressBar()
        self.bar.setRange(0, max(1, total_archivos))
        self.bar.setValue(0)
        self.bar.setTextVisible(True)
        self.bar.setStyleSheet(
            "QProgressBar { background:#050505; color:#fff; "
            "border:1px solid #555; padding:1px; text-align:center; }"
            "QProgressBar::chunk { background: qlineargradient("
            "x1:0,y1:0,x2:1,y2:0, stop:0 #007a66, stop:1 #00ffcc); }"
        )

        sub = QLabel("RIGOR FORENSE EN CURSO  ·  TRIANGULACIÓN BPM + KEY + ENERGÍA")
        sub.setStyleSheet("color:#888; font-size:9px; letter-spacing:2px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ly.addWidget(self.lbl_estado)
        ly.addWidget(self.bar)
        ly.addWidget(sub)

    def update_prog(self, actual: int, total: int):
        self.bar.setMaximum(max(1, total))
        self.bar.setValue(actual)
        self.lbl_estado.setText(f"PROCESANDO {actual} / {total} ARCHIVOS…")
        if actual >= total:
            self.lbl_estado.setText("ANÁLISIS FINALIZADO")
            # Auto-cierre breve
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(700, self.accept)


# -------------------------------------------------------
# RatingWidget: 5 estrellas para histórico de sesiones
# -------------------------------------------------------
class RatingWidget(QWidget):
    """5 estrellas clicables. value() devuelve 0..5."""
    changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._buttons = []
        ly = QHBoxLayout(self)
        ly.setContentsMargins(0, 0, 0, 0)
        ly.setSpacing(2)
        for i in range(1, 6):
            b = QPushButton("☆")
            b.setFixedSize(28, 28)
            b.setFlat(True)
            b.setStyleSheet(
                "QPushButton { color:#666; background:transparent; "
                "border:none; font-size:18px; }"
                "QPushButton:hover { color:#ffd100; }"
            )
            b.clicked.connect(lambda chk, v=i: self.setValue(v))
            ly.addWidget(b)
            self._buttons.append(b)

    def value(self) -> int:
        return self._value

    def setValue(self, v: int):
        v = max(0, min(5, int(v)))
        self._value = v
        for i, b in enumerate(self._buttons, 1):
            if i <= v:
                b.setText("★")
                b.setStyleSheet(
                    "QPushButton { color:#ffd100; background:transparent; "
                    "border:none; font-size:18px; }"
                )
            else:
                b.setText("☆")
                b.setStyleSheet(
                    "QPushButton { color:#666; background:transparent; "
                    "border:none; font-size:18px; }"
                    "QPushButton:hover { color:#ffd100; }"
                )
        self.changed.emit(v)
