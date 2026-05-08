# ufulu_style.py
# UFULU RODEC EDITION - PIEL ANALÓGICA BX-9 v33.7
# =====================================================
# Paleta inspirada en la mesa Rodec BX-9: panel grafito,
# anodizados oscuros, etiquetas serigrafiadas plateadas,
# acentos turquesa para 'sealed' y rojo para 'inject'.
# =====================================================

# Marcadores de cabina (HotCues 1..8) - colores hardware
CUE_COLORS = [
    "#ff3333",  # M1 - Intro / Rojo Rodec
    "#ff8c00",  # M2 - Build  / Naranja
    "#ffd100",  # M3 - Drop   / Amarillo
    "#33ff66",  # M4 - Break  / Verde
    "#00ffcc",  # M5 - Outro  / Turquesa
    "#33aaff",  # M6 - Loop   / Azul claro
    "#bb66ff",  # M7 - Salto  / Violeta
    "#ff66cc",  # M8 - Fade   / Rosa
]


def get_ufulu_stylesheet() -> str:
    """Devuelve el QSS global con la estética Rodec BX-9 v33.7."""
    return """
    /* ======================================== */
    /* PANEL PRINCIPAL                          */
    /* ======================================== */
    QMainWindow, QWidget {
        background-color: #161616;
        color: #e6e6e6;
        font-family: "Segoe UI", "Helvetica Neue", Arial;
        font-size: 11px;
    }

    QLabel {
        color: #cfd2d4;
        font-weight: 500;
        letter-spacing: 0.5px;
    }

    /* HEADERS DE MÓDULO */
    QLabel#maletaHeader {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #2c2c2c, stop:1 #1a1a1a);
        color: #00ffcc;
        font-size: 18px;
        font-weight: bold;
        padding: 12px;
        border: 1px solid #444;
        border-radius: 4px;
        letter-spacing: 3px;
    }

    QLabel#timeLabel {
        color: #00ffcc;
        background: #050505;
        border: 1px solid #333;
        padding: 3px 6px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 10px;
        min-width: 60px;
    }

    QLabel#conteoMaleta {
        color: #ffaa00;
        font-weight: bold;
        font-size: 11px;
        padding-right: 12px;
    }

    /* ======================================== */
    /* TABS (RACK CENTRAL)                      */
    /* ======================================== */
    QTabWidget::pane {
        background: #111;
        border-top: 2px solid #444;
    }
    QTabBar::tab {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #2a2a2a, stop:1 #181818);
        color: #888;
        padding: 10px 26px;
        font-weight: bold;
        letter-spacing: 2px;
        border: 1px solid #333;
        border-bottom: none;
    }
    QTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #3a3a3a, stop:1 #232323);
        color: #00ffcc;
        border-top: 2px solid #00ffcc;
    }
    QTabBar::tab:hover { color: #fff; }

    /* ======================================== */
    /* GROUP BOXES (RACKS)                      */
    /* ======================================== */
    QGroupBox {
        border: 1px solid #555;
        margin-top: 14px;
        padding-top: 10px;
        background: #1c1c1c;
        border-radius: 3px;
        font-weight: bold;
        color: #00ffcc;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        background: #161616;
    }

    /* ======================================== */
    /* INPUTS                                   */
    /* ======================================== */
    QLineEdit, QComboBox {
        background: #050505;
        color: #e6e6e6;
        border: 1px solid #555;
        padding: 5px;
        selection-background-color: #00ffcc;
        selection-color: #000;
    }
    QLineEdit#buscadorMaleta {
        background: #050505;
        color: #00ffcc;
        font-family: "Consolas", monospace;
        border: 1px solid #00ffcc;
    }
    QComboBox::drop-down { border: none; width: 18px; }
    QComboBox QAbstractItemView {
        background: #1a1a1a;
        color: #e6e6e6;
        selection-background-color: #00ffcc;
        selection-color: #000;
    }

    /* ======================================== */
    /* BOTONES                                  */
    /* ======================================== */
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #353535, stop:1 #1f1f1f);
        color: #d8d8d8;
        border: 1px solid #555;
        padding: 7px 12px;
        font-weight: bold;
        letter-spacing: 1px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #4a4a4a, stop:1 #2a2a2a);
        color: #fff;
        border: 1px solid #888;
    }
    QPushButton:pressed { background: #111; color: #00ffcc; }
    QPushButton:checked {
        background: #00aa88; color: #000; border: 1px solid #00ffcc;
    }
    QPushButton#injectBtn {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #b00000, stop:1 #6a0000);
        color: #fff;
        border: 1px solid #ff5555;
        font-size: 12px;
    }
    QPushButton#injectBtn:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #d40000, stop:1 #800000);
    }

    /* ======================================== */
    /* TABLAS                                   */
    /* ======================================== */
    QTableWidget {
        background: #0a0a0a;
        gridline-color: #2a2a2a;
        color: #e6e6e6;
        selection-background-color: #00aa88;
        selection-color: #000;
        alternate-background-color: #121212;
    }
    QHeaderView::section {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #2c2c2c, stop:1 #1a1a1a);
        color: #00ffcc;
        padding: 6px;
        border: 1px solid #2a2a2a;
        font-weight: bold;
        letter-spacing: 1px;
    }

    /* ======================================== */
    /* TREE LATERAL                             */
    /* ======================================== */
    QTreeView {
        background: #0a0a0a;
        color: #cfd2d4;
        border: 1px solid #333;
        selection-background-color: #00aa88;
        selection-color: #000;
        outline: 0;
    }
    QTreeView::item:hover { background: #1c1c1c; }

    /* ======================================== */
    /* SCROLLBARS                               */
    /* ======================================== */
    QScrollBar:vertical {
        background: #0a0a0a;
        width: 10px; margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #444;
        min-height: 25px;
        border-radius: 2px;
    }
    QScrollBar::handle:vertical:hover { background: #00ffcc; }
    QScrollBar:horizontal {
        background: #0a0a0a;
        height: 10px; margin: 0;
    }
    QScrollBar::handle:horizontal {
        background: #444;
        min-width: 25px;
        border-radius: 2px;
    }
    QScrollBar::handle:horizontal:hover { background: #00ffcc; }
    QScrollBar::add-line, QScrollBar::sub-line { background: none; border: none; }

    /* ======================================== */
    /* MENUBAR / MENUS                          */
    /* ======================================== */
    QMenuBar {
        background: #1c1c1c;
        color: #cfd2d4;
        border-bottom: 1px solid #333;
    }
    QMenuBar::item:selected { background: #2c2c2c; color: #00ffcc; }
    QMenu {
        background: #1a1a1a;
        color: #e6e6e6;
        border: 1px solid #333;
    }
    QMenu::item:selected { background: #00aa88; color: #000; }

    /* ======================================== */
    /* DIALOGOS / MESSAGEBOX                    */
    /* ======================================== */
    QDialog, QMessageBox { background: #161616; }
    QCheckBox { color: #cfd2d4; }
    QCheckBox::indicator {
        width: 14px; height: 14px;
        border: 1px solid #555;
        background: #0a0a0a;
    }
    QCheckBox::indicator:checked {
        background: #00ffcc;
        border: 1px solid #00ffcc;
    }
    """
