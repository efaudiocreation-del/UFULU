# curaduria_engine.py
# MOTOR NARRATIVO UFULU: v28.0 - EDICIÓN MAESTRA "PLAN DE VUELO"
# PROTOCOLO DE RIGOR: PROHIBIDO RESUMIR - INTELIGENCIA MUSICAL PARA CABINA

import os
import random
from datetime import timedelta
from utils import normalizar


# --- [MÓDULO 1: ALGORITMO ARMÓNICO CAMELOT PRO] ---
def calcular_compatibilidad_armonica(key1, key2, nivel_tolerancia=0):
    """
    Rueda Camelot Inteligente.
    Nivel 0: Match Perfecto (11A -> 11A) o Relativa de Modo (11A -> 11B).
    Nivel 1: Salto de Energía Lateral (11A -> 12A / 10A) o Cambio de Modo con Energía (11A -> 10B / 12B).
    Nivel 2: Salto de +2 (Boost de mezcla dinámica).
    """
    if key1 == "-" or key2 == "-":
        return True
    if key1 == key2:
        return True

    try:
        n1, escala1 = int(key1[:-1]), key1[-1].upper()
        n2, escala2 = int(key2[:-1]), key2[-1].upper()

        # 1. Cambio de Modo (misma energía): 11A -> 11B
        if n1 == n2 and escala1 != escala2:
            return True

        # 2. Saltos Laterales (mismo modo): +/- 1
        if escala1 == escala2:
            if abs(n1 - n2) == 1:
                return True
            if (n1 == 12 and n2 == 1) or (n1 == 1 and n2 == 12):
                return True

        # 3. Saltos de Modo Cruzado (cambio de modo + energía): 11A -> 10B / 12B
        if escala1 != escala2:
            if abs(n1 - n2) == 1:
                return True
            if (n1 == 12 and n2 == 1) or (n1 == 1 and n2 == 12):
                return True

        # 4. Tolerancia Dinámica (+2 mismo modo)
        if nivel_tolerancia >= 1:
            if escala1 == escala2 and abs(n1 - n2) == 2:
                return True

    except Exception:
        pass

    return False


# --- [MÓDULO 2: ARCO NARRATIVO DE 6 ACTOS] ---
def obtener_estructura_literaria(momento):
    """
    Define la progresión de la sesión según el arco dramático clásico.
    1. OPEN | 2. HOLD | 3. SHIFT | 4. PEAK | 5. DROP | 6. OUTRO
    """
    if "WARM-UP" in momento.upper():
        # Curva ascendente lenta: empieza suave, construye tensión
        return ["1. OPEN", "1. OPEN", "2. HOLD", "3. SHIFT", "1. OPEN", "2. HOLD"]

    elif "PEAK" in momento.upper():
        # Energía máxima constante con giros
        return ["2. HOLD", "3. SHIFT", "4. PEAK", "4. PEAK", "3. SHIFT", "4. PEAK"]

    elif "CLOSING" in momento.upper():
        # Descenso emocional controlado: de la cumbre a la calma
        return ["4. PEAK", "4. PEAK", "3. SHIFT", "2. HOLD", "1. OPEN", "1. OPEN"]

    # Fallback equilibrado para cualquier otro caso
    return ["1. OPEN", "2. HOLD", "3. SHIFT", "4. PEAK", "3. SHIFT", "1. OPEN"]


# --- [MÓDULO 3: MOTOR DE SELECCIÓN EN CASCADA] ---
def generar_sesion_ufulu(pool_total, config):
    """
    Construye la playlist definitiva cruzando metadatos físicos y forenses.
    pool_total: [(filename, bpm, func, luz, estilo, path, energia, key, conf), ...]
    """
    if not pool_total:
        return []

    # Diagnóstico armónico (opcional, puedes eliminarlo si no quieres verlo)
    claves_validas = sum(1 for t in pool_total if t[7] and t[7] != "-")
    print(f"[CURADURÍA] Stock total: {len(pool_total)} pistas, "
          f"con clave armónica: {claves_validas} "
          f"({100 * claves_validas // max(1, len(pool_total))}%)")

    # 1. PARAMETRIZACIÓN DEL TIEMPO
    densidad = config.get('densidad', 'NORMAL')
    t_per_track = 4 if "RÁPIDA" in densidad else (10 if "LARGA" in densidad else 6)
    duracion_min = int(config.get('duracion', 60))
    n_objetivo = duracion_min // t_per_track

    # 2. FILTRADO INICIAL POR ESTILO (SIN LUZ, ya que no es relevante)
    estilo_req = config.get('estilo', 'TODOS').upper()
    estilos_permitidos = config.get('estilos_lista', [estilo_req])
    pool_estilo = [t for t in pool_total
               if "TODOS" in estilos_permitidos or any(normalizar(e) == normalizar(str(t[4])) for e in estilos_permitidos)]

    # 3. PREPARACIÓN DEL ARCO
    arco = obtener_estructura_literaria(config.get('momento', 'WARM-UP'))
    playlist_final = []
    tiempo_acumulado = 0

    def _key_de(track):
        try:
            return track[7] if len(track) > 7 and track[7] else "-"
        except Exception:
            return "-"

    # 4. BUCLE DE NARRATIVA MUSICAL
    for i in range(n_objetivo):
        fase_actual = arco[int((i / n_objetivo) * len(arco))]

        key_anterior = "-"
        if playlist_final:
            key_anterior = _key_de(playlist_final[-1]['data'])

        candidato_elegido = None
        motivo_eleccion = ""

        # Extraer palabra clave de la fase (ej. "1. OPEN" -> "OPEN")
        keyword = fase_actual.split('.')[-1].strip().upper()

        # Candidatos base: fase flexible, sin distinción de luz, no repetidos
        cands_base = [t for t in pool_estilo
                      if keyword in str(t[2]).upper()
                      and t not in [p['data'] for p in playlist_final]]

        # NIVEL 1: Match Armónico Perfecto (misma fase)
        match_1 = [c for c in cands_base
                   if calcular_compatibilidad_armonica(key_anterior, _key_de(c), 0)]
        if match_1:
            candidato_elegido = random.choice(match_1)
            motivo_eleccion = f"Match Armónico Perfecto ({fase_actual})"
        else:
            # NIVEL 2: Transición de Energía (fase flexible)
            match_2 = [c for c in cands_base
                       if calcular_compatibilidad_armonica(key_anterior, _key_de(c), 1)]
            if match_2:
                candidato_elegido = random.choice(match_2)
                motivo_eleccion = f"Transición de Energía ({fase_actual})"
            else:
                # NIVEL 3: Ajuste de Fase (ignorando compatibilidad armónica)
                match_3 = [t for t in pool_estilo
                           if keyword in str(t[2]).upper()
                           and t not in [p['data'] for p in playlist_final]]
                if match_3:
                    candidato_elegido = random.choice(match_3)
                    motivo_eleccion = f"Ajuste de Fase ({fase_actual})"
                else:
                    # NIVEL 4: Emergencia (cualquier tema no repetido del estilo)
                    match_4 = [t for t in pool_estilo
                              if t not in [p['data'] for p in playlist_final]]
                    if not match_4:
                        break
                    candidato_elegido = random.choice(match_4)
                    motivo_eleccion = "Selección de Emergencia (Sin stock en fase)"

        # Inyección de Semilla (primer track)
        if i == 0 and config.get('usar_semilla') and config.get('semilla'):
            sem_path = config.get('semilla')
            for t in pool_total:
                if t[5] == sem_path:
                    candidato_elegido = t
                    motivo_eleccion = "Semilla Literaria (Origen)"
                    break

        if candidato_elegido:
            playlist_final.append({
                'tiempo': str(timedelta(minutes=tiempo_acumulado))[:-3],
                'acto': fase_actual,
                'data': candidato_elegido,
                'motivo': motivo_eleccion
            })
            tiempo_acumulado += t_per_track

    return playlist_final


# --- [MÓDULO 4: REDACTOR DEL PLAN DE VUELO] ---
def generar_texto_guia(playlist, config):
    """Genera la Guía Técnica de Cabina en formato industrial"""
    if not playlist:
        return "ERROR: NO SE PUDO GENERAR NARRATIVA."

    txt = "========================================================\n"
    txt += "        UFULU DJ SYSTEM - PLAN DE VUELO ANALÓGICO       \n"
    txt += f"        MALETA: {config.get('maleta', 'GLOBAL').upper()} \n"
    txt += "========================================================\n\n"

    txt += f"PARÁMETROS: {config.get('luz')} | {config.get('momento')} | {config.get('duracion')} MIN\n"
    txt += "-" * 56 + "\n\n"

    for i, item in enumerate(playlist):
        d = item['data']
        txt += f"[{item['tiempo']}] PASO {i+1:02d} | {item['acto']}\n"
        txt += f"   TEMA: {d[0]}\n"
        txt += f"   TÉCNICA: {d[1]} BPM | {d[4]} | {item['motivo']}\n"
        txt += "." * 40 + "\n"

    txt += "\nFIN DE HOJA DE RUTA - UFULU NARRATIVE ENGINE v28.0"
    return txt


# --- [MÓDULO 5: SUGERIDOR DE SIGUIENTE TEMA] ---
def sugerir_siguiente_track(track_actual, pool, n=8):
    """
    Devuelve hasta N candidatos ordenados por compatibilidad Camelot + cercanía BPM.
    nivel: 1 (perfect) · 2 (bueno) · 3 (rescate)
    """
    if not track_actual or not pool:
        return []

    fn_a, bpm_a, func_a, color_a, est_a, path_a, ener_a, key_a, conf_a = track_actual
    try:
        bpm_base = int(float(bpm_a))
    except Exception:
        bpm_base = 120

    sugs = []
    for r in pool:
        if r[5] == path_a:
            continue
        try:
            b = int(float(r[1]))
        except Exception:
            continue
        if b <= 0:
            continue
        d_bpm = abs(b - bpm_base)
        if d_bpm > 12:
            continue

        key_r = r[7] if len(r) > 7 else "-"

        if calcular_compatibilidad_armonica(key_a, key_r, 0) and d_bpm <= 3:
            nivel = 1
            motivo = f"Match Armónico Perfecto · Δ={d_bpm}"
        elif calcular_compatibilidad_armonica(key_a, key_r, 1) and d_bpm <= 6:
            nivel = 2
            motivo = f"Transición de Energía · Δ={d_bpm}"
        elif d_bpm <= 12:
            nivel = 3
            motivo = f"Rescate · Δ={d_bpm}"
        else:
            continue

        sugs.append({
            'nivel': nivel,
            'track': r,
            'delta_bpm': float(d_bpm),
            'motivo': motivo,
        })

    sugs.sort(key=lambda s: (s['nivel'], s['delta_bpm']))
    return sugs[:n]