# collection_manager.py
# UFULU RODEC EDITION - ALMACÉN MAESTRO SQLITE v33.7
# =====================================================
# Persistencia local con backup diario automático,
# tablas: tracks, config, templates, history.
# =====================================================

import os
import json
import sqlite3
import shutil
from datetime import datetime, timedelta
import sys
from genre_definitions import RANGOS_BPM

DB_FILENAME = "ufulu_almacen.db"
BACKUP_DIRNAME = "ufulu_backups"



def _db_path() -> str:
    """Ruta de la BD junto al ejecutable / al lado de main.py."""
    if getattr(sys, 'frozen', False):
        # Compilado con PyInstaller: usar el directorio del .exe
        base = os.path.dirname(sys.executable)
    else:
        # En desarrollo: usar el directorio del script
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, DB_FILENAME)


def _backup_dir() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(base, BACKUP_DIRNAME)
    os.makedirs(d, exist_ok=True)
    return d




class CollectionManager:
    """Almacén centralizado del DJ. Wrapper SQLite v33.7."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or _db_path()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        self._backup_diario()

    # =====================================================
    # SCHEMA + MIGRACIONES NO DESTRUCTIVAS
    # =====================================================
    def _init_schema(self):
        c = self._conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS tracks (
                path TEXT PRIMARY KEY,
                filename TEXT,
                bpm TEXT,
                funcion TEXT,
                color TEXT,
                estilo TEXT,
                wave_data TEXT,
                analyzed INTEGER DEFAULT 1,
                energia INTEGER DEFAULT 5,
                key_camelot TEXT DEFAULT '-',
                notas TEXT DEFAULT '',
                bpm_confidence INTEGER DEFAULT 0,
                fecha_analisis TEXT
            );
            CREATE TABLE IF NOT EXISTS config (
                clave TEXT PRIMARY KEY,
                valor TEXT
            );
            CREATE TABLE IF NOT EXISTS templates (
                name TEXT PRIMARY KEY,
                luz TEXT,
                momento TEXT,
                estilo TEXT,
                densidad TEXT,
                duracion TEXT
            );
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                params TEXT,
                rating INTEGER DEFAULT 0,
                notas_sesion TEXT DEFAULT '',
                playlist_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tracks_estilo ON tracks(estilo);
            CREATE INDEX IF NOT EXISTS idx_tracks_color  ON tracks(color);
        """)
        # Migraciones suaves (en bibliotecas antiguas)
        for col, ddl in [
            ("energia",        "ALTER TABLE tracks ADD COLUMN energia INTEGER DEFAULT 5"),
            ("key_camelot",    "ALTER TABLE tracks ADD COLUMN key_camelot TEXT DEFAULT '-'"),
            ("notas",          "ALTER TABLE tracks ADD COLUMN notas TEXT DEFAULT ''"),
            ("bpm_confidence", "ALTER TABLE tracks ADD COLUMN bpm_confidence INTEGER DEFAULT 0"),
            ("fecha_analisis", "ALTER TABLE tracks ADD COLUMN fecha_analisis TEXT"),
        ]:
            try:
                c.execute(ddl)
            except sqlite3.OperationalError:
                pass
        self._conn.commit()

    # =====================================================
    # BACKUP DIARIO
    # =====================================================
    def _backup_diario(self):
        """Copia la BD una vez al día. Mantiene últimos 14."""
        try:
            if not os.path.exists(self.db_path):
                return
            hoy = datetime.now().strftime("%Y-%m-%d")
            destino = os.path.join(_backup_dir(), f"ufulu_{hoy}.db")
            if not os.path.exists(destino):
                shutil.copy2(self.db_path, destino)
                self._purgar_backups_antiguos(retener_dias=14)
        except Exception as e:
            print(f"[BACKUP] aviso: {e}")

    def _purgar_backups_antiguos(self, retener_dias: int = 14):
        try:
            corte = datetime.now() - timedelta(days=retener_dias)
            for f in os.listdir(_backup_dir()):
                p = os.path.join(_backup_dir(), f)
                if os.path.isfile(p):
                    if datetime.fromtimestamp(os.path.getmtime(p)) < corte:
                        os.remove(p)
        except Exception:
            pass

    # =====================================================
    # CONFIG
    # =====================================================
    def get_default_path(self) -> str:
        c = self._conn.cursor()
        row = c.execute("SELECT valor FROM config WHERE clave='default_path'").fetchone()
        return row["valor"] if row else ""

    def set_default_path(self, ruta: str):
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO config(clave,valor) VALUES('default_path',?) "
            "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
            (ruta or "",)
        )
        self._conn.commit()

    # =====================================================
    # TRACKS
    # =====================================================
    def track_exists(self, path: str) -> bool:
        c = self._conn.cursor()
        return c.execute("SELECT 1 FROM tracks WHERE path=?", (path,)).fetchone() is not None

    def is_folder_complete(self, path_carpeta: str) -> bool:
        """True si todos los .mp3/.flac de la carpeta están analizados."""
        try:
            if not os.path.isdir(path_carpeta):
                return False
            archivos = [
                os.path.join(path_carpeta, f)
                for f in os.listdir(path_carpeta)
                if f.lower().endswith(('.mp3', '.flac', '.wav', '.webm', '.opus'))
            ]
            if not archivos:
                return False
            c = self._conn.cursor()
            for a in archivos:
                row = c.execute("SELECT 1 FROM tracks WHERE path=?", (a,)).fetchone()
                if not row:
                    return False
            return True
        except Exception:
            return False

    def save_full_track(self, meta, adn):
        """
        Guarda/actualiza un track completo.
        meta: [filename, bpm, funcion, color, estilo, path,
               energia?, key_camelot?, bpm_confidence?]
        adn:  {"onda":[], "rms":[], "beat":[]}
        """
        try:
            filename = str(meta[0]) if len(meta) > 0 else ""
            bpm      = str(meta[1]) if len(meta) > 1 else "0"
            funcion  = str(meta[2]) if len(meta) > 2 else "-"
            color    = str(meta[3]) if len(meta) > 3 else "NOCHE"
            estilo   = str(meta[4]) if len(meta) > 4 else "*"
            path     = str(meta[5]) if len(meta) > 5 else ""
            energia  = int(meta[6]) if len(meta) > 6 and str(meta[6]).isdigit() else 5
            key      = str(meta[7]) if len(meta) > 7 else "-"
            conf     = int(meta[8]) if len(meta) > 8 and str(meta[8]).isdigit() else 0

            wave_json = json.dumps(adn or {"onda": [], "rms": [], "beat": []})
            ahora = datetime.now().isoformat(timespec="seconds")

            c = self._conn.cursor()
            c.execute("""
                INSERT INTO tracks(
                    path, filename, bpm, funcion, color, estilo,
                    wave_data, analyzed, energia, key_camelot,
                    bpm_confidence, fecha_analisis
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    filename=excluded.filename,
                    bpm=excluded.bpm,
                    funcion=excluded.funcion,
                    color=excluded.color,
                    estilo=excluded.estilo,
                    wave_data=excluded.wave_data,
                    analyzed=1,
                    energia=excluded.energia,
                    key_camelot=excluded.key_camelot,
                    bpm_confidence=excluded.bpm_confidence,
                    fecha_analisis=excluded.fecha_analisis
            """, (path, filename, bpm, funcion, color, estilo,
                  wave_json, energia, key, conf, ahora))
            self._conn.commit()
        except Exception as e:
            print(f"[DB] save_full_track fallo: {e}")

    def get_tracks_in_folder(self, carpeta: str):
        """Devuelve filas tipo (filename, bpm, funcion, color, estilo, path, energia, key, conf)."""
        c = self._conn.cursor()
        like = carpeta.rstrip(os.sep) + os.sep + "%"
        rows = c.execute("""
            SELECT filename, bpm, funcion, color, estilo, path,
                   energia, key_camelot, bpm_confidence
            FROM tracks
            WHERE path LIKE ?
            ORDER BY filename ASC
        """, (like,)).fetchall()
        return [tuple(r) for r in rows]

    def get_inventory_full(self):
        """Inventario global. Tupla:
        (filename, bpm, funcion, color, estilo, path, energia, key_camelot, bpm_confidence)."""
        c = self._conn.cursor()
        rows = c.execute("""
            SELECT filename, bpm, funcion, color, estilo, path,
                   energia, key_camelot, bpm_confidence
            FROM tracks
            ORDER BY filename ASC
        """).fetchall()
        return [tuple(r) for r in rows]

    def get_adn(self, path: str):
        c = self._conn.cursor()
        row = c.execute("SELECT wave_data FROM tracks WHERE path=?", (path,)).fetchone()
        if not row or not row["wave_data"]:
            return {"onda": [], "rms": [], "beat": []}
        try:
            return json.loads(row["wave_data"])
        except Exception:
            return {"onda": [], "rms": [], "beat": []}

    # =====================================================
    # NOTAS POR TEMA
    # =====================================================
    def get_notas(self, path: str) -> str:
        c = self._conn.cursor()
        row = c.execute("SELECT notas FROM tracks WHERE path=?", (path,)).fetchone()
        return (row["notas"] or "") if row else ""

    def set_notas(self, path: str, notas: str):
        c = self._conn.cursor()
        c.execute("UPDATE tracks SET notas=? WHERE path=?", (notas or "", path))
        self._conn.commit()

    # =====================================================
    # COHERENCIA BPM ↔ ESTILO
    # =====================================================
    def juzgar_coherencia_bpm(self, estilo: str, bpm) -> bool:
        try:
            b = float(bpm)
        except Exception:
            return True
        if not estilo:
            return True
        clave = str(estilo).upper()
        for k, (lo, hi) in RANGOS_BPM.items():
            if k in clave:
                return lo <= b <= hi
        return True  # estilos desconocidos: no marcamos rojo

    # =====================================================
    # SALUD DE LA MALETA
    # =====================================================
    def diagnosticar_salud_maleta(self):
        """Detecta problemas: BPM=0, FUNCIÓN=ERROR, archivo perdido,
        BPM incoherente con estilo, ausencia de KEY."""
        problemas = []
        for r in self.get_inventory_full():
            fn, bpm, func, color, estilo, path, energia, key, conf = r
            probs = []
            if not path or not os.path.exists(path):
                probs.append("ARCHIVO PERDIDO")
            try:
                if int(float(bpm)) <= 0:
                    probs.append("BPM=0")
            except Exception:
                probs.append("BPM INVÁLIDO")
            if str(func).upper() == "ERROR":
                probs.append("FUNC=ERROR")
            if not self.juzgar_coherencia_bpm(estilo, bpm):
                probs.append("BPM↔ESTILO")
            if not key or key == "-":
                probs.append("SIN KEY")
            try:
                if int(conf) < 30:
                    probs.append(f"CONFIANZA BAJA ({conf}%)")
            except Exception:
                pass
            if probs:
                problemas.append((path, fn, probs))
        return problemas

    # =====================================================
    # ESTADÍSTICAS DASHBOARD
    # =====================================================
    def get_stats(self) -> dict:
        rows = self.get_inventory_full()
        out = {
            "total": len(rows),
            "luz_dist": {"DÍA": 0, "NOCHE": 0},
            "estilo_dist": [],
            "bpm_hist": {},
            "energia_avg": 0.0,
        }
        if not rows:
            return out
        estilos = {}
        energias = []
        for fn, bpm, func, color, estilo, path, ener, key, conf in rows:
            # luz
            c = (color or "").upper()
            if "DÍA" in c or "DIA" in c: out["luz_dist"]["DÍA"] += 1
            else: out["luz_dist"]["NOCHE"] += 1
            # estilo
            estilos[estilo or "?"] = estilos.get(estilo or "?", 0) + 1
            # bpm bucket de 5
            try:
                b = int(float(bpm))
                bucket = (b // 5) * 5
                out["bpm_hist"][bucket] = out["bpm_hist"].get(bucket, 0) + 1
            except Exception:
                pass
            # energia
            try: energias.append(int(ener))
            except Exception: pass
        out["estilo_dist"] = sorted(estilos.items(), key=lambda x: -x[1])
        if energias:
            out["energia_avg"] = round(sum(energias) / len(energias), 2)
        return out

    # =====================================================
    # TEMPLATES (PLANTILLAS DE SESIÓN)
    # =====================================================
    def listar_templates(self):
        c = self._conn.cursor()
        rows = c.execute(
            "SELECT name, luz, momento, estilo, densidad, duracion "
            "FROM templates ORDER BY name ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    def guardar_template(self, name: str, luz: str, momento: str,
                         estilo: str, densidad: str, duracion: str):
        c = self._conn.cursor()
        c.execute("""
            INSERT INTO templates(name,luz,momento,estilo,densidad,duracion)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(name) DO UPDATE SET
                luz=excluded.luz, momento=excluded.momento,
                estilo=excluded.estilo, densidad=excluded.densidad,
                duracion=excluded.duracion
        """, (name, luz, momento, estilo, densidad, duracion))
        self._conn.commit()

    def borrar_template(self, name: str):
        c = self._conn.cursor()
        c.execute("DELETE FROM templates WHERE name=?", (name,))
        self._conn.commit()

    # =====================================================
    # HISTORY
    # =====================================================
    def registrar_sesion(self, params: dict, playlist: list,
                         rating: int = 0, notas: str = "") -> int:
        c = self._conn.cursor()
        c.execute("""
            INSERT INTO history(timestamp, params, rating, notas_sesion, playlist_json)
            VALUES(?,?,?,?,?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            json.dumps(params or {}, ensure_ascii=False),
            int(rating or 0),
            notas or "",
            json.dumps(playlist or [], default=str, ensure_ascii=False),
        ))
        self._conn.commit()
        return c.lastrowid

    def listar_historial(self, limit: int = 50):
        c = self._conn.cursor()
        rows = c.execute("""
            SELECT id, timestamp, params, rating, notas_sesion
            FROM history
            ORDER BY id DESC
            LIMIT ?
        """, (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def actualizar_rating_sesion(self, sesion_id: int, rating: int, notas: str = ""):
        c = self._conn.cursor()
        c.execute(
            "UPDATE history SET rating=?, notas_sesion=? WHERE id=?",
            (int(rating or 0), notas or "", int(sesion_id))
        )
        self._conn.commit()

    # =====================================================
    # CIERRE
    # =====================================================
    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass
