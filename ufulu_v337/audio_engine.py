# audio_engine.py
# MOTOR DE INTELIGENCIA FORENSE UFULU: v33.7 - REJILLA FIEL AL KICK + CONFIDENCE + SEGMENTACIÓN
# PROTOCOLO DE RIGOR: PROHIBIDO RESUMIR - FILTROS ANALÓGICOS PROPIOS

import os
import numpy as np
import librosa
from scipy.signal import butter, lfilter, find_peaks
from PyQt6.QtCore import QThread, pyqtSignal
import tag_manager


# === ENERGÍA 1-10 (DÍA 1-5 / NOCHE 6-10) v33.5 ===
def calcular_energia_1_10(rms_v, bpm, densidad_pct, centroide_hz):
    """Score 1-10: combinación ponderada de RMS, BPM, densidad y brillo."""
    try:
        rms_score = min(1.0, float(np.mean(rms_v)) / 0.5) if rms_v else 0
        bpm_score = max(0, min(1.0, (float(bpm) - 100) / 50))
        dens_score = float(densidad_pct)
        cent_score = max(0, min(1.0, (float(centroide_hz) - 1500) / 4000))
        weighted = (0.30 * rms_score + 0.25 * bpm_score
                    + 0.25 * dens_score + 0.20 * cent_score)
        return max(1, min(10, int(round(weighted * 10))))
    except Exception:
        return 5


def calcular_estabilidad_ritmica(beat_v, ventana_picos=8):
    """Coeficiente de variación entre intervalos de pico (1.0=estable, 0=caótico)."""
    if not beat_v or len(beat_v) < 4:
        return 0.5
    try:
        idx_picos = [i for i, b in enumerate(beat_v) if b]
        if len(idx_picos) < 4:
            return 0.5
        intervalos = np.diff(idx_picos[:ventana_picos * 2])
        if len(intervalos) == 0:
            return 0.5
        media = np.mean(intervalos); std = np.std(intervalos)
        if media <= 0:
            return 0.5
        cv = std / media
        return max(0.0, min(1.0, 1.0 - cv))
    except Exception:
        return 0.5


class EngineUfulu(QThread):
    """Hilo de procesado forense v33.7."""
    progreso = pyqtSignal(int)
    # list: [Título, BPM_Tag, Función, Luz, Estilo, Ruta, Energía, Key, Confidence]
    # dict: {"onda":[], "rms":[], "beat":[]}
    # str:  "BPM_UFULU"
    resultado = pyqtSignal(list, dict, str)

    def __init__(self, archivos, pt_a=None, pt_b=None, pt_c=None):
        super().__init__()
        self.archivos = archivos
        self.sondas_manuales = [pt_a, pt_b, pt_c]

    def aplicar_filtro_ufulu(self, data, tipo, freq, sr):
        nyq = 0.5 * sr
        if freq >= nyq:
            freq = nyq - 100
        normal_cutoff = freq / nyq
        b, a = butter(2, normal_cutoff, btype=tipo, analog=False)
        return lfilter(b, a, data)

    def analizar_sondeo(self, y, sr):
        """
        v33.7 - REJILLA FIEL AL KICK + CONFIDENCE
        Devuelve (bpm, confidence_pct).
          - El kick manda. Los hats SOLO rellenan huecos.
          - confidence: 0-100 (kicks_reales / slots_totales).
        """
        banda_baja = self.aplicar_filtro_ufulu(y, 'low', 150, sr)
        banda_alta = self.aplicar_filtro_ufulu(y, 'high', 5000, sr)
        env_baja = np.abs(banda_baja)
        env_alta = np.abs(banda_alta)
        distancia_minima = int(sr * 0.3)

        umbral_baja = np.max(env_baja) * 0.20 if np.max(env_baja) > 0 else 0.1
        picos_bombo, _ = find_peaks(env_baja, distance=distancia_minima, prominence=umbral_baja)
        if len(picos_bombo) < 3:
            return 0.0, 0

        intervalos_kick = np.diff(picos_bombo)
        intervalo_grid = float(np.median(intervalos_kick))
        if intervalo_grid <= 0:
            return 0.0, 0

        umbral_alta = np.max(env_alta) * 0.25 if np.max(env_alta) > 0 else 0.1
        picos_brillo, _ = find_peaks(env_alta, distance=distancia_minima, prominence=umbral_alta)

        margen_grid = intervalo_grid * 0.20
        puntos_validados = list(picos_bombo)
        slots_esperados_total = 0
        slots_rellenos_hat = 0

        for i in range(len(picos_bombo) - 1):
            gap = picos_bombo[i + 1] - picos_bombo[i]
            n_slots = int(round(gap / intervalo_grid))
            if n_slots >= 2:
                slots_esperados_total += (n_slots - 1)
                for k in range(1, n_slots):
                    pos_esperada = picos_bombo[i] + k * intervalo_grid
                    candidatos = [h for h in picos_brillo if abs(h - pos_esperada) < margen_grid]
                    if candidatos:
                        mejor = min(candidatos, key=lambda h: abs(h - pos_esperada))
                        puntos_validados.append(int(mejor))
                        slots_rellenos_hat += 1

        puntos_validados = sorted(set(puntos_validados))
        if len(puntos_validados) < 2:
            return 0.0, 0

        intervalos_segundos = np.diff(puntos_validados) / sr
        bpm_ventana = 60.0 / np.median(intervalos_segundos)
        if bpm_ventana < 40 or bpm_ventana > 220:
            return 0.0, 0

        kicks_reales = len(picos_bombo)
        slots_total = kicks_reales + slots_esperados_total
        confidence = int(round(100 * kicks_reales / slots_total)) if slots_total > 0 else 100
        confidence = max(0, min(100, confidence))
        return bpm_ventana, confidence

    def determinar_funcion_densidad(self, rms_v, beat_v):
        promedio_presion = np.mean(rms_v) if len(rms_v) > 0 else 0.0
        promedio_densidad = np.mean(beat_v) if len(beat_v) > 0 else 0.0
        umbral_presion = 0.12
        umbral_densidad = 0.15
        if promedio_presion < umbral_presion:
            return "1. OPEN" if promedio_densidad < umbral_densidad else "2. HOLD"
        else:
            return "3. SHIFT" if promedio_densidad < umbral_densidad else "4. PEAK"

    def determinar_luz_espectral(self, ruta, dur_total, sr_proc):
        try:
            offset_centro = dur_total / 2.0 if dur_total > 40 else 0
            y_muestra, _ = librosa.load(ruta, offset=offset_centro, duration=30, sr=sr_proc)
            centroide = np.mean(librosa.feature.spectral_centroid(y=y_muestra, sr=sr_proc))
            return ("DÍA" if centroide > 2200 else "NOCHE", float(centroide))
        except Exception:
            return ("NOCHE", 0.0)

    def calcular_key_camelot(self, ruta, dur_total, sr_proc):
        """Estimación de Camelot Key vía chroma + Krumhansl. Devuelve string '5A'/'8B' o '-'."""
        try:
            offset_centro = dur_total / 2.0 if dur_total > 40 else 0
            y_k, _ = librosa.load(ruta, offset=offset_centro, duration=30, sr=sr_proc)
            chroma = librosa.feature.chroma_stft(y=y_k, sr=sr_proc)
            chroma_mean = np.mean(chroma, axis=1)
            # Perfiles Krumhansl
            mayor = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
            menor = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
            mejor_score, mejor_idx, mejor_modo = -1, 0, 'M'
            for i in range(12):
                rolled_M = np.roll(mayor, i)
                rolled_m = np.roll(menor, i)
                sM = np.corrcoef(chroma_mean, rolled_M)[0, 1]
                sm = np.corrcoef(chroma_mean, rolled_m)[0, 1]
                if sM > mejor_score: mejor_score, mejor_idx, mejor_modo = sM, i, 'M'
                if sm > mejor_score: mejor_score, mejor_idx, mejor_modo = sm, i, 'm'
            # Tonalidad PC -> Camelot
            mapa_camelot_M = {0:'8B',1:'3B',2:'10B',3:'5B',4:'12B',5:'7B',
                              6:'2B',7:'9B',8:'4B',9:'11B',10:'6B',11:'1B'}
            mapa_camelot_m = {0:'5A',1:'12A',2:'7A',3:'2A',4:'9A',5:'4A',
                              6:'11A',7:'6A',8:'1A',9:'8A',10:'3A',11:'10A'}
            return mapa_camelot_M[mejor_idx] if mejor_modo == 'M' else mapa_camelot_m[mejor_idx]
        except Exception:
            return "-"

    def run(self):
        for indice, ruta in enumerate(self.archivos):
            try:
                sr_proc = 22050
                if not os.path.exists(ruta):
                    continue
                dur_total = librosa.get_duration(path=ruta)

                t_bpm, t_titulo, t_artista, t_cues, t_genero = tag_manager.leer_tags_completos(ruta)
                bpm_referencia = float(t_bpm) if (t_bpm and t_bpm != "0") else 120.0
                nombre_mostrable = t_titulo if (t_titulo and t_titulo.strip()) else os.path.basename(ruta)
                genero_mostrable = t_genero if (t_genero and t_genero.strip()) else "GÉNERO DESCONOCIDO"

                # SONDEO TRIPLE
                resultados_sondas = []
                resultados_confidence = []
                p_manuales = [p for p in self.sondas_manuales if p is not None]
                segundos_ventana = 20
                if p_manuales:
                    puntos_anclaje = p_manuales
                else:
                    puntos_anclaje = [60.0, dur_total / 2.0, max(0.0, dur_total - 60.0)]

                for pt in puntos_anclaje:
                    if pt < dur_total:
                        offset_v = min(float(pt), max(0.0, dur_total - segundos_ventana))
                        y_v, _ = librosa.load(ruta, offset=offset_v, duration=segundos_ventana, sr=sr_proc)
                        res_ventana, conf_ventana = self.analizar_sondeo(y_v, sr_proc)
                        if res_ventana > 0:
                            resultados_sondas.append(res_ventana)
                            resultados_confidence.append(conf_ventana)

                # RESOLUCIÓN POR VOTOS
                if len(resultados_sondas) == 3:
                    r1, r2, r3 = resultados_sondas
                    if abs(r1-r2) < 0.5 and abs(r2-r3) < 0.5:
                        bpm_final = (r1 + r2 + r3) / 3
                    elif abs(r1-r2) < 0.5: bpm_final = (r1 + r2) / 2
                    elif abs(r1-r3) < 0.5: bpm_final = (r1 + r3) / 2
                    elif abs(r2-r3) < 0.5: bpm_final = (r2 + r3) / 2
                    else:
                        bpm_final = min(resultados_sondas, key=lambda x: abs(x - bpm_referencia))
                elif len(resultados_sondas) == 2:
                    r1, r2 = resultados_sondas
                    if abs(r1-r2) < 0.5: bpm_final = (r1 + r2) / 2
                    else: bpm_final = min(resultados_sondas, key=lambda x: abs(x - bpm_referencia))
                elif len(resultados_sondas) == 1:
                    bpm_final = resultados_sondas[0]
                else:
                    bpm_final = bpm_referencia

                bpm_ufulu_str = str(int(round(bpm_final)))
                confidence_final = int(np.median(resultados_confidence)) if resultados_confidence else 0

                # ADN VISUAL
                y_draw, _ = librosa.load(ruta, duration=dur_total, sr=4000)
                if y_draw.size == 0:
                    self.resultado.emit(
                        [nombre_mostrable, "0", "ERROR", "NOCHE", genero_mostrable, ruta, 5, "-", 0],
                        {"onda":[], "rms":[], "beat":[]}, "0")
                    continue

                pts_objetivo = 3000
                chunks_raw = np.array_split(y_draw, pts_objetivo)
                onda_v = [float(np.max(np.abs(c))) for c in chunks_raw]
                rms_raw = [float(np.sqrt(np.mean(c**2))) for c in chunks_raw]
                ventana_suave = np.ones(7) / 7
                rms_suave = np.convolve(rms_raw, ventana_suave, mode='same')
                max_ener = np.max(rms_suave) if np.max(rms_suave) > 0 else 1.0
                rms_v = [min(1.0, float(v / max_ener) * 1.2) for v in rms_suave]
                umbral_ritmo = np.mean(onda_v) * 1.3
                beat_v = [1 if v > umbral_ritmo else 0 for v in onda_v]
                onda_v = [v if np.isfinite(v) else 0.0 for v in onda_v]
                rms_v = [v if np.isfinite(v) else 0.0 for v in rms_v]

                # CLASIFICACIÓN
                funcion_final = self.determinar_funcion_densidad(rms_v, beat_v)
                luz_final, centroide_hz = self.determinar_luz_espectral(ruta, dur_total, sr_proc)
                key_camelot = self.calcular_key_camelot(ruta, dur_total, sr_proc)

                # ENERGÍA 1-10
                densidad_pct = sum(beat_v) / len(beat_v) if beat_v else 0
                energia_final = calcular_energia_1_10(rms_v, bpm_final, densidad_pct, centroide_hz)
                # Mapeo luz -> energía: 1-5 DÍA, 6-10 NOCHE (forzar coherencia)
                if energia_final <= 5: luz_final = "DÍA"
                else: luz_final = "NOCHE"

                adn_dict = {"onda": onda_v, "rms": rms_v, "beat": beat_v}
                meta_final = [
                    nombre_mostrable,
                    t_bpm if (t_bpm and t_bpm != "0") else bpm_ufulu_str,
                    funcion_final,
                    luz_final,
                    genero_mostrable,
                    ruta,
                    energia_final,
                    key_camelot,
                    confidence_final
                ]
                self.resultado.emit(meta_final, adn_dict, bpm_ufulu_str)

            except Exception as e:
                print(f"FALLO CANAL {indice}: {os.path.basename(ruta)} -> {e}")
                self.resultado.emit(
                    [os.path.basename(ruta), "0", "ERROR", "NOCHE", "UNK", ruta, 5, "-", 0],
                    {"onda":[], "rms":[], "beat":[]}, "0")

            self.progreso.emit(indice + 1)


# ======================================================================
# DETECTOR DE SEGMENTOS ESTRUCTURALES UFULU v33.7
# ======================================================================
def detectar_segmentos_estructurales(rms_v, beat_v, duracion_seg):
    """
    Detecta INTRO / BUILD / DROP / BREAK / OUTRO desde el RMS persistido.
    Devuelve dict {nombre: tiempo_seg}.
    """
    if not rms_v or len(rms_v) < 50 or duracion_seg <= 0:
        return {}
    arr = np.array(rms_v, dtype=float)
    n = len(arr)
    ventana = max(7, n // 60)
    kernel = np.ones(ventana) / ventana
    s = np.convolve(arr, kernel, mode="same")
    media = float(np.mean(s)) if np.mean(s) > 0 else 0.001
    maxv = float(np.max(s)) if np.max(s) > 0 else 0.001

    def _idx_a_seg(idx):
        return float(idx / n * duracion_seg)

    seg = {}
    umbral_intro = media * 0.6
    for i in range(n):
        if s[i] > umbral_intro:
            seg["INTRO"] = _idx_a_seg(i); break

    umbral_drop = maxv * 0.85
    sostenido = max(3, n // 30)
    for i in range(n - sostenido):
        if np.min(s[i:i + sostenido]) > umbral_drop:
            seg["DROP"] = _idx_a_seg(i); break

    if "INTRO" in seg and "DROP" in seg:
        idx_intro = int(seg["INTRO"] / duracion_seg * n)
        idx_drop = int(seg["DROP"] / duracion_seg * n)
        if idx_drop > idx_intro + 5:
            tramo = s[idx_intro:idx_drop]
            if len(tramo) >= 5:
                deltas = np.diff(tramo)
                inicio_busq = max(0, int(len(deltas) * 0.4))
                if inicio_busq < len(deltas):
                    idx_max_pend = inicio_busq + int(np.argmax(deltas[inicio_busq:]))
                    seg["BUILD"] = _idx_a_seg(idx_intro + idx_max_pend)

    if "DROP" in seg:
        idx_drop = int(seg["DROP"] / duracion_seg * n)
        umbral_break = maxv * 0.45
        sostenido_break = max(5, n // 10)
        inicio = idx_drop + max(2, n // 20)
        for i in range(inicio, n - sostenido_break):
            if np.max(s[i:i + sostenido_break]) < umbral_break:
                seg["BREAK"] = _idx_a_seg(i); break

    inicio_outro = int(n * 0.7)
    umbral_outro = media * 0.7
    for i in range(n - 1, inicio_outro, -1):
        if s[i] > umbral_outro:
            outro_idx = min(n - 1, i + max(2, n // 40))
            seg["OUTRO"] = _idx_a_seg(outro_idx); break
    if "OUTRO" not in seg:
        seg["OUTRO"] = _idx_a_seg(int(n * 0.85))
    return seg
