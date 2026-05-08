# ufulu_style.py
# UFULU RODEC EDITION - PIEL ANALÓGICA BX-9 v33.7
# =====================================================
# Paleta extraída de la mesa Rodec BX-9 real:
#   - Panel:        azul antracita mate
#   - Anillos:      plata cepillada
#   - Cuerpo knob:  negro mate
#   - Texto:        blanco serigrafiado
#   - LCD:          verde fósforo sobre negro
#   - LEDs:         verde / ámbar / rojo
# =====================================================

# === PALETA RODEC BX-9 ===
ROD_PANEL_DARK   = "#384048"   # antracita más profundo (sombras)
ROD_PANEL        = "#485059"   # antracita base (casquillo BX-9)
ROD_PANEL_LIGHT  = "#5a626b"   # antracita iluminado (highlights)
ROD_RING_SILVER  = "#9ea4ab"   # plata cepillada (anillos knobs)
ROD_RING_DARK    = "#1a1d20"   # zócalo profundo

ROD_TEXT         = "#ecedee"   # serigrafía blanca
ROD_TEXT_DIM     = "#9aa3ad"   # texto secundario
ROD_LCD_BG       = "#0a1410"   # fondo LCD verde fósforo
ROD_LCD_FG       = "#3dff7a"   # texto LCD verde
ROD_LCD_GLOW     = "#00cc55"   # halo del LCD

ROD_LED_GREEN    = "#00ff66"
ROD_LED_AMBER    = "#ffc000"
ROD_LED_RED      = "#ff3030"

# Marcadores de cabina (HotCues 1..8) - colores LED hardware
CUE_COLORS = [
    "#ff3333",  # M1 - Intro / Rojo Rodec
    "#ff8c00",  # M2 - Build  / Naranja
    "#ffd100",  # M3 - Drop   / Amarillo
    "#33ff66",  # M4 - Break  / Verde fósforo
    "#00ffcc",  # M5 - Outro  / Turquesa
    "#33aaff",  # M6 - Loop   / Azul claro
    "#bb66ff",  # M7 - Salto  / Violeta
    "#ff66cc",  # M8 - Fade   / Rosa
]


def get_ufulu_stylesheet() -> str:
    """Devuelve el QSS global con la estética Rodec BX-9 v33.7 — azul antracita."""
    return f"""
    /* ================================================ */
    /* PANEL PRINCIPAL — chasis Rodec antracita        */
    /* ================================================ */
    QMainWindow, QWidget {{
        background-color: {ROD_PANEL};
        color: {ROD_TEXT};
        font-family: "Segoe UI", "Helvetica Neue", Arial;
        font-size: 11px;
    }}

    QLabel {{
        color: {ROD_TEXT};
        font-weight: 500;
        letter-spacing: 0.5px;
    }}

    /* HEADERS (placa serigrafiada) */
    QLabel#maletaHeader {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {ROD_PANEL_LIGHT},
                                    stop:1 {ROD_PANEL_DARK});
        color: {ROD_LED_AMBER};
        font-size: 17px;
        font-weight: bold;
        padding: 12px;
        border: 1px solid {ROD_RING_DARK};
        border-radius: 3px;
        letter-spacing: 4px;
    }}

    /* DISPLAY LCD numérico — bajo cada knob */
    QLabel#timeLabel, QLabel.lcdSmall {{
        color: {ROD_LCD_FG};
        background: {ROD_LCD_BG};
        border: 1px solid {ROD_RING_DARK};
        border-radius: 2px;
        padding: 3px 8px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 10px;
        font-weight: bold;
        min-width: 60px;
        letter-spacing: 1px;
    }}

    QLabel#conteoMaleta {{
        color: {ROD_LED_AMBER};
        background: {ROD_LCD_BG};
        border: 1px solid {ROD_RING_DARK};
        padding: 4px 10px;
        font-family: "Consolas", monospace;
        font-weight: bold;
        font-size: 10px;
        letter-spacing: 2px;
    }}

    /* ================================================ */
    /* TABS — pestañas de rack                         */
    /* ================================================ */
    QTabWidget::pane {{
        background: {ROD_PANEL};
        border-top: 2px solid {ROD_RING_SILVER};
    }}
    QTabBar::tab {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {ROD_PANEL_LIGHT},
                                    stop:1 {ROD_PANEL_DARK});
        color: {ROD_TEXT_DIM};
        padding: 11px 28px;
        font-weight: bold;
        letter-spacing: 3px;
        border: 1px solid {ROD_RING_DARK};
        border-bottom: none;
    }}
    QTabBar::tab:selected {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {ROD_PANEL_LIGHT},
                                    stop:1 {ROD_PANEL});
        color: {ROD_LED_AMBER};
        border-top: 2px solid {ROD_LED_AMBER};
    }}
    QTabBar::tab:hover {{ color: {ROD_TEXT}; }}

    /* ================================================ */
    /* GROUP BOXES — bloques serigrafiados             */
    /* ================================================ */
    QGroupBox {{
        border: 1px solid {ROD_RING_SILVER};
        margin-top: 14px;
        padding-top: 10px;
        background: {ROD_PANEL_DARK};
        border-radius: 3px;
        font-weight: bold;
        color: {ROD_LED_AMBER};
        letter-spacing: 2px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
        background: {ROD_PANEL};
    }}

    /* ================================================ */
    /* INPUTS                                          */
    /* ================================================ */
    QLineEdit {{
        background: {ROD_LCD_BG};
        color: {ROD_LCD_FG};
        border: 1px solid {ROD_RING_DARK};
        border-radius: 2px;
        padding: 5px 8px;
        font-family: "Consolas", monospace;
        selection-background-color: {ROD_LED_AMBER};
        selection-color: {ROD_PANEL_DARK};
    }}
    QLineEdit#buscadorMaleta {{
        background: {ROD_LCD_BG};
        color: {ROD_LCD_FG};
        font-family: "Consolas", monospace;
        font-size: 12px;
        border: 1px solid {ROD_LCD_GLOW};
        padding: 7px;
        letter-spacing: 1px;
    }}

    /* QComboBox legacy (fallback si quedara alguno) */
    QComboBox {{
        background: {ROD_LCD_BG};
        color: {ROD_LCD_FG};
        border: 1px solid {ROD_RING_SILVER};
        padding: 5px 8px;
        font-family: "Consolas", monospace;
    }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{
        background: {ROD_LCD_BG};
        color: {ROD_LCD_FG};
        selection-background-color: {ROD_LED_AMBER};
        selection-color: {ROD_PANEL_DARK};
    }}

    /* ================================================ */
    /* BOTONES — pulsadores hardware                   */
    /* ================================================ */
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {ROD_PANEL_LIGHT},
                                    stop:1 {ROD_PANEL_DARK});
        color: {ROD_TEXT};
        border: 1px solid {ROD_RING_SILVER};
        border-radius: 2px;
        padding: 7px 14px;
        font-weight: bold;
        letter-spacing: 1px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #6a727b,
                                    stop:1 {ROD_PANEL});
        color: {ROD_LED_AMBER};
        border: 1px solid {ROD_TEXT};
    }}
    QPushButton:pressed {{
        background: {ROD_PANEL_DARK};
        color: {ROD_LED_GREEN};
    }}
    QPushButton:checked {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #006633, stop:1 #003319);
        color: {ROD_LED_GREEN};
        border: 1px solid {ROD_LED_GREEN};
    }}
    /* Botón rojo de inyección — acción fuerte */
    QPushButton#injectBtn {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #d40000, stop:1 #6a0000);
        color: white;
        border: 1px solid #ff5555;
        font-size: 12px;
        letter-spacing: 2px;
    }}
    QPushButton#injectBtn:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #ff2020, stop:1 #800000);
    }}

    /* ================================================ */
    /* TABLAS — pantallas LCD verde fósforo            */
    /* ================================================ */
    QTableWidget {{
        background: {ROD_LCD_BG};
        gridline-color: #1a3320;
        color: {ROD_LCD_FG};
        font-family: "Consolas", "Courier New", monospace;
        font-size: 10px;
        selection-background-color: {ROD_LED_AMBER};
        selection-color: {ROD_PANEL_DARK};
        alternate-background-color: #0c1a14;
        border: 2px solid {ROD_RING_DARK};
        border-radius: 3px;
    }}
    QTableWidget::item {{ padding: 4px; }}
    QHeaderView::section {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {ROD_PANEL_LIGHT},
                                    stop:1 {ROD_PANEL_DARK});
        color: {ROD_LED_AMBER};
        padding: 7px;
        border: 1px solid {ROD_RING_DARK};
        font-family: "Segoe UI", sans-serif;
        font-weight: bold;
        font-size: 10px;
        letter-spacing: 2px;
    }}

    /* ================================================ */
    /* TREE LATERAL — suministro físico                 */
    /* ================================================ */
    QTreeView {{
        background: {ROD_LCD_BG};
        color: {ROD_LCD_FG};
        border: 1px solid {ROD_RING_DARK};
        font-family: "Consolas", monospace;
        selection-background-color: {ROD_LED_AMBER};
        selection-color: {ROD_PANEL_DARK};
        outline: 0;
    }}
    QTreeView::item:hover {{ background: #142820; }}

    /* ================================================ */
    /* SCROLLBARS — barras finas grafito                */
    /* ================================================ */
    QScrollBar:vertical {{
        background: {ROD_PANEL_DARK};
        width: 10px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {ROD_RING_SILVER};
        min-height: 25px;
        border-radius: 2px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {ROD_LED_AMBER}; }}
    QScrollBar:horizontal {{
        background: {ROD_PANEL_DARK};
        height: 10px; margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {ROD_RING_SILVER};
        min-width: 25px;
        border-radius: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {ROD_LED_AMBER}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ background: none; border: none; }}

    /* ================================================ */
    /* MENUBAR / MENUS                                  */
    /* ================================================ */
    QMenuBar {{
        background: {ROD_PANEL_DARK};
        color: {ROD_TEXT};
        border-bottom: 1px solid {ROD_RING_DARK};
        font-weight: bold;
        letter-spacing: 1px;
    }}
    QMenuBar::item:selected {{
        background: {ROD_PANEL_LIGHT};
        color: {ROD_LED_AMBER};
    }}
    QMenu {{
        background: {ROD_PANEL_DARK};
        color: {ROD_TEXT};
        border: 1px solid {ROD_RING_SILVER};
    }}
    QMenu::item:selected {{
        background: {ROD_LED_AMBER};
        color: {ROD_PANEL_DARK};
    }}

    /* ================================================ */
    /* DIALOGOS / MESSAGEBOX / CHECKBOX                */
    /* ================================================ */
    QDialog, QMessageBox {{ background: {ROD_PANEL}; }}
    QCheckBox {{ color: {ROD_TEXT}; letter-spacing: 1px; }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {ROD_RING_SILVER};
        background: {ROD_LCD_BG};
    }}
    QCheckBox::indicator:checked {{
        background: {ROD_LED_GREEN};
        border: 1px solid {ROD_LED_GREEN};
    }}

    QProgressBar {{
        background: {ROD_LCD_BG};
        color: {ROD_TEXT};
        border: 1px solid {ROD_RING_SILVER};
        text-align: center;
        font-family: "Consolas", monospace;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {ROD_LED_GREEN},
                                    stop:1 {ROD_LED_AMBER});
    }}
    """
