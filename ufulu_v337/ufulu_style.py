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
ROD_PANEL_DARK   = "#1E2A36"   # antracita más profundo (sombras)
ROD_PANEL        = "#263443"   # antracita base (casquillo BX-9)
ROD_PANEL_LIGHT  = "#3F566B"    # antracita iluminado (highlights)
ROD_RING_SILVER  = "#D6D2C4"   # plata cepillada (anillos knobs)
ROD_RING_DARK    = "#7A6B3A"   # zócalo profundo

ROD_TEXT         = "#E6E3DA"   # serigrafía blanca
ROD_TEXT_DIM     = "#8E98A3"   # texto secundario
ROD_LCD_BG       = "#2D3B2F"   # fondo LCD verde fósforo
ROD_LCD_FG       = "#A6FF9E"   # texto LCD verde
ROD_LCD_GLOW     = "#4CFF88"   # halo del LCD

ROD_LED_GREEN    = "#3CFF7A"
ROD_LED_AMBER    = "#E0A83A"
ROD_LED_RED      = "#D94B3D"

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


def get_ufulu_stylesheet(tema: str = "ORIGINAL") -> str:
    """
    Devuelve el QSS global según el tema elegido.
    """
    # --- Diccionario maestro de paletas ---
    PALETAS = {
        "ORIGINAL": {
            "ROD_PANEL": ROD_PANEL,
            "ROD_PANEL_DARK": ROD_PANEL_DARK,
            "ROD_PANEL_LIGHT": ROD_PANEL_LIGHT,
            "ROD_RING_SILVER": ROD_RING_SILVER,
            "ROD_RING_DARK": ROD_RING_DARK,
            "ROD_TEXT": ROD_TEXT,
            "ROD_TEXT_DIM": ROD_TEXT_DIM,
            "ROD_LCD_BG": ROD_LCD_BG,
            "ROD_LCD_FG": ROD_LCD_FG,
            "ROD_LCD_GLOW": ROD_LCD_GLOW,
            "ROD_LED_GREEN": ROD_LED_GREEN,
            "ROD_LED_AMBER": ROD_LED_AMBER,
            "ROD_LED_RED": ROD_LED_RED,
        },
        "ORDEN": {
            "ROD_PANEL": "#F5F5F5",
            "ROD_PANEL_DARK": "#E0E0E0",
            "ROD_PANEL_LIGHT": "#FFFFFF",
            "ROD_RING_SILVER": "#B0B0B0",
            "ROD_RING_DARK": "#707070",
            "ROD_TEXT": "#333333",
            "ROD_TEXT_DIM": "#666666",
            "ROD_LCD_BG": "#EEEEEE",
            "ROD_LCD_FG": "#1A3A5C",
            "ROD_LCD_GLOW": "#4A90D9",
            "ROD_LED_GREEN": "#2E7D32",
            "ROD_LED_AMBER": "#F57C00",
            "ROD_LED_RED": "#C62828",
        },
        "CALMA": {
            "ROD_PANEL": "#E8F0E3",
            "ROD_PANEL_DARK": "#D0DBC8",
            "ROD_PANEL_LIGHT": "#F4F8F0",
            "ROD_RING_SILVER": "#A0A090",
            "ROD_RING_DARK": "#606050",
            "ROD_TEXT": "#3E3E2E",
            "ROD_TEXT_DIM": "#6B6B5A",
            "ROD_LCD_BG": "#F5F0E0",
            "ROD_LCD_FG": "#2E4A2E",
            "ROD_LCD_GLOW": "#7D9B6E",
            "ROD_LED_GREEN": "#558B2F",
            "ROD_LED_AMBER": "#D49A00",
            "ROD_LED_RED": "#B71C1C",
        },
        "N I STYLE": {
            "ROD_PANEL": "#1E1E1E",
            "ROD_PANEL_DARK": "#151515",
            "ROD_PANEL_LIGHT": "#2D2D2D",
            "ROD_RING_SILVER": "#3A3A3A",
            "ROD_RING_DARK": "#0A0A0A",
            "ROD_TEXT": "#CCCCCC",
            "ROD_TEXT_DIM": "#888888",
            "ROD_LCD_BG": "#0A0A0A",
            "ROD_LCD_FG": "#FF9933",
            "ROD_LCD_GLOW": "#FF6600",
            "ROD_LED_GREEN": "#33CC33",
            "ROD_LED_AMBER": "#FFAA00",
            "ROD_LED_RED": "#FF3333",
        },
    }

    # Seleccionar la paleta activa
    P = PALETAS.get(tema, PALETAS["ORIGINAL"])

    # --- Hoja de estilos (idéntica a la original, pero usando las variables de P) ---
    return f"""
    /* ================================================ */
    /* PANEL PRINCIPAL — chasis Rodec antracita        */
    /* ================================================ */
    QMainWindow, QWidget {{
        background-color: {P['ROD_PANEL']};
        color: {P['ROD_TEXT']};
        font-family: "Segoe UI", "Helvetica Neue", Arial;
        font-size: 11px;
    }}

    QLabel {{
        color: {P['ROD_TEXT']};
        font-weight: 500;
        letter-spacing: 0.5px;
    }}

    /* HEADERS (placa serigrafiada) */
    QLabel#maletaHeader {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {P['ROD_PANEL_LIGHT']},
                                    stop:1 {P['ROD_PANEL_DARK']});
        color: {P['ROD_LED_AMBER']};
        font-size: 17px;
        font-weight: bold;
        padding: 12px;
        border: 1px solid {P['ROD_RING_DARK']};
        border-radius: 3px;
        letter-spacing: 4px;
    }}

    /* DISPLAY LCD numérico — bajo cada knob */
    QLabel#timeLabel, QLabel.lcdSmall {{
        color: {P['ROD_LCD_FG']};
        background: {P['ROD_LCD_BG']};
        border: 1px solid {P['ROD_RING_DARK']};
        border-radius: 2px;
        padding: 3px 8px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 10px;
        font-weight: bold;
        min-width: 60px;
        letter-spacing: 1px;
    }}

    QLabel#conteoMaleta {{
        color: {P['ROD_LED_AMBER']};
        background: {P['ROD_LCD_BG']};
        border: 1px solid {P['ROD_RING_DARK']};
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
        background: {P['ROD_PANEL']};
        border-top: 2px solid {P['ROD_RING_SILVER']};
    }}
    QTabBar::tab {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {P['ROD_PANEL_LIGHT']},
                                    stop:1 {P['ROD_PANEL_DARK']});
        color: {P['ROD_TEXT_DIM']};
        padding: 11px 28px;
        font-weight: bold;
        letter-spacing: 3px;
        border: 1px solid {P['ROD_RING_DARK']};
        border-bottom: none;
    }}
    QTabBar::tab:selected {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {P['ROD_PANEL_LIGHT']},
                                    stop:1 {P['ROD_PANEL']});
        color: {P['ROD_LED_AMBER']};
        border-top: 2px solid {P['ROD_LED_AMBER']};
    }}
    QTabBar::tab:hover {{ color: {P['ROD_TEXT']}; }}

    /* ================================================ */
    /* GROUP BOXES — bloques serigrafiados             */
    /* ================================================ */
    QGroupBox {{
        border: 1px solid {P['ROD_RING_SILVER']};
        margin-top: 14px;
        padding-top: 10px;
        background: {P['ROD_PANEL_DARK']};
        border-radius: 3px;
        font-weight: bold;
        color: {P['ROD_LED_AMBER']};
        letter-spacing: 2px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
        background: {P['ROD_PANEL']};
    }}

    /* ================================================ */
    /* INPUTS                                          */
    /* ================================================ */
    QLineEdit {{
        background: {P['ROD_LCD_BG']};
        color: {P['ROD_LCD_FG']};
        border: 1px solid {P['ROD_RING_DARK']};
        border-radius: 2px;
        padding: 5px 8px;
        font-family: "Consolas", monospace;
        selection-background-color: {P['ROD_LED_AMBER']};
        selection-color: {P['ROD_PANEL_DARK']};
    }}
    QLineEdit#buscadorMaleta {{
        background: {P['ROD_LCD_BG']};
        color: {P['ROD_LCD_FG']};
        font-family: "Consolas", monospace;
        font-size: 12px;
        border: 1px solid {P['ROD_LCD_GLOW']};
        padding: 7px;
        letter-spacing: 1px;
    }}

    QComboBox {{
        background: {P['ROD_LCD_BG']};
        color: {P['ROD_LCD_FG']};
        border: 1px solid {P['ROD_RING_SILVER']};
        padding: 5px 8px;
        font-family: "Consolas", monospace;
    }}
    QComboBox::drop-down {{ border: none; width: 18px; }}
    QComboBox QAbstractItemView {{
        background: {P['ROD_LCD_BG']};
        color: {P['ROD_LCD_FG']};
        selection-background-color: {P['ROD_LED_AMBER']};
        selection-color: {P['ROD_PANEL_DARK']};
    }}

    /* ================================================ */
    /* BOTONES — pulsadores hardware                   */
    /* ================================================ */
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {P['ROD_PANEL_LIGHT']},
                                    stop:1 {P['ROD_PANEL_DARK']});
        color: {P['ROD_TEXT']};
        border: 1px solid {P['ROD_RING_SILVER']};
        border-radius: 2px;
        padding: 7px 14px;
        font-weight: bold;
        letter-spacing: 1px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #6a727b,
                                    stop:1 {P['ROD_PANEL']});
        color: {P['ROD_LED_AMBER']};
        border: 1px solid {P['ROD_TEXT']};
    }}
    QPushButton:pressed {{
        background: {P['ROD_PANEL_DARK']};
        color: {P['ROD_LED_GREEN']};
    }}
    QPushButton:checked {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #006633, stop:1 #003319);
        color: {P['ROD_LED_GREEN']};
        border: 1px solid {P['ROD_LED_GREEN']};
    }}
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
        background: {P['ROD_LCD_BG']};
        gridline-color: #1a3320;
        color: {P['ROD_LCD_FG']};
        font-family: "Consolas", "Courier New", monospace;
        font-size: 10px;
        selection-background-color: {P['ROD_LED_AMBER']};
        selection-color: {P['ROD_PANEL_DARK']};
        alternate-background-color: #0c1a14;
        border: 2px solid {P['ROD_RING_DARK']};
        border-radius: 3px;
    }}
    QTableWidget::item {{ padding: 4px; }}
    QHeaderView::section {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {P['ROD_PANEL_LIGHT']},
                                    stop:1 {P['ROD_PANEL_DARK']});
        color: {P['ROD_LED_AMBER']};
        padding: 7px;
        border: 1px solid {P['ROD_RING_DARK']};
        font-family: "Segoe UI", sans-serif;
        font-weight: bold;
        font-size: 10px;
        letter-spacing: 2px;
    }}

    /* ================================================ */
    /* TREE LATERAL — suministro físico                 */
    /* ================================================ */
    QTreeView {{
        background: {P['ROD_LCD_BG']};
        color: {P['ROD_LCD_FG']};
        border: 1px solid {P['ROD_RING_DARK']};
        font-family: "Consolas", monospace;
        selection-background-color: {P['ROD_LED_AMBER']};
        selection-color: {P['ROD_PANEL_DARK']};
        outline: 0;
    }}
    QTreeView::item:hover {{ background: #142820; }}

    /* ================================================ */
    /* SCROLLBARS — barras finas grafito                */
    /* ================================================ */
    QScrollBar:vertical {{
        background: {P['ROD_PANEL_DARK']};
        width: 10px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {P['ROD_RING_SILVER']};
        min-height: 25px;
        border-radius: 2px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {P['ROD_LED_AMBER']}; }}
    QScrollBar:horizontal {{
        background: {P['ROD_PANEL_DARK']};
        height: 10px; margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {P['ROD_RING_SILVER']};
        min-width: 25px;
        border-radius: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {P['ROD_LED_AMBER']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ background: none; border: none; }}

    /* ================================================ */
    /* MENUBAR / MENUS                                  */
    /* ================================================ */
    QMenuBar {{
        background: {P['ROD_PANEL_DARK']};
        color: {P['ROD_TEXT']};
        border-bottom: 1px solid {P['ROD_RING_DARK']};
        font-weight: bold;
        letter-spacing: 1px;
    }}
    QMenuBar::item:selected {{
        background: {P['ROD_PANEL_LIGHT']};
        color: {P['ROD_LED_AMBER']};
    }}
    QMenu {{
        background: {P['ROD_PANEL_DARK']};
        color: {P['ROD_TEXT']};
        border: 1px solid {P['ROD_RING_SILVER']};
    }}
    QMenu::item:selected {{
        background: {P['ROD_LED_AMBER']};
        color: {P['ROD_PANEL_DARK']};
    }}

    /* ================================================ */
    /* DIALOGOS / MESSAGEBOX / CHECKBOX                */
    /* ================================================ */
    QDialog, QMessageBox {{ background: {P['ROD_PANEL']}; }}
    QCheckBox {{ color: {P['ROD_TEXT']}; letter-spacing: 1px; }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {P['ROD_RING_SILVER']};
        background: {P['ROD_LCD_BG']};
    }}
    QCheckBox::indicator:checked {{
        background: {P['ROD_LED_GREEN']};
        border: 1px solid {P['ROD_LED_GREEN']};
    }}

    QProgressBar {{
        background: {P['ROD_LCD_BG']};
        color: {P['ROD_TEXT']};
        border: 1px solid {P['ROD_RING_SILVER']};
        text-align: center;
        font-family: "Consolas", monospace;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 {P['ROD_LED_GREEN']},
                                    stop:1 {P['ROD_LED_AMBER']});
    }}
    """