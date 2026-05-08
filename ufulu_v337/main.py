import sys
import os
import librosa
import numpy as np
import csv
import traceback
import json
import sqlite3
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# --- SINCRONIZACIÓN CON EL ECOSISTEMA UFULU ---
import ufulu_style
import collection_manager
import tag_manager
import curaduria_engine
import widgets_ufulu
import playlist_exporters
from widgets_rodec import RodecKnob, RodecKnobSelector
from audio_engine import EngineUfulu, detectar_segmentos_estructurales

# --- MODELO DE EXPLORACIÓN CON MEMORIA VISUAL ---
class UfuluFileModel(QFileSystemModel):
    """
    Navegador lateral que colorea los archivos según su estado en el almacén.
    Turquesa = Analizado | Blanco = Carpeta Completa | Gris = Pendiente.
    """
    def __init__(self, db): 
        super().__init__()
        self.db = db

    def data(self, index, role):
        if role == Qt.ItemDataRole.ForegroundRole:
            path = self.filePath(index)
            if not os.path.isdir(path):
                # Si el tema ya existe en la base de datos
                if self.db.track_exists(path):
                    return QColor("#00ffcc")
                else:
                    return QColor("#8899a6")
            else:
                # Si es carpeta, comprobamos si todo el contenido está sellado
                if self.db.is_folder_complete(path):
                    return QColor("#FFFFFF")
                else:
                    return QColor("#8899a6")
        return super().data(index, role)

class MainApp(QMainWindow):
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
        # Ocultamos metadatos de sistema (tamaño, tipo, fecha)
        for i in range(1, 4):
            self.tree.hideColumn(i)
        self.tree.doubleClicked.connect(self.on_folder_open)
        
        sidebar_ly.addWidget(QLabel("SUMINISTRO DE AUDIO"))
        sidebar_ly.addWidget(self.tree)
        main_ly.addWidget(sidebar)
        
        # --- RACK CENTRAL DE 3 MÓDULOS ---
        self.tabs = QTabWidget()
        main_ly.addWidget(self.tabs)
        
        self.tab_col = QWidget()     # Módulo 1: EL TALLER
        self.tab_maleta = QWidget()  # Módulo 2: MI MALETA
        self.tab_cur = QWidget()     # Módulo 3: CURADURÍA
        
        self.tabs.addTab(self.tab_col, "1. EL TALLER")
        self.tabs.addTab(self.tab_maleta, "2. MI MALETA")
        self.tabs.addTab(self.tab_cur, "3. CURADURÍA")
        
        # Inicialización de interfaces de módulos (Se entregan en bloques siguientes)
        self.init_coleccion_ui() 
        self.init_maleta_ui()    
        self.init_curaduria_ui() 
        
        # Conexión de señal de cambio de pestaña para refresco de datos
        self.tabs.currentChanged.connect(self.gestor_pestanas)

        # === INTEGRACIÓN v33.7 ===
        # Reproductor de pre-escucha (3-5s al soltar el knob)
        self._cur_player = QMediaPlayer()
        self._cur_audio_out = QAudioOutput()
        self._cur_player.setAudioOutput(self._cur_audio_out)

        # Barra de menú con todas las acciones avanzadas
        self._build_menu_v337()

        # Atajos de cabina + drag&drop de carpetas
        self._instalar_extensiones_v337()

    # =====================================================
    # MENU BAR v33.7 - Acciones avanzadas accesibles
    # =====================================================
    def _build_menu_v337(self):
        mb = self.menuBar()

        # === TALLER ===
        m_tal = mb.addMenu("&TALLER")
        a_seg = m_tal.addAction("Auto-segmentar (Intro/Build/Drop/Break/Outro)")
        a_seg.setShortcut("Ctrl+T")
        a_seg.triggered.connect(self.auto_segmentar_handler)

        a_sug = m_tal.addAction("Sugerir siguiente tema")
        a_sug.setShortcut("Ctrl+N")
        a_sug.triggered.connect(self.sugerir_siguiente_handler)

        # === MALETA ===
        m_mal = mb.addMenu("&MALETA")
        m_mal.addAction("Salud de la maleta",
                        self.abrir_diagnostico_salud).setShortcut("Ctrl+H")
        m_mal.addAction("Estadísticas (dashboard)",
                        self.abrir_dashboard_estadisticas).setShortcut("Ctrl+E")

        # === CURADURÍA ===
        m_cur = mb.addMenu("&CURADURÍA")
        m_cur.addAction("Generar plan de vuelo",
                        self._v337_generar).setShortcut("Ctrl+G")
        m_cur.addSeparator()
        m_cur.addAction("Plantillas de sesión…", self.abrir_dialogo_templates)
        m_cur.addAction("Histórico + rating…",   self.abrir_dialogo_historico)

        # === EXPORTAR ===
        m_exp = mb.addMenu("&EXPORTAR")
        m_exp.addAction("Playlist M3U8",          self.export_playlist_m3u8)
        m_exp.addAction("Traktor NML (con HotCues)", self.export_playlist_nml)
        m_exp.addAction("Rekordbox XML",          self.export_playlist_xml)
        m_exp.addSeparator()
        m_exp.addAction("Informe PDF de sesión",  self.export_playlist_pdf)
        m_exp.addAction("Inventario CSV",         self.exportar_maleta_csv)

        # === AYUDA ===
        m_h = mb.addMenu("&AYUDA")
        m_h.addAction("Acerca de Ufulu", self._about_v337)

    def _about_v337(self):
        QMessageBox.information(
            self, "UFULU · RODEC EDITION",
            "UFULU RODEC EDITION  ·  v33.7\n\n"
            "Consola forense de procesado analógico para DJs.\n"
            "Análisis BPM/Energía/Key + curaduría narrativa\n"
            "+ exportadores Traktor/Rekordbox/PDF.\n\n"
            "Atajos: Ctrl+1/2/3 cambian de pestaña.\n"
            "Ctrl+T auto-segmentar  ·  Ctrl+N sugerir\n"
            "Ctrl+H salud  ·  Ctrl+E stats  ·  Ctrl+G plan\n"
        )

    # =====================================================
    # PLANTILLAS DE SESIÓN
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
            lst.addItem(
                f"{t['name']}  ·  {t['luz']} / {t['momento']} / "
                f"{t['estilo']} / {t['densidad']} / {t['duracion']} min"
            )
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
            self.db.guardar_template(
                name.strip(),
                self.cb_luz.currentText(), self.cb_mom.currentText(),
                self.cb_estilo_cur.currentText(),
                self.cb_den.currentText(), self.in_dur.text()
            )
            QMessageBox.information(dlg, "PLANTILLA",
                                    f"Plantilla '{name}' guardada.")
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

    # =====================================================
    # HISTÓRICO + RATING
    # =====================================================
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
    def init_coleccion_ui(self):
        """MÓDULO 1: EL TALLER (Ingesta de Audio y Quirófano ADN)"""
        ly = QVBoxLayout(self.tab_col)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(15)
        
        # --- INDICADOR DE SUMINISTRO ACTIVO ---
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

        # --- TABLA DE INGESTA UFULU (8 COLUMNAS) ---
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
        ly.addWidget(self.tabla)
        
        # --- RACK DE QUIRÓFANO ANALÓGICO ---
        self.grp_q = QGroupBox("QUIRÓFANO ANALÓGICO")
        self.grp_q.setFixedHeight(500)
        ly_q = QVBoxLayout(self.grp_q)
        
        # --- REEMPLAZO DEL BLOQUE SCROLL (v31.2) ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:#050505; border: 1px solid #555;")
        
        # BLINDAJE ANTI-PARPADEO:
        # Forzamos a que las barras NUNCA aparezcan a menos que el Zoom sea > 1
        # Y desactivamos que las barras reserven espacio físico (evita el cambio de tamaño)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.view_onda = QLabel()
        self.view_onda.mousePressEvent = self.on_waveform_click
        self.scroll.setWidget(self.view_onda)
        ly_q.addWidget(self.scroll)
        
        # --- BARRA DE CONTROL DE VISIÓN ---
        ctrls_ly = QHBoxLayout()
        self.btn_rms = QPushButton("VISTA ENVOLVENTE")
        self.btn_stab = QPushButton("VISTA RÍTMICA")
        self.btn_rms.setCheckable(True)
        self.btn_stab.setCheckable(True)
        self.btn_rms.clicked.connect(self.refresh_visuals)
        self.btn_stab.clicked.connect(self.refresh_visuals)
        
        # Selectores de Escala Quirúrgica
        for z in [1, 2, 4]:
            b = QPushButton(f"ZOOM {z}X")
            b.setFixedWidth(70)
            b.clicked.connect(lambda chk, v=z: self.change_zoom(v))
            ctrls_ly.addWidget(b)
        
        ctrls_ly.addStretch()
        ctrls_ly.addWidget(self.btn_rms)
        ctrls_ly.addWidget(self.btn_stab)
        ly_q.addLayout(ctrls_ly)
        
        # --- PANEL DE POTENCIÓMETROS (TRIANGULACIÓN) ---
        knobs_ly = QHBoxLayout()
        self.dials = []
        for i in range(3):
            v_box = QVBoxLayout()
            d = RodecKnob(style="red")
            d.setRange(0, 60000) # Máxima resolución
            d.setFixedSize(85, 85)
            # Rigor técnico: multiplicador x10 para rueda de ratón
            d.wheelEvent = lambda e, dial=d: dial.setValue(dial.value() + (10 if e.angleDelta().y() > 0 else -10))
            d.valueChanged.connect(self.refresh_visuals)
            
            l = QLabel("00:00:00")
            l.setObjectName("timeLabel")
            v_box.addWidget(l, 0, Qt.AlignmentFlag.AlignCenter)
            v_box.addWidget(d)
            knobs_ly.addLayout(v_box)
            self.dials.append((d, l))
        
        # Botones de Comando de Análisis
        self.btn_re = QPushButton("RE-TRIANGULAR")
        self.btn_inj = QPushButton("FIJAR ADN ACTUAL")
        self.btn_inj.setObjectName("injectBtn")
        self.btn_re.clicked.connect(self.run_triangulation)
        self.btn_inj.clicked.connect(self.inject_current)
        
        knobs_ly.addSpacing(30)
        knobs_ly.addWidget(self.btn_re)
        knobs_ly.addWidget(self.btn_inj)
        ly_q.addLayout(knobs_ly)
        
        # --- FILA DE MARCADORES (HOTCUES) ---
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
    def init_maleta_ui(self):
        """MÓDULO 2: MI MALETA (Central de Inteligencia y Stock Analizado)"""
        ly = QVBoxLayout(self.tab_maleta)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(15)
        
        # --- HEADER DE BÚSQUEDA Y ESTADÍSTICAS ---
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
        search_ly.addWidget(self.in_busq, 5) # Estiramiento mayor para el buscador
        search_ly.addSpacing(20)
        search_ly.addWidget(self.lbl_count_maleta)
        search_ly.addWidget(self.btn_exp)
        ly.addLayout(search_ly)

        # --- TABLA DE INVENTARIO CENTRALIZADO (6 COLUMNAS) ---
        self.tabla_maleta = QTableWidget(0, 6)
        self.tabla_maleta.setHorizontalHeaderLabels([
            "NOMBRE TEMA", "BPM", "FUNCIÓN", "ILUMINACIÓN", "ESTILO", "UBICACIÓN FÍSICA"
        ])
        self.tabla_maleta.setSortingEnabled(True)
        self.tabla_maleta.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # CONEXIÓN CRÍTICA: Doble clic para cargar el ADN en el Quirófano del Taller
        self.tabla_maleta.doubleClicked.connect(self.cargar_desde_maleta_al_taller)
        
        ly.addWidget(self.tabla_maleta)
        
        # --- PIE DE PÁGINA DE NAVEGACIÓN ---
        footer_info = QLabel("SISTEMA CENTRALIZADO: LOS DATOS SE ALIMENTAN DE TU HISTÓRICO DE ANÁLISIS")
        footer_info.setStyleSheet("color: #8899a6; font-size: 9px; font-style: italic;")
        footer_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ly.addWidget(footer_info)

    def refrescar_maleta_tabla(self):
        """Consulta profunda a SQLite y volcado en el inventario central"""
        try:
            # Recuperamos el 100% de la biblioteca analizada desde el Almacén
            data = self.db.get_inventory_full()
            self.tabla_maleta.setRowCount(0)
            f_t = QFont("Segoe UI", 10)
            
            for r_idx, r_data in enumerate(data):
                self.tabla_maleta.insertRow(r_idx)
                # Mapeo: 0:filename, 1:bpm, 2:func, 3:luz, 4:estilo, 5:path
                for c_idx, val in enumerate(r_data):
                    # En la columna de ruta (5), mostramos solo el nombre del archivo para limpiar la vista
                    # pero el texto completo permanece para la lógica de carga
                    texto_celda = os.path.basename(str(val)) if c_idx == 5 else str(val)
                    it = QTableWidgetItem(texto_celda)
                    it.setFont(f_t)
                    it.setForeground(QColor("#e1e1e1"))
                    self.tabla_maleta.setItem(r_idx, c_idx, it)
                    
            self.lbl_count_maleta.setText(f"{len(data)} TEMAS EN STOCK")
            print(f">>> Maleta sincronizada: {len(data)} registros cargados.")
        except Exception as e:
            print(f"Error de sincronización en maleta: {e}")

    def filtrar_maleta(self, texto):
        """Motor de filtrado en tiempo real sobre el rack visual"""
        t = texto.upper()
        for i in range(self.tabla_maleta.rowCount()):
            match = any(t in self.tabla_maleta.item(i, j).text().upper() 
                       for j in range(self.tabla_maleta.columnCount()))
            self.tabla_maleta.setRowHidden(i, not match)
    def init_curaduria_ui(self):
        """MÓDULO 3: CURADURÍA (Planificación Narrativa sobre Stock Global)"""
        ly = QVBoxLayout(self.tab_cur)
        ly.setContentsMargins(20, 20, 20, 20)
        ly.setSpacing(15)
        
        # --- PANEL DE CONTROL NARRATIVO ---
        grp = QGroupBox("DISEÑO DE SESIÓN ANALÓGICA")
        grp.setFixedHeight(250)
        ly_g = QGridLayout(grp)
        
        # Selectores de Ingeniería Musical
        self.cb_luz = QComboBox(); self.cb_luz.addItems(["DÍA", "NOCHE"])
        self.cb_mom = QComboBox(); self.cb_mom.addItems(["WARM-UP (APERTURA)", "PEAK (CÉNIT)", "CLOSING (CIERRE)"])
        self.cb_den = QComboBox(); self.cb_den.addItems(["NORMAL", "RÁPIDA", "LARGA"])
        self.cb_estilo_cur = QComboBox(); self.cb_estilo_cur.addItems(["TODOS", "AMAPIANO", "ORGANIC", "HOUSE", "MINIMAL", "TECHNO", "PSY"])
        
        # Parámetros de Duración y Semilla
        self.in_dur = QLineEdit("90")
        self.in_dur.setFixedWidth(60)
        self.in_dur.setStyleSheet("background:black; border:1px solid #555; color:white;")
        
        self.chk_semilla = QCheckBox("USAR TEMA ACTUAL COMO SEMILLA")
        
        # Botón de Ignición de Algoritmo
        self.btn_gen = QPushButton("GENERAR PLAN DE VUELO")
        self.btn_gen.setObjectName("injectBtn")
        self.btn_gen.setFixedHeight(40)
        self.btn_gen.clicked.connect(self.run_curaduria_feedback)
        
        # --- MAQUETACIÓN DE RACK (Rejilla) ---
        ly_g.addWidget(QLabel("ILUMINACIÓN:"), 0, 0); ly_g.addWidget(self.cb_luz, 0, 1)
        ly_g.addWidget(QLabel("ARCO/MOMENTO:"), 0, 2); ly_g.addWidget(self.cb_mom, 0, 3)
        ly_g.addWidget(QLabel("ESTILO BASE:"), 1, 0); ly_g.addWidget(self.cb_estilo_cur, 1, 1)
        ly_g.addWidget(QLabel("DENSIDAD MEZCLA:"), 1, 2); ly_g.addWidget(self.cb_den, 1, 3)
        ly_g.addWidget(QLabel("DURACIÓN (MIN):"), 2, 0); ly_g.addWidget(self.in_dur, 2, 1)
        ly_g.addWidget(self.chk_semilla, 2, 2); ly_g.addWidget(self.btn_gen, 2, 3)
        
        ly.addWidget(grp)

        # --- TABLA DE RESULTADOS (PLAN DE VUELO) ---
        self.tabla_cur = QTableWidget(0, 5)
        self.tabla_cur.setHorizontalHeaderLabels(["INICIO", "ACTO", "TRACK", "BPM / KEY", "MOTIVO TÉCNICO"])
        self.tabla_cur.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        ly.addWidget(self.tabla_cur)
        
        # Botón de Exportación de Hoja de Ruta
        self.btn_exp_plan = QPushButton("EXPORTAR GUÍA DE CABINA (.TXT)")
        self.btn_exp_plan.clicked.connect(self.export_guia_txt)
        ly.addWidget(self.btn_exp_plan)

    def run_curaduria_feedback(self):
        """Feedback visual para evitar bloqueos durante el proceso Camelot"""
        self.btn_gen.setText("PROCESANDO NARRATIVA..."); self.btn_gen.setEnabled(False)
        QTimer.singleShot(100, self.run_curaduria)

    def run_curaduria(self):
        """Dispara el motor de cascada v28.0 sobre la Maleta Central"""
        try:
            # Suministro global desde la base de datos
            pool = self.db.get_inventory_full()
            if not pool or len(pool) < 5:
                QMessageBox.warning(self, "CURADURÍA", "STOCK INSUFICIENTE: Debes analizar más temas en EL TALLER antes de generar una sesión.")
                self.btn_gen.setText("GENERAR PLAN DE VUELO"); self.btn_gen.setEnabled(True)
                return
            
            # Configuración enviada al motor
            config = {
                'luz': self.cb_luz.currentText(),
                'duracion': self.in_dur.text(),
                'densidad': self.cb_den.currentText(),
                'momento': self.cb_mom.currentText(),
                'estilo': self.cb_estilo_cur.currentText(),
                'usar_semilla': self.chk_semilla.isChecked(),
                'semilla': self.current_path
            }
            
            # Llamada al motor externo sellado
            self.current_playlist_data = curaduria_engine.generar_sesion_ufulu(pool, config)
            
            # Volcado de resultados en el Rack
            self.tabla_cur.setRowCount(0)
            fuente_item = QFont("Segoe UI", 10)
            
            for item in self.current_playlist_data:
                r = self.tabla_cur.rowCount()
                self.tabla_cur.insertRow(r)
                d_track = item['data'] # (filename, bpm, func, luz, estilo, path)
                
                # Mapeo: Tiempo, Fase del Arco, Nombre tema, Metadatos, Motivo
                valores = [item['tiempo'], item['acto'], os.path.basename(str(d_track[0])), f"{d_track[1]} BPM", item['motivo']]
                
                for col, val in enumerate(valores):
                    it = QTableWidgetItem(str(val))
                    it.setFont(fuente_item)
                    it.setForeground(QColor("#00ffcc")) # Turquesa para destacar el plan
                    self.tabla_cur.setItem(r, col, it)
                    
        except Exception as e:
            print(f"Fallo en motor narrativo: {e}")
        finally:
            self.btn_gen.setText("GENERAR PLAN DE VUELO")
            self.btn_gen.setEnabled(True)
    # --- [MÓDULO LÓGICO: PROCESADO DE SUMINISTRO Y TALLER] ---
    def on_folder_open(self, index):
        """Dispara el análisis forense sobre una maleta física (Pestaña 1)"""
        p = self.model.filePath(index)
        if os.path.isdir(p):
            self.tabla.setRowCount(0)
            self.todos_los_temas = []
            archivos = [os.path.join(p, f) for f in os.listdir(p) if f.lower().endswith(('.mp3', '.flac'))]
            
            if archivos and not self.db.is_folder_complete(p):
                # Lanzamos Splash de Extracción de ADN
                self.sf = widgets_ufulu.SplashForense(len(archivos), self)
                self.w = EngineUfulu(archivos)
                self.w.resultado.connect(self.add_f_to_db)
                self.w.progreso.connect(lambda v: self.sf.update_prog(v, len(archivos)))
                self.sf.show()
                self.w.start()
            elif archivos:
                # Carga instantánea desde la Base de Datos
                for t in self.db.get_tracks_in_folder(p):
                    # El Almacén ya trae la verdad guardada, no hay bpm_calculado extra
                    self.add_f_table(list(t), "ALMACÉN")
            
            self.model.layoutChanged.emit()

    def add_f_to_db(self, meta, adn, bpm_ufulu):
        """Recepción de la señal v32.0: Guarda en DB y actualiza Rack"""
        self.db.save_full_track(meta, adn)
        # Pasamos el meta y el bpm_ufulu para que la tabla muestre la comparativa
        self.add_f_table(meta, "NUEVO", bpm_ufulu)
        self.model.layoutChanged.emit()

    def add_f_table(self, meta, origen, bpm_calculado=None):
        """Mapeo de 8 columnas con la Verdad Híbrida (v32.0)"""
        # meta: [0:Título, 1:BPM_Persistencia, 2:Func, 3:Luz, 4:Estilo, 5:Ruta]
        path = meta[5] if isinstance(meta, list) else meta
        r = self.tabla.rowCount()
        self.tabla.insertRow(r)
        self.todos_los_temas.append(path)
        
        chk = QCheckBox(); chk.setChecked(True)
        self.tabla.setCellWidget(r, 0, chk)
        
        # Recuperamos el BPM del Tag (el que está en meta[1] por ahora)
        bt = meta[1] if isinstance(meta, list) else "0"
        # El calculado por el motor (o el que ya tenemos si es Almacén)
        bu = bpm_calculado if bpm_calculado else bt
        
        # Alerta Roja por incoherencia de estilo
        bg = QColor(139, 0, 0, 60) if not self.db.juzgar_coherencia_bpm(meta[4], bu) else None
        
        datos = [
            meta[0],        # Nombre/Título
            bt,             # BPM TAG (Original)
            bu,             # BPM UFULU (Calculado)
            meta[2],        # FUNCIÓN
            meta[3],        # ENERGÍA/LUZ
            meta[4],        # ESTILO
            origen          # ESTADO
        ]
        
        for i, v in enumerate(datos):
            it = QTableWidgetItem(str(v))
            it.setFont(QFont("Segoe UI", 10)); it.setForeground(QColor("#e1e1e1"))
            if bg: it.setBackground(bg)
            # Resalte visual de discrepancia entre Tag y Ufulu
            if i == 1 and str(bt) != "0" and str(bt) != str(bu):
                it.setForeground(QColor("#ff4444"))
            self.tabla.setItem(r, i + 1, it)

    def load_q(self, item):
        """Carga un track en el Quirófano Forense para cirugía ADN"""
        self.tabla.selectRow(item.row())
        p = self.todos_los_temas[item.row()]
        self.current_path = p
        self.adn_actual = self.db.get_adn(p)
        # Recuperamos marcadores y tags físicos
        _, _, _, self.cue_times, _ = tag_manager.leer_tags_completos(p)
        self.track_duration = librosa.get_duration(path=p)
        self.refresh_visuals()

    def run_triangulation(self):
        """Relanza el motor forense usando los 3 puntos marcados por los Knobs"""
        if not self.current_path: return
        try:
            # Extracción de valores de tiempo desde los Dials de 60k pasos
            v_pts = [float(dial.value() / 60000.0 * self.track_duration) for dial, lb in self.dials]
            
            # Lanzamos motor en modo manual sobre los 3 puntos exactos
            self.w = EngineUfulu([self.current_path], pt_a=v_pts[0], pt_b=v_pts[1], pt_c=v_pts[2])
            self.w.resultado.connect(lambda m, a: self.tabla.setItem(self.tabla.currentRow(), 3, QTableWidgetItem(str(m[1]))))
            self.w.start()
            print(f">>> Re-triangulando tema sobre puntos: {v_pts}")
        except Exception as e:
            print(f"Error en Triangulación: {e}")

    def inject_current(self):
        """Fija el ADN (BPM, Func, Cues) en el archivo físico actual"""
        row = self.tabla.currentRow()
        if row < 0: return
        bpm = self.tabla.item(row, 3).text()
        fnc = self.tabla.item(row, 4).text()
        if tag_manager.escribir_tags_ufulu(self.current_path, bpm, fnc, self.cue_times):
            QMessageBox.information(self, "RODEC SYSTEM", "ADN FIJADO CON ÉXITO EN EL SUMINISTRO.")

    def toggle_all(self):
        """Selección masiva de la maleta abierta"""
        for r in range(self.tabla.rowCount()):
            chk = self.tabla.cellWidget(r, 0)
            if chk: chk.setChecked(not chk.isChecked())

    def save_selected(self):
        """Inyección Dual v32.0: Sella archivo y actualiza Almacén Maestro"""
        confirm = QMessageBox.question(self, "SISTEMA RODEC", 
            "¿SOBRESCRIBIR TAGS Y ACTUALIZAR MALETA CON EL ANÁLISIS DE UFULU?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
        if confirm == QMessageBox.StandardButton.Yes:
            exitos, fallos = 0, 0
            for r in range(self.tabla.rowCount()):
                chk = self.tabla.cellWidget(r, 0)
                if chk and chk.isChecked():
                    try:
                        path_tema = self.todos_los_temas[r]
                        # Tomamos la verdad de las celdas (lo que ves es lo que se inyecta)
                        bpm_ufulu = self.tabla.item(r, 3).text()
                        func_ufulu = self.tabla.item(r, 4).text()
                        luz_ufulu = self.tabla.item(r, 5).text()
                        estilo_ufulu = self.tabla.item(r, 6).text()
                        
                        # 1. ESCRIBIR EN ARCHIVO FÍSICO
                        cues = self.cue_times if path_tema == self.current_path else None
                        if tag_manager.escribir_tags_ufulu(path_tema, bpm_ufulu, func_ufulu, cues):
                            
                            # 2. ACTUALIZAR BASE DE DATOS (Fusión de Inyección)
                            adn_pre = self.db.get_adn(path_tema)
                            meta_update = [
                                self.tabla.item(r, 1).text(), # Título
                                bpm_ufulu,                    # El BPM ahora es el de Ufulu
                                func_ufulu,
                                luz_ufulu,
                                estilo_ufulu,
                                path_tema
                            ]
                            self.db.save_full_track(meta_update, adn_pre)
                            exitos += 1
                        else:
                            fallos += 1
                    except: fallos += 1
            
            self.refrescar_maleta_tabla()
            QMessageBox.information(self, "SELLADO", f"PROCESO COMPLETADO:\n{exitos} Éxitos / {fallos} Fallos.")
    def gestor_pestanas(self, index):
        """Sincroniza los datos cuando el DJ cambia de módulo central"""
        if index == 1: # Entrada en MI MALETA
            self.refrescar_maleta_tabla()

    def cargar_desde_maleta_al_taller(self, index):
        """Doble clic en Inventario: Salto al Quirófano del Taller"""
        try:
            # Recuperamos la ruta real desde la columna 5
            path_real = self.tabla_maleta.item(index.row(), 5).text()
            if os.path.exists(path_real):
                self.current_path = path_real
                self.adn_actual = self.db.get_adn(path_real)
                # Recuperamos tags físicos y duración
                _, _, _, self.cue_times, _ = tag_manager.leer_tags_completos(path_real)
                self.track_duration = librosa.get_duration(path=path_real)
                
                # Salto automático a la pestaña Taller (0) y renderizado
                self.tabs.setCurrentIndex(0)
                self.refresh_visuals()
                print(f">>> Suministro cargado desde Almacén: {os.path.basename(path_real)}")
            else:
                QMessageBox.warning(self, "MALETA", "El archivo físico no existe en la ruta registrada.")
        except Exception as e:
            print(f"Error en carga desde maleta: {e}")

    def exportar_maleta_csv(self):
        """Generador de inventario industrial para Excel"""
        p, _ = QFileDialog.getSaveFileName(self, "Exportar Inventario", "", "Archivo CSV (*.csv)")
        if p:
            try:
                with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(["NOMBRE", "BPM", "FUNCIÓN", "LUZ", "ESTILO", "RUTA"])
                    for i in range(self.tabla_maleta.rowCount()):
                        writer.writerow([self.tabla_maleta.item(i, j).text() for j in range(6)])
                QMessageBox.information(self, "MALETA", "INVENTARIO EXPORTADO CON ÉXITO.")
            except Exception as e:
                print(f"Error en exportación: {e}")

    def export_guia_txt(self):
        """Guarda la Hoja de Ruta narrativa de Curaduría"""
        p, _ = QFileDialog.getSaveFileName(self, "Guardar Plan de Vuelo", "", "Texto (*.txt)")
        if p:
            config = {'maleta': "BIBLIOTECA GLOBAL", 'duracion': self.in_dur.text()}
            with open(p, "w", encoding="utf-8") as f:
                f.write(curaduria_engine.generar_texto_guia(self.current_playlist_data, config))

    # --- [MÓDULO GRÁFICO: ONDA Y MARCADORES] ---
    def on_waveform_click(self, event):
        """Marcado físico de HotCues sobre el visualizador"""
        if self.armed_cue:
            x_pulsado = event.position().x()
            ancho_total = self.view_onda.width()
            tiempo = (x_pulsado / ancho_total) * self.track_duration
            self.cue_times[self.armed_cue] = tiempo
            self.armed_cue = None
            self.refresh_visuals()

    def refresh_visuals(self):
        """Renderizado de Onda Turquesa y Línea Envolvente Blanca"""
        if not self.adn_actual or self.view_onda.width() <= 0: return
        w_v = int(self.scroll.viewport().width() * self.current_zoom)
        h_v = self.scroll.viewport().height()
        pix = QPixmap(w_v, h_v); pix.fill(QColor("#080808"))
        p = QPainter(pix)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            onda, rms_d, beat_d, centro = self.adn_actual["onda"], self.adn_actual["rms"], self.adn_actual["beat"], h_v // 2
            
            # 1. Dibujo de Onda Turquesa (Cuerpo)
            for i in range(len(onda)):
                x = int((i/len(onda)) * w_v); v_o = float(onda[i]); ap = int(v_o * (h_v * 0.7) / 2)
                if self.btn_stab.isChecked() and i < len(beat_d) and beat_d[i]:
                    p.setPen(QPen(QColor(255, 140, 0, 60), 1)); p.drawLine(x, 0, x, h_v)
                p.setPen(QPen(QColor("#00ffcc"), 1)); p.drawLine(x, centro-ap, x, centro+ap)
            
            # 2. Línea Blanca Envolvente (Trading Line)
            if self.btn_rms.isChecked() and len(rms_d) > 1:
                p.setPen(QPen(QColor(255, 255, 255, 220), 2)); poly = QPolygonF()
                for i in range(len(rms_d)):
                    px = (i / len(rms_d)) * w_v; py = centro - (float(rms_d[i]) * (h_v * 0.7) / 2)
                    poly.append(QPointF(px, py))
                p.drawPolyline(poly)
            
            # 3. Sondas de Knobs y Marcadores CUE
            for i, (dial, lb) in enumerate(self.dials):
                perc = dial.value()/60000.0; kx = int(perc*w_v); p.setOpacity(0.4); p.fillRect(kx-2,0,4,h_v,Qt.GlobalColor.white)
                tv = perc * self.track_duration; lb.setText(f"{int(tv//60):02d}:{int(tv%60):02d}:{int((tv%1)*100):02d}")
            for n_cue, t_cue in self.cue_times.items():
                if t_cue is not None:
                    xc = int((t_cue / self.track_duration) * w_v)
                    p.setPen(QPen(QColor(ufulu_style.CUE_COLORS[n_cue-1]), 3)); p.drawLine(xc, 0, xc, h_v)
        finally:
            p.end()
        self.view_onda.setPixmap(pix); self.view_onda.setFixedWidth(pix.width())

    def change_zoom(self, v):
        self.current_zoom = v
        # Si el zoom es mayor a 1, permitimos la barra horizontal de forma fija
        if v > 1:
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        else:
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.refresh_visuals()
    def asignar_cue_logic(self, n):
        """Lógica de armado y borrado de marcadores"""
        if self.cue_times[n] is not None:
            self.cue_times[n] = None; self.armed_cue = None
        else:
            self.armed_cue = n
        for i, b in enumerate(self.cue_btns):
            idx = i + 1
            if self.armed_cue == idx: b.setStyleSheet("background:#8b0000; color:white; border: 1px solid white;")
            elif self.cue_times[idx] is not None: b.setStyleSheet(f"background:{ufulu_style.CUE_COLORS[i]}; color:black;")
            else: b.setStyleSheet("")
        self.refresh_visuals()

    # ============================================================
    # === BLOQUE DE EXTENSIONES UFULU v33.7 ====================
    # ============================================================
    # Añadidas: drag&drop carpetas, auto-segmentar, sugerir siguiente,
    # exportadores PDF/M3U8/NML/XML con hotcues, salud, estadísticas,
    # plantillas, histórico+rating, modo AB, modo Performance,
    # filtros avanzados, atajos teclado.
    # Para activar: llamar a self._instalar_extensiones_v337() al final de __init__
    # ============================================================

    def _instalar_extensiones_v337(self):
        """Instala drag&drop + atajos. Llamar al final de __init__."""
        self.setAcceptDrops(True)
        # Atajos cabina
        for k, fn in [("P", self._v337_play_pause), ("Space", self._v337_play_pause),
                      ("S", self._v337_stop), ("Ctrl+G", self._v337_generar)]:
            try: QShortcut(QKeySequence(k), self).activated.connect(fn)
            except Exception: pass
        for i in range(3):
            try:
                QShortcut(QKeySequence(f"Ctrl+{i+1}"), self).activated.connect(
                    lambda idx=i: self.tabs.setCurrentIndex(idx))
            except Exception: pass

    def _v337_play_pause(self):
        if hasattr(self, '_cur_player'):
            try:
                if self._cur_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                    self._cur_player.pause()
                else:
                    self._cur_player.play()
            except Exception: pass

    def _v337_stop(self):
        if hasattr(self, '_cur_player'):
            try: self._cur_player.stop()
            except Exception: pass

    def _v337_generar(self):
        if hasattr(self, 'btn_gen'):
            try: self.btn_gen.click()
            except Exception: pass

    # --- DRAG & DROP CARPETAS ---
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

    # --- AUTO-SEGMENTAR ---
    def auto_segmentar_handler(self):
        if not self.current_path or not self.adn_actual:
            QMessageBox.warning(self, "AUTO-SEGMENTAR", "Carga primero un tema.")
            return
        rms_v = self.adn_actual.get("rms", [])
        if not rms_v or self.track_duration <= 0:
            QMessageBox.warning(self, "AUTO-SEGMENTAR", "RMS insuficiente.")
            return
        seg = detectar_segmentos_estructurales(
            rms_v, self.adn_actual.get("beat", []), self.track_duration)
        if not seg:
            QMessageBox.information(self, "AUTO-SEGMENTAR", "No se detectó estructura.")
            return
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
        QMessageBox.information(self, "AUTO-SEGMENTAR",
                                "Segmentos aplicados como CUEs:\n\n" + "\n".join(cambios))

    # --- SUGERIR SIGUIENTE ---
    def sugerir_siguiente_handler(self):
        if not self.current_path:
            QMessageBox.warning(self, "SUGERIR", "Carga primero un tema.")
            return
        pool = self.db.get_inventory_full()
        track_actual = next((t for t in pool if t[5] == self.current_path), None)
        if not track_actual:
            QMessageBox.warning(self, "SUGERIR", "No está en la maleta. Fíjalo primero.")
            return
        sugs = curaduria_engine.sugerir_siguiente_track(track_actual, pool, 8)
        if not sugs:
            QMessageBox.information(self, "SUGERIR", "Sin candidatos compatibles.")
            return
        msg = "MEJORES SUGERENCIAS:\n\n"
        for i, s in enumerate(sugs[:5], 1):
            t = s['track']
            msg += f"{i}. N{s['nivel']} - {os.path.basename(str(t[0]))[:40]}\n"
            msg += f"   {t[1]} BPM | KEY {t[7]} | Δ={s['delta_bpm']:.1f} | {s['motivo']}\n\n"
        QMessageBox.information(self, "SIGUIENTE TEMA", msg)

    # --- SALUD MALETA ---
    def abrir_diagnostico_salud(self):
        problemas = self.db.diagnosticar_salud_maleta()
        if not problemas:
            QMessageBox.information(self, "SALUD", "Todos los temas en orden.")
            return
        msg = f"{len(problemas)} TEMAS CON PROBLEMAS:\n\n"
        for path, fn, probs in problemas[:30]:
            msg += f"• {fn[:40]}: {', '.join(probs)}\n"
        if len(problemas) > 30:
            msg += f"\n... y {len(problemas)-30} más"
        QMessageBox.warning(self, "SALUD MALETA", msg)

    # --- ESTADÍSTICAS ---
    def abrir_dashboard_estadisticas(self):
        s = self.db.get_stats()
        if s['total'] == 0:
            QMessageBox.information(self, "STATS", "Sin datos.")
            return
        msg = f"TOTAL: {s['total']} TEMAS\n\n"
        msg += f"DÍA: {s['luz_dist']['DÍA']} | NOCHE: {s['luz_dist']['NOCHE']}\n\n"
        msg += "TOP 5 ESTILOS:\n"
        for est, c in s['estilo_dist'][:5]:
            msg += f"  • {est}: {c}\n"
        msg += "\nTOP 5 BUCKETS BPM:\n"
        for b, c in sorted(s['bpm_hist'].items(), key=lambda x: -x[1])[:5]:
            msg += f"  • {b}-{b+5} BPM: {c}\n"
        QMessageBox.information(self, "ESTADÍSTICAS", msg)

    # --- EXPORTADORES ---
    def _recolectar_cues_playlist(self):
        out = {}
        if not getattr(self, 'current_playlist_data', None):
            return out
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
            except Exception: pass
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
        except Exception as e:
            QMessageBox.critical(self, "EXPORTAR", str(e))

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
        except Exception as e:
            QMessageBox.critical(self, "EXPORTAR", str(e))

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
            playlist_exporters.exportar_pdf_sesion(
                self.current_playlist_data, p, params=params,
                rating=0, notas_sesion="", notas_por_path=notas_path)
            QMessageBox.information(self, "EXPORTAR", f"PDF:\n{p}")
        except ImportError:
            QMessageBox.critical(self, "EXPORTAR", "Falta reportlab.\npip install reportlab")
        except Exception as e:
            QMessageBox.critical(self, "EXPORTAR", str(e))

    def _exp_generic(self, fn_export, ext, descr):
        if not getattr(self, 'current_playlist_data', None):
            QMessageBox.warning(self, "EXPORTAR", "Genera un Plan primero."); return
        p, _ = QFileDialog.getSaveFileName(self, f"Exportar {descr}", "", f"{descr} (*.{ext})")
        if not p: return
        if not p.lower().endswith(f".{ext}"): p += f".{ext}"
        try:
            fn_export(self.current_playlist_data, p)
            QMessageBox.information(self, "EXPORTAR", f"OK: {p}")
        except Exception as e:
            QMessageBox.critical(self, "EXPORTAR", str(e))

# ============================================================
# === FIN BLOQUE EXTENSIONES v33.7 =========================
# ============================================================

# --- [IGNICIÓN BÚNKER DE SEGURIDAD] ---
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
        global main_instance
        main_window = MainApp(sw.selected_path, db_master)
        main_window.show()
        sys.exit(app.exec())
