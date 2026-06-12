import sys
import os
import json
import csv
import threading
import librosa
import numpy as np
import sqlite3
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from genre_definitions import ESTILOS_UFULU
# --- SINCRONIZACIÓN CON EL ECOSISTEMA UFULU ---
import ufulu_style
import collection_manager
import tag_manager
import curaduria_engine
import widgets_ufulu
import playlist_exporters
from widgets_rodec import RodecKnob, RodecKnobSelector, RodecLCD, RodecFader
from audio_engine import EngineUfulu, detectar_segmentos_estructurales
# --- MODELO DE EXPLORACIÓN CON MEMORIA VISUAL ---
class UfuluFileModel(QFileSystemModel):
    def __init__(self, db): 
        super().__init__()
        self.db = db

    def data(self, index, role):
        if role == Qt.ItemDataRole.ForegroundRole:
            path = self.filePath(index)
            if not os.path.isdir(path):
                if self.db.track_exists(path):
                    return QColor("#00ffcc")
                else:
                    return QColor("#8899a6")
            else:
                if self.db.is_folder_complete(path):
                    return QColor("#FFFFFF")
                else:
                    return QColor("#8899a6")
        return super().data(index, role)

class MainApp(QMainWindow):
    # Señal para actualizar la interfaz desde el hilo de análisis
    analisis_completado = pyqtSignal(dict)
    analisis_progreso = pyqtSignal(int, int)  # (actual, total)

    def __init__(self, root_path, db):
        super().__init__()
        
        # --- ESTADO INTERNO DEL SISTEMA ---
        self.db = db
        self.carpeta_raiz = root_path
        self.todos_los_temas = []
        self.current_path = ""
        self.track_duration = 1.0
        self.current_zoom = 1
        self.cue_times = {i: None for i in range(1, 9)}
        self.armed_cue = None
        self.adn_actual = None
        self.current_playlist_data = []
        self.botones_perfil = []
        self._config_activa = {}  # Se cargará al pulsar un botón de perfil
        self._cargar_perfil(1)    # Cargar el perfil 1 por defecto
                # Valores por defecto de configuración
        self._confianza = 0.25
        self._duracion_muestreo = 60
        self._ventana_sondeo = 20
        self._umbral_open = 0.22
        self._umbral_hold = 0.28
        self._umbral_peak = 0.36
        self._tolerancia_armonica = 1
        self._densidad_default = "NORMAL"
        self._retencion_backups = 14
        self._frecuencia_backup = 1
        
        # --- APLICACIÓN DE PIEL RODEC BX-9 ---
        self.setStyleSheet(ufulu_style.get_ufulu_stylesheet())
        self.setWindowTitle(f"UFULU RODEC EDITION - {os.path.basename(root_path).upper()}")
        
        # --- LAYOUT PRINCIPAL DE LA CONSOLA ---
        cw = QWidget()
        self.setCentralWidget(cw)
        main_ly = QHBoxLayout(cw)
        main_ly.setContentsMargins(0, 0, 0, 0)
        main_ly.setSpacing(0)
        
        # --- MÓDULO LATERAL: SUMINISTRO ---
        sidebar = QWidget()
        sidebar.setFixedWidth(280)
        sidebar_ly = QVBoxLayout(sidebar)
        sidebar_ly.setContentsMargins(10, 10, 10, 10)
        
        self.model = UfuluFileModel(self.db)
        self.model.setRootPath(root_path)
        
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(root_path))
        for i in range(1, 4):
            self.tree.hideColumn(i)
        self.tree.doubleClicked.connect(self.on_folder_open)
        
        sidebar_ly.addWidget(QLabel("SUMINISTRO DE AUDIO"))
        sidebar_ly.addWidget(self.tree)
        main_ly.addWidget(sidebar)
        
        # --- RACK CENTRAL DE 3 MÓDULOS ---
        self.tabs = QTabWidget()
        main_ly.addWidget(self.tabs)
        
        self.tab_col = QWidget()
        self.tab_maleta = QWidget()
        self.tab_cur = QWidget()
        self.tab_config = QWidget()
        
        self.tabs.addTab(self.tab_col, "1. EL TALLER")
        self.tabs.addTab(self.tab_maleta, "2. MI MALETA")
        self.tabs.addTab(self.tab_cur, "3. CURADURÍA")
        self.tabs.addTab(self.tab_config, "4. CONFIG")
        self.init_coleccion_ui() 
        self.init_maleta_ui()    
        self.init_curaduria_ui()
        self.init_config_ui()
        
        self.tabs.currentChanged.connect(self.gestor_pestanas)

        # === INTEGRACIÓN v33.7 ===
        self._cur_player = QMediaPlayer()
        self._cur_audio_out = QAudioOutput()
        self._cur_player.setAudioOutput(self._cur_audio_out)

        # Conectar la señal de finalización del análisis
        self.analisis_completado.connect(self._actualizar_estilos)
        self.analisis_progreso.connect(self._actualizar_progreso)
        self._build_menu_v337()
        self._instalar_extensiones_v337()
    # =====================================================
    # MENU BAR v33.7
    # =====================================================
    def _build_menu_v337(self):
        mb = self.menuBar()
        m_tal = mb.addMenu("&TALLER")
        a_seg = m_tal.addAction("Auto-segmentar (Intro/Build/Drop/Break/Outro)")
        a_seg.setShortcut("Ctrl+T")
        a_seg.triggered.connect(self.auto_segmentar_handler)

        a_sug = m_tal.addAction("Sugerir siguiente tema")
        a_sug.setShortcut("Ctrl+N")
        a_sug.triggered.connect(self.sugerir_siguiente_handler)

        m_mal = mb.addMenu("&MALETA")
        m_mal.addAction("Salud de la maleta", self.abrir_diagnostico_salud).setShortcut("Ctrl+H")
        m_mal.addAction("Estadísticas (dashboard)", self.abrir_dashboard_estadisticas).setShortcut("Ctrl+E")

        m_cur = mb.addMenu("&CURADURÍA")
        m_cur.addAction("Generar plan de vuelo", self._v337_generar).setShortcut("Ctrl+G")
        m_cur.addSeparator()
        m_cur.addAction("Plantillas de sesión…", self.abrir_dialogo_templates)
        m_cur.addAction("Histórico + rating…", self.abrir_dialogo_historico)

        m_exp = mb.addMenu("&EXPORTAR")
        m_exp.addAction("Playlist M3U8", self.export_playlist_m3u8)
        m_exp.addAction("Traktor NML (con HotCues)", self.export_playlist_nml)
        m_exp.addAction("Rekordbox XML", self.export_playlist_xml)
        m_exp.addSeparator()
        m_exp.addAction("Informe PDF de sesión", self.export_playlist_pdf)
        m_exp.addAction("Inventario CSV", self.exportar_maleta_csv)

        m_h = mb.addMenu("&AYUDA")
        m_h.addAction("Acerca de Ufulu", self._about_v337)

    def _about_v337(self):
        QMessageBox.information(self, "UFULU · RODEC EDITION",
            "UFULU RODEC EDITION  ·  v33.7\n\n"
            "Consola forense de procesado analógico para DJs.\n"
            "Análisis BPM/Energía/Key + curaduría narrativa\n"
            "+ exportadores Traktor/Rekordbox/PDF.\n\n"
            "Atajos: Ctrl+1/2/3 cambian de pestaña.\n"
            "Ctrl+T auto-segmentar  ·  Ctrl+N sugerir\n"
            "Ctrl+H salud  ·  Ctrl+E stats  ·  Ctrl+G plan\n")

    # =====================================================
    # PLANTILLAS DE SESIÓN - HISTÓRICO
    # =====================================================
    def abrir_dialogo_templates(self):
        try:
            templates = self.db.listar_templates()
        except Exception as e:
            QMessageBox.critical(self, "PLANTILLAS", str(e)); return
        dlg = QDialog(self)
        dlg.setWindowTitle("PLANTILLAS DE SESIÓN")
        dlg.resize(560, 380)
        ly = QVBoxLayout(dlg)
        lst = QListWidget()
        for t in templates:
            lst.addItem(f"{t['name']}  ·  {t['luz']} / {t['momento']} / {t['estilo']} / {t['densidad']} / {t['duracion']} min")
        ly.addWidget(QLabel("PLANTILLAS GUARDADAS:"))
        ly.addWidget(lst)
        btns = QHBoxLayout()
        b_load = QPushButton("CARGAR EN CURADURÍA")
        b_save = QPushButton("GUARDAR ACTUAL COMO…")
        b_del  = QPushButton("BORRAR")
        b_close = QPushButton("CERRAR")
        for b in (b_load, b_save, b_del, b_close):
            btns.addWidget(b)
        ly.addLayout(btns)

        def cargar():
            row = lst.currentRow()
            if row < 0 or row >= len(templates): return
            t = templates[row]
            self.cb_luz.setCurrentText(t["luz"])
            self.cb_mom.setCurrentText(t["momento"])
            self.cb_estilo_cur.setCurrentText(t["estilo"])
            self.cb_den.setCurrentText(t["densidad"])
            self.in_dur.setText(str(t["duracion"]))
            self.tabs.setCurrentIndex(2)
            dlg.accept()

        def guardar():
            name, ok = QInputDialog.getText(dlg, "NOMBRE PLANTILLA", "Nombre:")
            if not ok or not name.strip(): return
            self.db.guardar_template(name.strip(),
                                     self.cb_luz.currentText(), self.cb_mom.currentText(),
                                     self.cb_estilo_cur.currentText(),
                                     self.cb_den.currentText(), self.in_dur.text())
            QMessageBox.information(dlg, "PLANTILLA", f"Plantilla '{name}' guardada.")
            dlg.accept()

        def borrar():
            row = lst.currentRow()
            if row < 0 or row >= len(templates): return
            self.db.borrar_template(templates[row]["name"])
            QMessageBox.information(dlg, "PLANTILLA", "Borrada.")
            dlg.accept()

        b_load.clicked.connect(cargar)
        b_save.clicked.connect(guardar)
        b_del.clicked.connect(borrar)
        b_close.clicked.connect(dlg.reject)
        dlg.exec()


    def abrir_dialogo_historico(self):
        try:
            hist = self.db.listar_historial(50)
        except Exception as e:
            QMessageBox.critical(self, "HISTÓRICO", str(e)); return
        if not hist:
            QMessageBox.information(self, "HISTÓRICO", "Sin sesiones registradas.")
            return
        msg = "ÚLTIMAS SESIONES:\n\n"
        for h in hist[:20]:
            stars = "★" * int(h.get("rating") or 0)
            msg += f"#{h['id']}  {h['timestamp']}  {stars}\n"
            try:
                p = json.loads(h.get("params") or "{}")
                msg += (f"   {p.get('luz','-')} / {p.get('momento','-')} / "
                        f"{p.get('estilo','-')} / {p.get('duracion','-')} min\n")
            except Exception: pass
            if h.get("notas_sesion"):
                msg += f"   ✎ {h['notas_sesion'][:90]}\n"
            msg += "\n"
        QMessageBox.information(self, "HISTÓRICO", msg)
    def _actualizar_progreso(self, actual, total):
        """Actualiza la barra de progreso y el texto de los botones."""
        if hasattr(self, 'progress_ia'):
            self.progress_ia.setMaximum(total)
            self.progress_ia.setValue(actual)
        texto = f"ANALIZANDO... ({actual}/{total})"
       
        if hasattr(self, 'btn_analizar_toda_maleta') and not self.btn_analizar_toda_maleta.isEnabled():
            self.btn_analizar_toda_maleta.setText(texto)
    # ------------------------------------------------------------
    # MÓDULO 1: EL TALLER (con análisis de estilos IA)
    # ------------------------------------------------------------
    
    def _guardar_conf_umbral(self, val):
        self._confianza = val / 100.0
    def _guardar_conf_duracion(self, val):
        self._duracion_muestreo = val
    def _guardar_conf_ventana(self, val):
        self._ventana_sondeo = val
    def _guardar_conf_open(self, val):
        self._umbral_open = val / 100.0
    def _guardar_conf_hold(self, val):
        self._umbral_hold = val / 100.0
    def _guardar_conf_peak(self, val):
        self._umbral_peak = val / 100.0
    def _guardar_conf_tolerancia(self, idx):
        self._tolerancia_armonica = idx
    def _guardar_conf_densidad(self, txt):
        self._densidad_default = txt
    def _guardar_conf_ret_backup(self, val):
        self._retencion_backups = val
    def _guardar_conf_freq_backup(self, val):
        self._frecuencia_backup = val
    def init_coleccion_ui(self):
        ly = QVBoxLayout(self.tab_col)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(15)
        
        self.lbl_maleta = QLabel(os.path.basename(self.carpeta_raiz).upper())
        self.lbl_maleta.setObjectName("maletaHeader")
        self.lbl_maleta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly.addWidget(self.lbl_maleta)

                # --- PANEL DE ACCIONES MASIVAS ---
        btns_top = QHBoxLayout()



        self.btn_save_all = QPushButton("FIJAR ADN SELECCIONADOS")
        self.btn_sel_all = QPushButton("MARCAR TODOS")
        self.btn_save_all.setObjectName("injectBtn")
        self.btn_save_all.clicked.connect(self.save_selected)
        self.btn_sel_all.clicked.connect(self.toggle_all)
       

        btns_top.addStretch()
        btns_top.addWidget(self.btn_sel_all)
        btns_top.addWidget(self.btn_save_all)
       
       
        ly.addLayout(btns_top)
        self.tabla = QTableWidget(0, 8)
        self.tabla.setHorizontalHeaderLabels([
            "", "NOMBRE TEMA", "BPM TAG", "BPM UFULU", 
            "FUNCIÓN", "ENERGÍA", "ESTILO", "ESTADO"
        ])
        
        self.tabla.setSortingEnabled(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(0, 40)
        self.tabla.itemClicked.connect(self.load_q)
        self.tabla.cellChanged.connect(self.on_tabla_cell_changed)
        ly.addWidget(self.tabla)
        
        self.grp_q = QGroupBox("QUIRÓFANO ANALÓGICO")
        self.grp_q.setFixedHeight(500)
        ly_q = QVBoxLayout(self.grp_q)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:#050505; border: 1px solid #555;")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view_onda = QLabel()
        self.view_onda.mousePressEvent = self.on_waveform_click
        self.scroll.setWidget(self.view_onda)
        ly_q.addWidget(self.scroll)
        
        ctrls_ly = QHBoxLayout()
        self.btn_rms = QPushButton("VISTA ENVOLVENTE")
        self.btn_stab = QPushButton("VISTA RÍTMICA")
        self.btn_rms.setCheckable(True)
        self.btn_stab.setCheckable(True)
        self.btn_rms.clicked.connect(self.refresh_visuals)
        self.btn_stab.clicked.connect(self.refresh_visuals)
        for z in [1, 2, 4]:
            b = QPushButton(f"ZOOM {z}X")
            b.setFixedWidth(70)
            b.clicked.connect(lambda chk, v=z: self.change_zoom(v))
            ctrls_ly.addWidget(b)
        ctrls_ly.addStretch()
        ctrls_ly.addWidget(self.btn_rms)
        ctrls_ly.addWidget(self.btn_stab)
        ly_q.addLayout(ctrls_ly)
        
        knobs_ly = QHBoxLayout()
        self.dials = []
        for i in range(3):
            v_box = QVBoxLayout()
            d = RodecKnob(style="red")
            d.setRange(0, 60000 * 4)  # Suficiente resolución incluso a x4
            d.setFixedSize(85, 85)
            d.wheelEvent = lambda e, dial=d: dial.setValue(dial.value() + ( (10 // self.current_zoom) 
               if e.angleDelta().y() > 0 else -(10 // self.current_zoom) ))
            d.valueChanged.connect(self.refresh_visuals)
            l = QLabel("00:00:00")
            l.setObjectName("timeLabel")
            v_box.addWidget(l, 0, Qt.AlignmentFlag.AlignCenter)
            v_box.addWidget(d)
            knobs_ly.addLayout(v_box)
            self.dials.append((d, l))
        
        self.btn_re = QPushButton("RE-TRIANGULAR")
        self.btn_inj = QPushButton("FIJAR ADN ACTUAL")
        self.btn_inj.setObjectName("injectBtn")
        self.btn_re.clicked.connect(self.run_triangulation)
        self.btn_inj.clicked.connect(self.inject_current)
        knobs_ly.addSpacing(30)
        knobs_ly.addWidget(self.btn_re)
        knobs_ly.addWidget(self.btn_inj)
        ly_q.addLayout(knobs_ly)
        
        cues_ly = QHBoxLayout()
        self.cue_btns = []
        for i in range(1, 9):
            b = QPushButton(f"M{i}")
            b.setFixedWidth(55)
            b.clicked.connect(lambda chk, n=i: self.asignar_cue_logic(n))
            cues_ly.addWidget(b)
            self.cue_btns.append(b)
        ly_q.addLayout(cues_ly)
        ly.addWidget(self.grp_q)

    # ------------------------------------------------------------
    # MÓDULO 2: MI MALETA
    # ------------------------------------------------------------
    def init_maleta_ui(self):
        ly = QVBoxLayout(self.tab_maleta)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(15)
        search_ly = QHBoxLayout()
        self.in_busq = QLineEdit()
        self.in_busq.setObjectName("buscadorMaleta")
        self.in_busq.setPlaceholderText("BUSCAR POR NOMBRE, BPM, FUNCIÓN O ESTILO...")
        self.in_busq.textChanged.connect(self.filtrar_maleta)
        self.lbl_count_maleta = QLabel("0 TEMAS EN STOCK ANALIZADO")
        self.lbl_count_maleta.setObjectName("conteoMaleta")
        self.btn_exp = QPushButton("EXPORTAR INVENTARIO (.CSV)")
        self.btn_exp.setFixedWidth(220)
        self.btn_exp.clicked.connect(self.exportar_maleta_csv)
        search_ly.addWidget(QLabel("DISPLAY BÚSQUEDA:"))
        search_ly.addWidget(self.in_busq, 5)
        search_ly.addSpacing(20)
        search_ly.addWidget(self.lbl_count_maleta)
        search_ly.addWidget(self.btn_exp)
        ly.addLayout(search_ly)
                # --- Botones de acciones globales (IA + Refinar) ---
        btns_globales = QHBoxLayout()
        self.btn_analizar_estilos = QPushButton("ANALIZAR ESTILOS (AI)")
        self.btn_analizar_estilos.clicked.connect(lambda: self._ejecutar_analisis([r[5] for r in self.db.get_inventory_full() if len(r) > 5]))
        self.btn_analizar_toda_maleta = QPushButton("ANALIZAR TODA LA MALETA (AI)")
        self.btn_analizar_toda_maleta.clicked.connect(lambda: self._ejecutar_analisis([r[5] for r in self.db.get_inventory_full() if len(r) > 5]))
        self.progress_ia = QProgressBar()
        self.progress_ia.setVisible(False)
        self.progress_ia.setStyleSheet("QProgressBar { border: 1px solid #555; background: #111; text-align: center; color: #0cf; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0cf, stop:1 #0f6); }")
        btns_globales.addWidget(self.btn_analizar_estilos)
        btns_globales.addWidget(self.btn_analizar_toda_maleta)
        btns_globales.addWidget(self.progress_ia)
        ly.addLayout(btns_globales)
        self.tabla_maleta = QTableWidget(0, 6)
        self.tabla_maleta.setHorizontalHeaderLabels([
            "NOMBRE TEMA", "BPM", "FUNCIÓN", "ILUMINACIÓN", "ESTILO", "UBICACIÓN FÍSICA"
        ])
        self.tabla_maleta.setSortingEnabled(True)  # Mantener desactivado
        self.tabla_maleta.doubleClicked.connect(self.cargar_desde_maleta_al_taller)
        ly.addWidget(self.tabla_maleta)
        footer_info = QLabel("SISTEMA CENTRALIZADO: LOS DATOS SE ALIMENTAN DE TU HISTÓRICO DE ANÁLISIS")
        footer_info.setStyleSheet("color: #8899a6; font-size: 9px; font-style: italic;")
        footer_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly.addWidget(footer_info)

    def init_config_ui(self):
        ly = QVBoxLayout(self.tab_config)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(15)

 
        # --- 1. TEMA VISUAL ---
        grp_tema = QGroupBox("TEMA VISUAL")
        ly_tema = QHBoxLayout(grp_tema)
        ly_tema.addWidget(QLabel("Estética de la consola:"))
        
        self.botones_tema = []
        for nombre in ["ORIGINAL", "ORDEN", "CALMA", "N I STYLE"]:
            btn = QPushButton(nombre)
            btn.setFixedHeight(28)
            btn.setFixedWidth(100)
            btn.setCheckable(True)
            btn.clicked.connect(lambda chk, t=nombre: self._cambiar_tema(t))
            if nombre == "ORIGINAL":
                btn.setChecked(True)
                btn.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3F566B, stop:1 #1E2A36); color: white; border: 1px solid #D6D2C4; border-radius: 3px; font-weight: bold; }")
            else:
                btn.setStyleSheet("QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a626b, stop:1 #384048); color: #8E98A3; border: 1px solid #7A6B3A; border-radius: 3px; font-weight: bold; } QPushButton:checked { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3F566B, stop:1 #1E2A36); color: white; border: 1px solid #D6D2C4; }")
            ly_tema.addWidget(btn)
            self.botones_tema.append(btn)
        ly_tema.addStretch()
        ly.addWidget(grp_tema)
            # --- 2. PERFILES DE CURADURÍA ---
        grp_perfiles = QGroupBox("PERFILES DE CURADURÍA")
        ly_perfiles_v = QVBoxLayout(grp_perfiles)

        # Selector de perfil (arriba centrado)
        self.sel_perfil_editar = RodecKnobSelector(["1", "2", "3", "4"], style="cyan", size=48)
        self.sel_perfil_editar.setCurrentIndex(0)
        self.sel_perfil_editar.currentIndexChanged.connect(self._cargar_perfil_edicion)
        ly_perfiles_v.addWidget(self.sel_perfil_editar, 0, Qt.AlignmentFlag.AlignCenter)

        # Grid de dos columnas para los 4 controles principales
        grid_cur = QGridLayout()
        grid_cur.setColumnStretch(0, 1)
        grid_cur.setColumnStretch(1, 1)

        # Función auxiliar para crear un panel de control (knob + valor + descripción)
        def crear_panel_selector(titulo, items, estilo, conexion_guardado, descripcion):
            panel = QHBoxLayout()
            knob = RodecKnobSelector(items, style=estilo, size=58)
            knob.setCurrentText(titulo)
            knob.currentTextChanged.connect(conexion_guardado)
            info_ly = QVBoxLayout()
            lbl_valor = QLabel(titulo)
            lbl_valor.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_valor.setStyleSheet("color: #ecedee; font-family: Consolas; font-size: 9px;")
            lbl_desc = QLabel(descripcion)
            lbl_desc.setStyleSheet("color: #8E98A3; font-size: 10px; font-style: italic;")
            lbl_desc.setWordWrap(True)
            info_ly.addWidget(lbl_valor)
            info_ly.addWidget(lbl_desc)
            panel.addWidget(knob)
            panel.addLayout(info_ly)
            return panel, knob

        # ILUMINACIÓN
        panel_luz, self.cb_luz_conf = crear_panel_selector(
            "DÍA", ["AMBOS", "DÍA", "NOCHE"], "amber",
            self._guardar_perfil_actual, "Luz: DÍA / NOCHE / AMBOS"
        )
        # MOMENTO
        panel_mom, self.cb_mom_conf = crear_panel_selector(
            "WARM-UP (APERTURA)", ["WARM-UP (APERTURA)", "PEAK (CÉNIT)", "CLOSING (CIERRE)"],
            "red", self._guardar_perfil_actual, "Arco narrativo de la sesión"
        )
        # ESTILO BASE
        panel_estilo, self.cb_estilo_conf = crear_panel_selector(
            "TODOS", ["TODOS"] + ESTILOS_UFULU,
            "cyan", self._guardar_perfil_actual, "Filtro de estilo base"
        )
        # DENSIDAD
        panel_den, self.cb_den_conf = crear_panel_selector(
            "NORMAL", ["NORMAL", "RÁPIDA", "LARGA"],
            "green", self._guardar_perfil_actual, "Densidad de mezcla"
        )

        # Colocar en grid: fila 0 col 0 -> luz, col 1 -> momento; fila 1 -> estilo, densidad
        grid_cur.addLayout(panel_luz, 0, 0)
        grid_cur.addLayout(panel_mom, 0, 1)
        grid_cur.addLayout(panel_estilo, 1, 0)
        grid_cur.addLayout(panel_den, 1, 1)

        # Duración (abajo centrado)
        dur_ly = QHBoxLayout()
        dur_ly.addWidget(QLabel("DURACIÓN (MIN):"))
        self.in_dur_conf = QLineEdit("90")
        self.in_dur_conf.setFixedWidth(60)
        self.in_dur_conf.setObjectName("lcdSmall")
        self.in_dur_conf.editingFinished.connect(self._guardar_perfil_actual)
        dur_ly.addWidget(self.in_dur_conf)
        dur_ly.addStretch()
        grid_cur.addLayout(dur_ly, 2, 0, 1, 2)

        ly_perfiles_v.addLayout(grid_cur)
        ly.addWidget(grp_perfiles)
      
           # --- 4. ANÁLISIS FORENSE ---
        grp_forense = QGroupBox("ANÁLISIS FORENSE")
        ly_forense = QHBoxLayout(grp_forense)
        ly_forense.setSpacing(20)

        # Función auxiliar para crear un panel de knob con info
        def crear_panel_knob(titulo, estilo, rango, valor_inicial, conexion, desc_texto):
            panel = QHBoxLayout()
            knob = RodecKnob(style=estilo)
            knob.setRange(rango[0], rango[1]); knob.setSingleStep(1); knob.setPageStep(1)
            knob.setValue(valor_inicial)
            knob.valueChanged.connect(conexion)
            lbl_val = QLabel(f"{valor_inicial/100:.2f}" if rango[0] == 10 else f"{valor_inicial}")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_val.setStyleSheet("color: #ecedee; font-family: Consolas; font-size: 9px;")
            knob.valueChanged.connect(lambda v, l=lbl_val: l.setText(f"{v/100:.2f}" if rango[0] == 10 else f"{v}"))
            info = QVBoxLayout()
            info.addWidget(QLabel(titulo))
            info.addWidget(lbl_val)
            desc = QLabel(desc_texto)
            desc.setStyleSheet("color: #8E98A3; font-size: 10px; font-style: italic;"); desc.setWordWrap(True)
            info.addWidget(desc)
            panel.addWidget(knob)
            panel.addLayout(info)
            return panel, knob

        # Panel Ventana BPM (fader)
        panel_ventana = QHBoxLayout()
        self.fader_conf_ventana = RodecFader(10, 30, style="amber")
        self.fader_conf_ventana.setValue(self._ventana_sondeo)
        self.fader_conf_ventana.valueChanged.connect(self._guardar_conf_ventana)
        self.fader_conf_ventana.valueChanged.connect(lambda v: self.lbl_conf_ventana.setText(f"{v} s"))
        self.lbl_conf_ventana = QLabel(f"{self._ventana_sondeo} s")
        self.lbl_conf_ventana.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_conf_ventana.setStyleSheet("color: #ecedee; font-family: Consolas; font-size: 9px;")
        desc_ventana = QLabel("Segundos que escucha el motor para calcular el tempo.")
        desc_ventana.setStyleSheet("color: #8E98A3; font-size: 10px; font-style: italic;"); desc_ventana.setWordWrap(True)
        info_ventana = QVBoxLayout()
        info_ventana.addWidget(QLabel("Ventana BPM"))
        info_ventana.addWidget(self.lbl_conf_ventana)
        info_ventana.addWidget(desc_ventana)
        panel_ventana.addWidget(self.fader_conf_ventana)
        panel_ventana.addLayout(info_ventana)

        # Paneles de knobs (OPEN, HOLD, PEAK)
        panel_open, self.knob_conf_open = crear_panel_knob(
            "Umbral OPEN", "green", (10, 40), int(self._umbral_open * 100),
            self._guardar_conf_open, "Presión máxima para que un tema sea considerado 'apertura'."
        )
        panel_hold, self.knob_conf_hold = crear_panel_knob(
            "Umbral HOLD", "green", (10, 40), int(self._umbral_hold * 100),
            self._guardar_conf_hold, "Presión máxima para que un tema sea considerado 'mantenimiento'."
        )
        panel_peak, self.knob_conf_peak = crear_panel_knob(
            "Umbral PEAK", "red", (20, 60), int(self._umbral_peak * 100),
            self._guardar_conf_peak, "Presión mínima para que un tema sea considerado 'clímax'."
        )

        # Añadir todos los paneles al layout horizontal
        ly_forense.addLayout(panel_ventana)
        ly_forense.addLayout(panel_open)
        ly_forense.addLayout(panel_hold)
        ly_forense.addLayout(panel_peak)
        ly.addWidget(grp_forense)
         
                # --- 5. BASE DE DATOS ---
        grp_db = QGroupBox("BASE DE DATOS")
        ly_db = QHBoxLayout(grp_db)
        ly_db.setSpacing(30)

        # Función auxiliar para crear un panel de fader con info
        def crear_panel_fader(titulo, estilo, rango, valor_inicial, conexion, desc_texto):
            panel = QHBoxLayout()
            fader = RodecFader(rango[0], rango[1], style=estilo)
            fader.setValue(valor_inicial)
            fader.valueChanged.connect(conexion)
            lbl_val = QLabel(f"{valor_inicial} días")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_val.setStyleSheet("color: #ecedee; font-family: Consolas; font-size: 9px;")
            fader.valueChanged.connect(lambda v, l=lbl_val: l.setText(f"{v} días"))
            info = QVBoxLayout()
            info.addWidget(QLabel(titulo))
            info.addWidget(lbl_val)
            desc = QLabel(desc_texto)
            desc.setStyleSheet("color: #8E98A3; font-size: 10px; font-style: italic;"); desc.setWordWrap(True)
            info.addWidget(desc)
            panel.addWidget(fader)
            panel.addLayout(info)
            return panel, fader

        panel_ret, self.fader_conf_ret_backup = crear_panel_fader(
            "Retención backups", "white", (7, 90), self._retencion_backups,
            self._guardar_conf_ret_backup, "Días que se conservan las copias de seguridad de la base de datos."
        )
        panel_freq, self.fader_conf_freq_backup = crear_panel_fader(
            "Frecuencia backup", "white", (1, 30), self._frecuencia_backup,
            self._guardar_conf_freq_backup, "Cada cuántos días se crea una nueva copia de seguridad."
        )

        ly_db.addLayout(panel_ret)
        ly_db.addLayout(panel_freq)
        ly.addWidget(grp_db)
        ly.addStretch()
   
    def refrescar_maleta_tabla(self):
        try:
            data = self.db.get_inventory_full()
            if not data:
                self.tabla_maleta.setRowCount(0)
                self.lbl_count_maleta.setText("0 TEMAS EN STOCK")
                return

            self.tabla_maleta.blockSignals(True)
            self.tabla_maleta.clearContents()
            self.tabla_maleta.setRowCount(0)

            fuente = QFont("Segoe UI", 10)
            color_texto = QColor("#f0f0f0")
            color_fondo = QColor("#1e1e1e")

            for fila, pista in enumerate(data):
                self.tabla_maleta.insertRow(fila)
                nombre, bpm, funcion, iluminacion, estilo, ruta = pista[:6]

                valores = [
                    str(nombre),
                    str(bpm),
                    str(funcion).replace("-", "—"),
                    str(iluminacion).replace("NOCHE", "🌙").replace("DÍA", "☀️"),
                    str(estilo),
                    os.path.basename(str(ruta))
                ]

                for col, texto in enumerate(valores):
                    item = QTableWidgetItem(texto)
                    item.setFont(fuente)
                    item.setForeground(color_texto)
                    item.setBackground(color_fondo)
                    flags = item.flags() & ~Qt.ItemFlag.ItemIsEditable
                    item.setFlags(flags)
                    if col == 5:
                        item.setData(Qt.ItemDataRole.UserRole, ruta)
                    self.tabla_maleta.setItem(fila, col, item)

            # Permitir que la tabla se expanda a todo el ancho disponible
            for col, ancho_min in enumerate([100, 50, 60, 60, 80, 100]):
                self.tabla_maleta.horizontalHeader().setMinimumSectionSize(ancho_min)
            self.tabla_maleta.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

            for i in range(self.tabla_maleta.rowCount()):
                self.tabla_maleta.setRowHidden(i, False)

            self.in_busq.clear()
            self.lbl_count_maleta.setText(f"{len(data)} TEMAS EN STOCK")
            print(f">>> Maleta sincronizada: {len(data)} registros cargados.")

        except Exception as e:
            print(f"Error de sincronización en maleta: {e}")
        finally:
            self.tabla_maleta.blockSignals(False)

    def filtrar_maleta(self, texto):
        t = texto.upper()
        for i in range(self.tabla_maleta.rowCount()):
            match = False
            for j in range(self.tabla_maleta.columnCount()):
                item = self.tabla_maleta.item(i, j)
                if item is not None and t in item.text().upper():
                    match = True
                    break
    
            self.tabla_maleta.setRowHidden(i, not match)
    
    def _cambiar_tema(self, tema: str):
        """Aplica el tema visual y resalta el botón activo."""
        nueva_piel = ufulu_style.get_ufulu_stylesheet(tema)
        self.setStyleSheet(nueva_piel)
        for btn in self.botones_tema:
            if btn.text() == tema:
                btn.setChecked(True)
                btn.setStyleSheet(
                    "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3F566B, stop:1 #1E2A36); "
                    "color: white; border: 1px solid #D6D2C4; border-radius: 3px; font-weight: bold; }"
                )
            else:
                btn.setChecked(False)
                btn.setStyleSheet(
                    "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5a626b, stop:1 #384048); "
                    "color: #8E98A3; border: 1px solid #7A6B3A; border-radius: 3px; font-weight: bold; }"
                )
        print(f"[TEMA] Cambiado a {tema}")
        # ------------------------------------------------------------
    # MÓDULO 3: CURADURÍA
    # ------------------------------------------------------------
    def init_curaduria_ui(self):
        ly = QVBoxLayout(self.tab_cur)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(15)

        # --- SECCIÓN DE PERFILES ---
        grp_perfiles = QGroupBox("CONFIGURACIÓN DE SESIÓN")
        ly_perfiles = QHBoxLayout(grp_perfiles)

        self.botones_perfil = []
        for i in range(1, 5):
            btn = QPushButton(f"PERFIL {i}")
            btn.setObjectName("injectBtn")
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda chk, n=i: self._cargar_perfil(n))
            ly_perfiles.addWidget(btn)
            self.botones_perfil.append(btn)

        ly.addWidget(grp_perfiles)

        # --- OPCIONES ADICIONALES ---
        opciones_ly = QHBoxLayout()
        self.chk_semilla = QCheckBox("USAR TEMA ACTUAL COMO SEMILLA")
        self.in_dur = QLineEdit("90")
        self.in_dur.setFixedWidth(60)
        self.in_dur.setObjectName("lcdSmall")
        opciones_ly.addWidget(QLabel("DURACIÓN (MIN):"))
        opciones_ly.addWidget(self.in_dur)
        opciones_ly.addStretch()
        opciones_ly.addWidget(self.chk_semilla)
        ly.addLayout(opciones_ly)

        # --- BOTÓN DE GENERAR ---
        self.btn_gen = QPushButton("GENERAR PLAN DE VUELO")
        self.btn_gen.setObjectName("injectBtn")
        self.btn_gen.setFixedHeight(45)
        self.btn_gen.clicked.connect(self.run_curaduria_feedback)
        ly.addWidget(self.btn_gen)

        # --- WIDGETS OCULTOS PARA COMPATIBILIDAD (usados por diálogo de plantillas y exportación) ---
        self.cb_luz = QComboBox()
        self.cb_luz.addItems(["AMBOS", "DÍA", "NOCHE"])
        self.cb_luz.setCurrentText("DÍA")
        self.cb_luz.setVisible(False)
        ly.addWidget(self.cb_luz)

        self.cb_mom = QComboBox()
        self.cb_mom.addItems(["WARM-UP (APERTURA)", "PEAK (CÉNIT)", "CLOSING (CIERRE)"])
        self.cb_mom.setCurrentText("WARM-UP (APERTURA)")
        self.cb_mom.setVisible(False)
        ly.addWidget(self.cb_mom)

        self.cb_estilo_cur = QComboBox()
        self.cb_estilo_cur.addItems(["TODOS"] + ESTILOS_UFULU)
        self.cb_estilo_cur.setCurrentText("TODOS")
        self.cb_estilo_cur.setVisible(False)
        ly.addWidget(self.cb_estilo_cur)

        self.cb_den = QComboBox()
        self.cb_den.addItems(["NORMAL", "RÁPIDA", "LARGA"])
        self.cb_den.setCurrentText("NORMAL")
        self.cb_den.setVisible(False)
        ly.addWidget(self.cb_den)

        # --- TABLA DE RESULTADOS ---
        self.tabla_cur = QTableWidget(0, 5)
        self.tabla_cur.setHorizontalHeaderLabels(["INICIO", "ACTO", "TRACK", "BPM / KEY", "MOTIVO TÉCNICO"])
        self.tabla_cur.setSortingEnabled(False)
        for col, ancho_min in enumerate([60, 100, 180, 80, 120]):
            self.tabla_cur.horizontalHeader().setMinimumSectionSize(ancho_min)
        self.tabla_cur.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_cur.horizontalHeader().setStretchLastSection(False)
        ly.addWidget(self.tabla_cur)

        # --- BOTÓN DE EXPORTAR ---
        self.btn_exp_plan = QPushButton("EXPORTAR GUÍA DE CABINA (.TXT)")
        self.btn_exp_plan.clicked.connect(self.export_guia_txt)
        ly.addWidget(self.btn_exp_plan)
    def run_curaduria_feedback(self):
        self.btn_gen.setText("PROCESANDO NARRATIVA..."); self.btn_gen.setEnabled(False)
        QTimer.singleShot(100, self.run_curaduria)

    def run_curaduria(self):
        try:
            pool = self.db.get_inventory_full()
            if not pool or len(pool) < 5:
                QMessageBox.warning(self, "CURADURÍA", "STOCK INSUFICIENTE.")
                self.btn_gen.setText("GENERAR PLAN DE VUELO"); self.btn_gen.setEnabled(True)
                return

            # Usar la configuración activa en lugar de los selectores
            cfg = self._config_activa
            config = {
                'luz': cfg.get('luz', 'DÍA'),
                'duracion': cfg.get('duracion', '90'),
                'densidad': cfg.get('densidad', 'NORMAL'),
                'momento': cfg.get('momento', 'WARM-UP (APERTURA)'),
                'estilo': cfg.get('estilo', 'TODOS'),
                'estilos_lista': cfg.get('estilos_lista', ['TODOS']),
                'usar_semilla': self.chk_semilla.isChecked(),
                'semilla': self.current_path
            }

            self.current_playlist_data = curaduria_engine.generar_sesion_ufulu(pool, config)

            self.tabla_cur.setRowCount(0)
            fuente_item = QFont("Segoe UI", 10)

            for item in self.current_playlist_data:
                r = self.tabla_cur.rowCount()
                self.tabla_cur.insertRow(r)
                d_track = item['data']

                valores = [
                    item['tiempo'],
                    item['acto'],
                    os.path.basename(str(d_track[0])),
                    f"{d_track[1]} BPM",
                    item['motivo']
                ]

                for col, val in enumerate(valores):
                    it = QTableWidgetItem(str(val))
                    it.setFont(fuente_item)
                    it.setForeground(QColor("#f0f0f0"))
                    it.setBackground(QColor("#1e1e1e"))
                    flags = it.flags() & ~Qt.ItemFlag.ItemIsEditable
                    it.setFlags(flags)
                    self.tabla_cur.setItem(r, col, it)

            for i in range(self.tabla_cur.rowCount()):
                self.tabla_cur.setRowHidden(i, False)

            print(f"Plan generado con {self.tabla_cur.rowCount()} filas")

        except Exception as e:
            print(f"Fallo en motor narrativo: {e}")
        finally:
            self.btn_gen.setText("GENERAR PLAN DE VUELO")
            self.btn_gen.setEnabled(True)
    
    def _cargar_perfil(self, numero):
        """Carga el perfil de curaduría desde el JSON y actualiza la configuración activa."""
        perfil_path = os.path.join(os.path.dirname(__file__), "curaduria_profiles.json")
        
        # Crear archivo con valores por defecto si no existe
        if not os.path.exists(perfil_path):
            default_profiles = {
                "1": {"luz": "DÍA", "momento": "WARM-UP (APERTURA)", "densidad": "NORMAL", "estilo": "Kwaito Amapiano", "duracion": "90"},
                "2": {"luz": "NOCHE", "momento": "PEAK (CÉNIT)", "densidad": "RÁPIDA", "estilo": "Sgubhu", "duracion": "60"},
                "3": {"luz": "DÍA", "momento": "CLOSING (CIERRE)", "densidad": "LARGA", "estilo": "Bacardi", "duracion": "120"},
                "4": {"luz": "AMBOS", "momento": "WARM-UP (APERTURA)", "densidad": "NORMAL", "estilo": "TODOS", "duracion": "90"}
            }
            with open(perfil_path, "w", encoding="utf-8") as f:
                json.dump(default_profiles, f, indent=2)
        
        with open(perfil_path, "r", encoding="utf-8") as f:
            perfiles = json.load(f)
        
        self._config_activa = perfiles.get(str(numero), perfiles.get("1", {}))
        
        # Resaltar el botón activo
        for i, btn in enumerate(self.botones_perfil):
            if i == numero - 1:
                btn.setStyleSheet("background:#00ffcc; color:#000; font-weight:bold;")
            else:
                btn.setStyleSheet("")
        
        print(f"[CURADURÍA] Perfil {numero} cargado: {self._config_activa}")
    def _cargar_perfil_edicion(self, idx):
        """Carga los valores del perfil seleccionado en los selectores de edición."""
        numero = str(idx + 1)  # idx va de 0 a 3
        perfil_path = os.path.join(os.path.dirname(__file__), "curaduria_profiles.json")
        if os.path.exists(perfil_path):
            with open(perfil_path, "r", encoding="utf-8") as f:
                perfiles = json.load(f)
            perfil = perfiles.get(numero, {})
            self.cb_luz_conf.setCurrentText(perfil.get("luz", "DÍA"))
            self.cb_mom_conf.setCurrentText(perfil.get("momento", "WARM-UP (APERTURA)"))
            self.cb_den_conf.setCurrentText(perfil.get("densidad", "NORMAL"))
            self.cb_estilo_conf.setCurrentText(perfil.get("estilo", "TODOS"))
            self.in_dur_conf.setText(perfil.get("duracion", "90"))

    def _guardar_perfil_actual(self):
        """Guarda los valores actuales de los selectores en el perfil activo."""
        numero = str(self.sel_perfil_editar.currentIndex() + 1)
        perfil_path = os.path.join(os.path.dirname(__file__), "curaduria_profiles.json")
        try:
            with open(perfil_path, "r", encoding="utf-8") as f:
                perfiles = json.load(f)
        except FileNotFoundError:
            perfiles = {}

        perfiles[numero] = {
            "luz": self.cb_luz_conf.currentText(),
            "momento": self.cb_mom_conf.currentText(),
            "densidad": self.cb_den_conf.currentText(),
            "estilo": self.cb_estilo_conf.currentText(),
            "duracion": self.in_dur_conf.text()
        }

        with open(perfil_path, "w", encoding="utf-8") as f:
            json.dump(perfiles, f, indent=2)
        print(f"[CONFIG] Perfil {numero} guardado.") 
    # ------------------------------------------------------------
    # LÓGICA DE SUMINISTRO Y TALLER
    # ------------------------------------------------------------
    def on_folder_open(self, index):
        p = self.model.filePath(index)
        if os.path.isdir(p):
            self.tabla.setRowCount(0)
            self.todos_los_temas = []
            archivos = [os.path.join(p, f) for f in os.listdir(p) if f.lower().endswith(('.mp3', '.flac', '.wav'))]
            if not archivos: return
            self.sf = widgets_ufulu.SplashForense(len(archivos), self)
            self.w = EngineUfulu(archivos)
            self.w.resultado.connect(self.add_f_to_db)
            self.w.progreso.connect(lambda v, total=len(archivos): self.sf.update_prog(v, total))
            self.sf.open()
            self.w.start()

    def on_tabla_cell_changed(self, row, col):
        """
        Guarda automáticamente en los tags del archivo los cambios
        realizados por el DJ en las celdas de la tabla (BPM, Función, Luz, Estilo).
        """
        # Columnas editables:
        # 0: Checkbox (widget, no guardamos)
        # 1: Nombre (puede editarse, guardamos como título)
        # 2: BPM Tag (guardamos como BPM)
        # 3: BPM Ufulu (guardamos también como BPM)
        # 4: Función (guardamos como funcion)
        # 5: Energía/Luz (guardamos como luz)
        # 6: Estilo (guardamos como estilo)
        # 7: Estado (es solo visual, no se guarda en tag)
        if col in (0, 7):
            return  # No guardamos cambios en checkbox ni en estado

        path = self.todos_los_temas[row] if row < len(self.todos_los_temas) else None
        if not path or not os.path.exists(path):
            return

        # Leer valores actuales de la tabla
        item_bpm_tag = self.tabla.item(row, 2)
        item_bpm_ufulu = self.tabla.item(row, 3)
        item_funcion = self.tabla.item(row, 4)
        item_luz = self.tabla.item(row, 5)
        item_estilo = self.tabla.item(row, 6)
        item_nombre = self.tabla.item(row, 1)

        bpm = item_bpm_ufulu.text().strip() if item_bpm_ufulu else item_bpm_tag.text().strip() if item_bpm_tag else "0"
        funcion = item_funcion.text().strip() if item_funcion else "-"
        luz = item_luz.text().strip() if item_luz else "NOCHE"
        estilo = item_estilo.text().strip() if item_estilo else "*"
        titulo = item_nombre.text().strip() if item_nombre else os.path.basename(path)

        # Escribir en los tags del archivo físico
        try:
            tag_manager.escribir_tags_ufulu(
                path, bpm, funcion, luz=luz, estilo=estilo, cues=self.cue_times if path == self.current_path else None
            )
            print(f"[TALLER] Tags actualizados para {os.path.basename(path)}")
        except Exception as e:
            print(f"[TALLER] Error al guardar tags: {e}")

        # Actualizar también la base de datos (importante para coherencia)
        try:
            c = self.db._conn.cursor()
            c.execute("""
                UPDATE tracks 
                SET filename=?, bpm=?, funcion=?, color=?, estilo=?
                WHERE path=?
            """, (titulo, bpm, funcion, luz, estilo, path))
            self.db._conn.commit()
        except Exception as e:
            print(f"[TALLER] Error al actualizar BD: {e}")






    def add_f_to_db(self, meta, adn, bpm_ufulu):
        self.db.save_full_track(meta, adn)
        self.add_f_table(meta, "NUEVO", bpm_ufulu)
        self.model.layoutChanged.emit()

    def add_f_table(self, meta, origen, bpm_calculado=None):
        path = meta[5] if isinstance(meta, list) else meta
        r = self.tabla.rowCount()
        self.tabla.insertRow(r)
        self.todos_los_temas.append(path)
        chk = QCheckBox(); chk.setChecked(True)
        self.tabla.setCellWidget(r, 0, chk)
        bt = meta[1] if isinstance(meta, list) else "0"
        bu = bpm_calculado if bpm_calculado else bt
        bg = QColor(139, 0, 0, 60) if not self.db.juzgar_coherencia_bpm(meta[4], bu) else None
        datos = [meta[0], bt, bu, meta[2], meta[3], meta[4], origen]
        for i, v in enumerate(datos):
            it = QTableWidgetItem(str(v))
            it.setFont(QFont("Segoe UI", 10))
            it.setForeground(QColor("#e1e1e1"))
            if bg: it.setBackground(bg)
            if i == 1 and str(bt) != "0" and str(bt) != str(bu):
                it.setForeground(QColor("#ff4444"))
            self.tabla.setItem(r, i + 1, it)

    def load_q(self, item):
        self.tabla.selectRow(item.row())
        p = self.todos_los_temas[item.row()]
        self.current_path = p
        self.adn_actual = self.db.get_adn(p)
        _, _, _, self.cue_times, _ = tag_manager.leer_tags_completos(p)
        self.track_duration = librosa.get_duration(path=p)
        # Preparar para preescucha
        self._cur_player.setSource(QUrl.fromLocalFile(p))
        self.refresh_visuals()

    def run_triangulation(self):
        if not self.current_path: return
        try:
            v_pts = [float(dial.value() / 60000.0 * self.track_duration) for dial, lb in self.dials]
            self.w = EngineUfulu([self.current_path], pt_a=v_pts[0], pt_b=v_pts[1], pt_c=v_pts[2])
            self.w.resultado.connect(lambda m, a: self.tabla.setItem(self.tabla.currentRow(), 3, QTableWidgetItem(str(m[1]))))
            self.w.start()
            print(f">>> Re-triangulando tema sobre puntos: {v_pts}")
        except Exception as e:
            print(f"Error en Triangulación: {e}")

    def inject_current(self):
        row = self.tabla.currentRow()
        if row < 0: return
        bpm = self.tabla.item(row, 3).text()
        fnc = self.tabla.item(row, 4).text()
        luz = self.tabla.item(row, 5).text()
        estilo = self.tabla.item(row, 6).text()
        if tag_manager.escribir_tags_ufulu(self.current_path, bpm, fnc, luz=luz, estilo=estilo, cues=self.cue_times):
            QMessageBox.information(self, "RODEC SYSTEM", "ADN FIJADO CON ÉXITO EN EL SUMINISTRO.")

    def toggle_all(self):
        for r in range(self.tabla.rowCount()):
            chk = self.tabla.cellWidget(r, 0)
            if chk: chk.setChecked(not chk.isChecked())

    def save_selected(self):
        confirm = QMessageBox.question(self, "SISTEMA RODEC", "¿SOBRESCRIBIR TAGS Y ACTUALIZAR MALETA CON EL ANÁLISIS DE UFULU?")
        if confirm != QMessageBox.StandardButton.Yes: return
        exitos = 0
        fallos = 0
        for r in range(self.tabla.rowCount()):
            chk = self.tabla.cellWidget(r, 0)
            if not chk or not chk.isChecked(): continue
            try:
                path_tema = self.todos_los_temas[r]
                bpm_ufulu = self.tabla.item(r, 3).text().strip() if self.tabla.item(r, 3) else "0"
                func_ufulu = self.tabla.item(r, 4).text().strip() if self.tabla.item(r, 4) else "-"
                luz_ufulu = self.tabla.item(r, 5).text().strip() if self.tabla.item(r, 5) else "-"
                estilo_ufulu = self.tabla.item(r, 6).text().strip() if self.tabla.item(r, 6) else "-"
                cues = self.cue_times if path_tema == self.current_path else None
                ok = tag_manager.escribir_tags_ufulu(path_tema, bpm_ufulu, func_ufulu, luz=luz_ufulu, estilo=estilo_ufulu, cues=cues)
                if ok:
                    adn_pre = self.db.get_adn(path_tema)
                    meta_update = [os.path.basename(path_tema), bpm_ufulu, func_ufulu, luz_ufulu, estilo_ufulu, path_tema]
                    self.db.save_full_track(meta_update, adn_pre)
                    exitos += 1
                else:
                    fallos += 1
            except Exception as e:
                print(f"[SAVE_SELECTED] error fila {r}: {e}")
                fallos += 1
        self.refrescar_maleta_tabla()
        QMessageBox.information(self, "SELLADO", f"PROCESO COMPLETADO:\n{exitos} Éxitos / {fallos} Fallos.")

    def gestor_pestanas(self, index):
        if index == 1:
            self.in_busq.clear()
            self.refrescar_maleta_tabla()

    def cargar_desde_maleta_al_taller(self, index):
        try:
            item = self.tabla_maleta.item(index.row(), 5)
            if not item: return
            path_real = item.data(Qt.ItemDataRole.UserRole)
            if not path_real or not os.path.exists(path_real):
                QMessageBox.warning(self, "MALETA", "Archivo no encontrado.")
                return
            self.current_path = path_real
            self.adn_actual = self.db.get_adn(path_real)
            _, _, _, self.cue_times, _ = tag_manager.leer_tags_completos(path_real)
            self.track_duration = librosa.get_duration(path=path_real)
            self.tabs.setCurrentIndex(0)
            self.refresh_visuals()
        except Exception as e:
            print(f"Error en carga desde maleta: {e}")

    def exportar_maleta_csv(self):
        p, _ = QFileDialog.getSaveFileName(self, "Exportar Inventario", "", "Archivo CSV (*.csv)")
        if p:
            try:
                with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(["NOMBRE", "BPM", "FUNCIÓN", "LUZ", "ESTILO", "RUTA"])
                    for i in range(self.tabla_maleta.rowCount()):
                        row = []
                        for j in range(6):
                            item = self.tabla_maleta.item(i, j)
                            if j == 5:
                                row.append(item.data(Qt.ItemDataRole.UserRole) or item.text())
                            else:
                                row.append(item.text() if item else "")
                        writer.writerow(row)
                QMessageBox.information(self, "MALETA", "INVENTARIO EXPORTADO CON ÉXITO.")
            except Exception as e:
                print(f"Error en exportación: {e}")

    def export_guia_txt(self):
        p, _ = QFileDialog.getSaveFileName(self, "Guardar Plan de Vuelo", "", "Texto (*.txt)")
        if p:
            config = {'maleta': "BIBLIOTECA GLOBAL", 'duracion': self.in_dur.text()}
            with open(p, "w", encoding="utf-8") as f:
                f.write(curaduria_engine.generar_texto_guia(self.current_playlist_data, config))

    # ------------------------------------------------------------
    # ANÁLISIS DE ESTILOS CON SVM
    def _preparar_analisis_ui(self):
        self.btn_analizar_estilos.setEnabled(False)
        self.btn_analizar_toda_maleta.setEnabled(False)
        self.btn_analizar_estilos.setText("ANALIZANDO...")
        self.btn_analizar_toda_maleta.setText("ANALIZANDO...")
        self.progress_ia.setVisible(True)
        self.progress_ia.setRange(0, 0)
        self.progress_ia.setValue(0)
    
    def _ejecutar_analisis(self, rutas):
        try:
            from genre_analyzer_svm import analizar_archivos_svm

            def reportar_progreso(actual, total):
                self.analisis_progreso.emit(actual, total)

            generos = analizar_archivos_svm(rutas, progress_callback=reportar_progreso)
            self.analisis_completado.emit(generos)
        except Exception as e:
            self.analisis_completado.emit({ruta: f"Error: {e}" for ruta in rutas})

    def _actualizar_estilos(self, generos: dict):
        # Refrescar la tabla de Mi Maleta
        self.refrescar_maleta_tabla()

        # Restaurar botones y barra
        self.btn_analizar_estilos.setEnabled(True)
        self.btn_analizar_toda_maleta.setEnabled(True)
        self.btn_analizar_estilos.setText("ANALIZAR ESTILOS (AI)")
        self.btn_analizar_toda_maleta.setText("ANALIZAR TODA LA MALETA (AI)")
        self.progress_ia.setVisible(False)

        errores = sum(1 for g in generos.values() if "Error" in str(g))
        mensaje = f"Se analizaron {len(generos)} pistas."
        if errores:
            mensaje += f"\nNo se pudieron procesar {errores} archivos."
        QMessageBox.information(self, "Análisis completado", mensaje)

    def _guardar_estilo_en_bd_y_tags(self, ruta: str, genero: str):
        try:
            c = self.db._conn.cursor()
            row = c.execute(
                "SELECT filename, bpm, funcion, color, wave_data, energia, key_camelot, bpm_confidence FROM tracks WHERE path=?",
                (ruta,)
            ).fetchone()
            if row:
                # Mensaje de progreso: guardando
                print(f"[DBG] Guardando '{genero}' en {os.path.basename(ruta)}")
                 # Extraer solo el género si viene con confianza (ej. "Techno (85%)")
                genero_limpio = genero.split('(')[0].strip() if '(' in genero else genero
                meta = [row[0], row[1], row[2], row[3], genero_limpio, ruta, row[5], row[6], row[7]]
                self.db.save_full_track(meta, json.loads(row[4]))
                cues = tag_manager.leer_tags_completos(ruta)[3]
                tag_manager.escribir_tags_ufulu(ruta, row[1], row[2], luz=row[3], estilo=genero_limpio, cues=cues)
            else:
                print(f"[DBG] No se encontró {os.path.basename(ruta)} en la BD")
        except Exception as e:
            print(f"[DBG] ERROR al guardar {ruta}: {e}")

    # ------------------------------------------------------------
    # MÓDULO GRÁFICO: ONDA Y MARCADORES (con preescucha)
    # ------------------------------------------------------------
    # MÓDULO GRÁFICO: ONDA Y MARCADORES (con preescucha)
    # ------------------------------------------------------------
    def on_waveform_click(self, event):
        x = event.position().x()
        ancho = self.view_onda.width()
        tiempo = (x / ancho) * self.track_duration

        # Preescucha con clic derecho o Shift+clic izquierdo
        if event.button() == Qt.MouseButton.RightButton or \
           (event.button() == Qt.MouseButton.LeftButton and QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier):
            self._cur_player.setPosition(int(tiempo * 1000))
            self._cur_player.play()
            return

        # Marcado de cue (comportamiento original)
        if event.button() == Qt.MouseButton.LeftButton and self.armed_cue:
            self.cue_times[self.armed_cue] = tiempo
            self.armed_cue = None
            self.refresh_visuals()
    def refresh_visuals(self):
        if not self.adn_actual or self.view_onda.width() <= 0: return
        w_v = int(self.scroll.viewport().width() * self.current_zoom)
        h_v = self.scroll.viewport().height()
        pix = QPixmap(w_v, h_v); pix.fill(QColor("#080808"))
        p = QPainter(pix)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            onda, rms_d, beat_d, centro = self.adn_actual["onda"], self.adn_actual["rms"], self.adn_actual["beat"], h_v // 2
            for i in range(len(onda)):
                x = int((i/len(onda)) * w_v); v_o = float(onda[i]); ap = int(v_o * (h_v * 0.7) / 2)
                if self.btn_stab.isChecked() and i < len(beat_d) and beat_d[i]:
                    p.setPen(QPen(QColor(255, 140, 0, 60), 1)); p.drawLine(x, 0, x, h_v)
                p.setPen(QPen(QColor("#00ffcc"), 1)); p.drawLine(x, centro-ap, x, centro+ap)
            if self.btn_rms.isChecked() and len(rms_d) > 1:
                p.setPen(QPen(QColor(255, 255, 255, 220), 2)); poly = QPolygonF()
                for i in range(len(rms_d)):
                    px = (i / len(rms_d)) * w_v; py = centro - (float(rms_d[i]) * (h_v * 0.7) / 2)
                    poly.append(QPointF(px, py))
                p.drawPolyline(poly)
            for i, (dial, lb) in enumerate(self.dials):
                # Escalar el valor del dial según el zoom
                perc = dial.value() / (60000.0 * self.current_zoom)
                perc = max(0.0, min(1.0, perc))  # No pasarse de 0 ni 1
                kx = int(perc * w_v)
                p.setOpacity(0.4)
                p.fillRect(kx-2, 0, 4, h_v, Qt.GlobalColor.white)
                tv = perc * self.track_duration
                lb.setText(f"{int(tv//60):02d}:{int(tv%60):02d}:{int((tv%1)*100):02d}")
            for n_cue, t_cue in self.cue_times.items():
                if t_cue is not None:
                    xc = int((t_cue / self.track_duration) * w_v)
                    p.setPen(QPen(QColor(ufulu_style.CUE_COLORS[n_cue-1]), 3)); p.drawLine(xc, 0, xc, h_v)
        finally:
            p.end()
        self.view_onda.setPixmap(pix); self.view_onda.setFixedWidth(pix.width())

    def change_zoom(self, v):
        self.current_zoom = v
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn if v > 1 else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.refresh_visuals()

    def asignar_cue_logic(self, n):
        if self.cue_times[n] is not None:
            self.cue_times[n] = None; self.armed_cue = None
        else:
            self.armed_cue = n
        for i, b in enumerate(self.cue_btns):
            idx = i + 1
            if self.armed_cue == idx:
                b.setStyleSheet("background:#8b0000; color:white; border: 1px solid white;")
            elif self.cue_times[idx] is not None:
                b.setStyleSheet(f"background:{ufulu_style.CUE_COLORS[i]}; color:black;")
            else:
                b.setStyleSheet("")
        self.refresh_visuals()

    # ============================================================
    # BLOQUE DE EXTENSIONES UFULU v33.7
    # ============================================================
    def _instalar_extensiones_v337(self):
        self.setAcceptDrops(True)
        for k, fn in [("P", self._v337_play_pause), ("Space", self._v337_play_pause),
                      ("S", self._v337_stop), ("Ctrl+G", self._v337_generar)]:
            try: QShortcut(QKeySequence(k), self).activated.connect(fn)
            except: pass
        for i in range(3):
            try:
                QShortcut(QKeySequence(f"Ctrl+{i+1}"), self).activated.connect(
                    lambda idx=i: self.tabs.setCurrentIndex(idx))
            except: pass

    def _v337_play_pause(self):
        if hasattr(self, '_cur_player'):
            try:
                if self._cur_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                    self._cur_player.pause()
                else:
                    self._cur_player.play()
            except: pass

    def _v337_stop(self):
        if hasattr(self, '_cur_player'):
            try: self._cur_player.stop()
            except: pass

    def _v337_generar(self):
        if hasattr(self, 'btn_gen'):
            try: self.btn_gen.animateClick()
            except: pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and os.path.isdir(url.toLocalFile()):
                    event.acceptProposedAction(); return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if not url.isLocalFile(): continue
            ruta = url.toLocalFile()
            if os.path.isdir(ruta):
                self.tabs.setCurrentIndex(0)
                idx = self.model.index(ruta)
                if idx.isValid():
                    self.tree.scrollTo(idx); self.tree.setCurrentIndex(idx)
                self.on_folder_open(self.model.index(ruta))
                event.acceptProposedAction(); return
        event.ignore()

    def auto_segmentar_handler(self):
        if not self.current_path or not self.adn_actual:
            QMessageBox.warning(self, "AUTO-SEGMENTAR", "Carga primero un tema."); return
        rms_v = self.adn_actual.get("rms", [])
        if not rms_v or self.track_duration <= 0:
            QMessageBox.warning(self, "AUTO-SEGMENTAR", "RMS insuficiente."); return
        seg = detectar_segmentos_estructurales(rms_v, self.adn_actual.get("beat", []), self.track_duration)
        if not seg:
            QMessageBox.information(self, "AUTO-SEGMENTAR", "No se detectó estructura."); return
        mapa = {"INTRO":1, "BUILD":2, "DROP":3, "BREAK":4, "OUTRO":5}
        cambios = []
        for nombre, t in seg.items():
            if nombre in mapa and t is not None:
                self.cue_times[mapa[nombre]] = float(t)
                cambios.append(f"M{mapa[nombre]}={nombre} ({int(t//60):02d}:{int(t%60):02d})")
        self.refresh_visuals()
        for i, b in enumerate(self.cue_btns):
            idx = i + 1
            if self.cue_times.get(idx) is not None:
                b.setStyleSheet(f"background:{ufulu_style.CUE_COLORS[i]}; color:black;")
        QMessageBox.information(self, "AUTO-SEGMENTAR", "Segmentos aplicados como CUEs:\n\n" + "\n".join(cambios))

    def sugerir_siguiente_handler(self):
        if not self.current_path:
            QMessageBox.warning(self, "SUGERIR", "Carga primero un tema."); return
        pool = self.db.get_inventory_full()
        track_actual = next((t for t in pool if t[5] == self.current_path), None)
        if not track_actual:
            QMessageBox.warning(self, "SUGERIR", "No está en la maleta. Fíjalo primero."); return
        sugs = curaduria_engine.sugerir_siguiente_track(track_actual, pool, 8)
        if not sugs:
            QMessageBox.information(self, "SUGERIR", "Sin candidatos compatibles."); return
        msg = "MEJORES SUGERENCIAS:\n\n"
        for i, s in enumerate(sugs[:5], 1):
            t = s['track']
            msg += f"{i}. N{s['nivel']} - {os.path.basename(str(t[0]))[:40]}\n"
            msg += f"   {t[1]} BPM | KEY {t[7]} | Δ={s['delta_bpm']:.1f} | {s['motivo']}\n\n"
        QMessageBox.information(self, "SIGUIENTE TEMA", msg)

    def abrir_diagnostico_salud(self):
        problemas = self.db.diagnosticar_salud_maleta()
        if not problemas:
            QMessageBox.information(self, "SALUD", "Todos los temas en orden."); return
        msg = f"{len(problemas)} TEMAS CON PROBLEMAS:\n\n"
        for path, fn, probs in problemas[:30]:
            msg += f"• {fn[:40]}: {', '.join(probs)}\n"
        if len(problemas) > 30: msg += f"\n... y {len(problemas)-30} más"
        QMessageBox.warning(self, "SALUD MALETA", msg)

    def abrir_dashboard_estadisticas(self):
        s = self.db.get_stats()
        if s['total'] == 0:
            QMessageBox.information(self, "STATS", "Sin datos."); return
        msg = f"TOTAL: {s['total']} TEMAS\n\n"
        msg += f"DÍA: {s['luz_dist']['DÍA']} | NOCHE: {s['luz_dist']['NOCHE']}\n\n"
        msg += "TOP 5 ESTILOS:\n"
        for est, c in s['estilo_dist'][:5]: msg += f"  • {est}: {c}\n"
        msg += "\nTOP 5 BUCKETS BPM:\n"
        for b, c in sorted(s['bpm_hist'].items(), key=lambda x: -x[1])[:5]: msg += f"  • {b}-{b+5} BPM: {c}\n"
        QMessageBox.information(self, "ESTADÍSTICAS", msg)

    def _recolectar_cues_playlist(self):
        out = {}
        if not getattr(self, 'current_playlist_data', None): return out
        for item in self.current_playlist_data:
            d = item.get('data', [])
            if len(d) < 6: continue
            path = str(d[5])
            if not path or not os.path.exists(path): continue
            try:
                _, _, _, cues, _ = tag_manager.leer_tags_completos(path)
                cues_limpios = {int(k): float(v) for k, v in cues.items() if v is not None}
                if cues_limpios:
                    out[path] = cues_limpios
                    out[os.path.abspath(path)] = cues_limpios
            except: pass
        return out

    def export_playlist_m3u8(self):
        self._exp_generic(playlist_exporters.exportar_m3u8, "m3u8", "M3U8")

    def export_playlist_nml(self):
        if not getattr(self, 'current_playlist_data', None):
            QMessageBox.warning(self, "EXPORTAR", "Genera un Plan primero."); return
        p, _ = QFileDialog.getSaveFileName(self, "Traktor NML", "", "NML (*.nml)")
        if not p: return
        if not p.lower().endswith(".nml"): p += ".nml"
        try:
            cues = self._recolectar_cues_playlist()
            playlist_exporters.exportar_nml_traktor(self.current_playlist_data, p, cues_por_path=cues)
            QMessageBox.information(self, "EXPORTAR", f"Traktor NML:\n{p}")
        except Exception as e: QMessageBox.critical(self, "EXPORTAR", str(e))

    def export_playlist_xml(self):
        if not getattr(self, 'current_playlist_data', None):
            QMessageBox.warning(self, "EXPORTAR", "Genera un Plan primero."); return
        p, _ = QFileDialog.getSaveFileName(self, "Rekordbox XML", "", "XML (*.xml)")
        if not p: return
        if not p.lower().endswith(".xml"): p += ".xml"
        try:
            cues = self._recolectar_cues_playlist()
            playlist_exporters.exportar_xml_rekordbox(self.current_playlist_data, p, cues_por_path=cues)
            QMessageBox.information(self, "EXPORTAR", f"Rekordbox XML:\n{p}")
        except Exception as e: QMessageBox.critical(self, "EXPORTAR", str(e))

    def export_playlist_pdf(self):
        if not getattr(self, 'current_playlist_data', None):
            QMessageBox.warning(self, "EXPORTAR", "Genera un Plan primero."); return
        p, _ = QFileDialog.getSaveFileName(self, "Informe PDF", "", "PDF (*.pdf)")
        if not p: return
        if not p.lower().endswith(".pdf"): p += ".pdf"
        try:
            notas_path = {}
            for item in self.current_playlist_data:
                d = item.get('data', [])
                if len(d) > 5:
                    n = self.db.get_notas(str(d[5]))
                    if n: notas_path[str(d[5])] = n
            params = {'luz': self.cb_luz.currentText() if hasattr(self, 'cb_luz') else '-',
                      'momento': self.cb_mom.currentText() if hasattr(self, 'cb_mom') else '-',
                      'estilo': self.cb_estilo_cur.currentText() if hasattr(self, 'cb_estilo_cur') else '-',
                      'densidad': self.cb_den.currentText() if hasattr(self, 'cb_den') else '-',
                      'duracion': self.in_dur.text() if hasattr(self, 'in_dur') else '-'}
            playlist_exporters.exportar_pdf_sesion(self.current_playlist_data, p, params=params, rating=0, notas_sesion="", notas_por_path=notas_path)
            QMessageBox.information(self, "EXPORTAR", f"PDF:\n{p}")
        except ImportError: QMessageBox.critical(self, "EXPORTAR", "Falta reportlab.\npip install reportlab")
        except Exception as e: QMessageBox.critical(self, "EXPORTAR", str(e))

    def _exp_generic(self, fn_export, ext, descr):
        if not getattr(self, 'current_playlist_data', None):
            QMessageBox.warning(self, "EXPORTAR", "Genera un Plan primero."); return
        p, _ = QFileDialog.getSaveFileName(self, f"Exportar {descr}", "", f"{descr} (*.{ext})")
        if not p: return
        if not p.lower().endswith(f".{ext}"): p += f".{ext}"
        try:
            fn_export(self.current_playlist_data, p)
            QMessageBox.information(self, "EXPORTAR", f"OK: {p}")
        except Exception as e: QMessageBox.critical(self, "EXPORTAR", str(e))
    def _analizar_y_refinar_carpeta(self, rutas):
        """Ejecuta la clasificación de IA y luego el refinamiento de funciones."""
        self.progress_ia.setVisible(True)
        self.progress_ia.setRange(0, 0)
    
        def callback_ia(actual, total):
            self.progress_ia.setMaximum(total)
            self.progress_ia.setValue(actual)
            self.progress_ia.setFormat(f"IA: {actual}/{total}")
    
        def al_terminar_ia(generos):
            self._actualizar_estilos(generos)
            # Lanzar refinamiento de funciones
            self._refinar_funciones_automatico()
    
        # Llamar a la IA en un hilo
        from genre_analyzer_svm import analizar_archivos_svm
        threading.Thread(target=lambda: al_terminar_ia(
            analizar_archivos_svm(rutas, progress_callback=callback_ia)
        ), daemon=True).start()
    def _refinar_funciones_automatico(self):
        """Refina las funciones narrativas y refresca la maleta."""
        self.hilo_refinar = HiloRefinarFunciones(self.db)
        self.hilo_refinar.progreso.connect(
            lambda a, t: (self.progress_ia.setMaximum(t), self.progress_ia.setValue(a), self.progress_ia.setFormat(f"Función: {a}/{t}"))
        )
        self.hilo_refinar.finalizado.connect(self._refinar_finalizado_auto)
        self.hilo_refinar.start()

    def _refinar_finalizado_auto(self):
        self.progress_ia.setVisible(False)
        self.refrescar_maleta_tabla()
        print(">> Análisis automático completado.")
class HiloRefinarFunciones(QThread):
    progreso = pyqtSignal(int, int)
    finalizado = pyqtSignal()

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        try:
            print("[REFINAR] Hilo iniciado.")
            cursor = self.db._conn.cursor()
            rows = cursor.execute(
                "SELECT path, estilo, wave_data, color FROM tracks WHERE analyzed=1"
            ).fetchall()

            total = len(rows)
            print(f"[REFINAR] Se van a procesar {total} pistas.")
            if total == 0:
                print("[REFINAR] No hay pistas analizadas.")
                self.finalizado.emit()
                return

            conteo = {"1. OPEN": 0, "2. HOLD": 0, "3. SHIFT": 0, "4. PEAK": 0}

            for idx, row in enumerate(rows):
                path, estilo, wave_json, color = row
                try:
                    adn = json.loads(wave_json)
                    rms_v = adn.get("rms", [])
                    beat_v = adn.get("beat", [])

                    from audio_engine import determinar_funcion_por_estructura, normalizar

                    nueva_funcion = determinar_funcion_por_estructura(
                        rms_v, beat_v, 1.0, estilo=normalizar(estilo), color=color
                    )
                    
                    cursor.execute(
                        "UPDATE tracks SET funcion=? WHERE path=?",
                        (nueva_funcion, path)
                    )

                    if nueva_funcion in conteo:
                        conteo[nueva_funcion] += 1
                    else:
                        conteo["3. SHIFT"] += 1

                    # ---- DIAGNÓSTICO CORREGIDO (dentro del try, solo 5 primeras) ----
                    if idx < 5:
                        rms_arr = np.array(rms_v) if len(rms_v) > 0 else np.array([0])
                        beat_arr = np.array(beat_v, dtype=float) if len(beat_v) > 0 else np.array([0])
                        presion_media = float(np.mean(rms_arr))
                        densidad_media = float(np.mean(beat_arr))
                        varianza_presion = float(np.std(rms_arr)) / max(presion_media, 0.001)
                        print(f"[DIAG] {os.path.basename(path)}: estilo={estilo} ({color}) → {nueva_funcion} | presión={presion_media:.4f}, densidad={densidad_media:.4f}, varianza={varianza_presion:.4f}")
                    # ----------------------------------------------------------------

                except Exception as e:
                    print(f"[REFINAR] Error en {os.path.basename(path)}: {e}")

                self.progreso.emit(idx + 1, total)

            self.db._conn.commit()
            print("\n" + "=" * 40)
            print("  RESUMEN DE FUNCIONES REFINADAS")
            print("=" * 40)
            for funcion, cantidad in conteo.items():
                if cantidad > 0:
                    print(f"  {funcion}: {cantidad}")
            print("=" * 40)
            self.finalizado.emit()

        except Exception as e:
            print(f"[REFINAR] Error general en el hilo: {e}")
            self.finalizado.emit()
def ufulu_error_handler(etype, value, tb):
    import traceback
    print("".join(traceback.format_exception(etype, value, tb)))
    input("\nSISTEMA DETENIDO. ENTER PARA SALIR...")

if __name__ == "__main__":
    sys.excepthook = ufulu_error_handler
    app = QApplication(sys.argv)
    db_master = collection_manager.CollectionManager()
    p_val = db_master.get_default_path()
    p_clean = p_val if isinstance(p_val, str) else ""
    sw = widgets_ufulu.SplashWelcome(p_clean)
    if sw.exec() == QDialog.DialogCode.Accepted:
        db_master.set_default_path(sw.selected_path)
        main_window = MainApp(sw.selected_path, db_master)
        main_window.show()
        sys.exit(app.exec())