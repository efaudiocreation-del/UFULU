# curaduria_engine.py
# UFULU RODEC EDITION - MOTOR NARRATIVO DE PLAYLISTS v33.7
# =====================================================
# Genera "planes de vuelo" musicales en cascada, respetando
# arco emocional (warm-up / peak / closing), iluminación,
# densidad y compatibilidad armónica Camelot.
# =====================================================

import os
import random
from datetime import timedelta


# Mapa Camelot: vecinos compatibles (mismo número, ±1, mismo número en otro modo)
def _camelot_vecinos(key: str):
    """Devuelve set de claves Camelot compatibles para mezcla armónica."""
    if not key or key == "-" or len(key) < 2:
        return set()
    try:
        num = int(key[:-1])
        modo = key[-1].upper()
        if modo not in ("A", "B"):
            return set()
        vecinos = set()
        # Mismo número, otro modo (relativa mayor/menor)
        otro = "B" if modo == "A" else "A"
        vecinos.add(f"{num}{otro}")
        # ±1 en mismo modo (cuarta/quinta perfecta)
        for d in (-1, +1):
            n = ((num - 1 + d) % 12) + 1
            vecinos.add(f"{n}{modo}")
        # Mismo
        vecinos.add(f"{num}{modo}")
        return vecinos
    except Exception:
        return set()


# Curva de BPM por momento del set (función del 0..1 dentro del arco)
def _curva_bpm(momento: str, t01: float) -> float:
    """Devuelve un offset multiplicador (factor sobre BPM base)."""
    momento = (momento or "").upper()
    if "WARM" in momento:
        return 0.92 + 0.08 * t01            # +0..+8%
    if "PEAK" in momento or "CÉNIT" in momento:
        return 1.00 + 0.04 * (1 - abs(2 * t01 - 1))  # campana +0..+4%
    if "CLOS" in momento:
        return 1.00 - 0.10 * t01            # decay -0..-10%
    return 1.0


def _densidad_a_minutos(densidad: str) -> float:
    """Minutos medios por tema para calcular cuántos meter."""
    d = (densidad or "").upper()
    if "RÁPID" in d or "RAPID" in d: return 4.0
    if "LARG" in d:                  return 8.0
    return 6.0  # NORMAL


def _bpm_a_int(v) -> int:
    try:
        return int(round(float(v)))
    except Exception:
        return 0


# =====================================================
# ALGORITMO PRINCIPAL: GENERAR SESIÓN
# =====================================================
def generar_sesion_ufulu(pool, config: dict):
    """
    pool: lista de filas
        (filename, bpm, funcion, color, estilo, path, energia, key, conf)
    config: dict con luz/momento/duracion/densidad/estilo/usar_semilla/semilla

    Devuelve: lista de items {tiempo, acto, motivo, data}
    """
    if not pool:
        return []

    luz       = (config.get("luz") or "").upper()
    momento   = (config.get("momento") or "").upper()
    densidad  = config.get("densidad") or "NORMAL"
    estilo_b  = (config.get("estilo") or "TODOS").upper()
    usar_sem  = bool(config.get("usar_semilla"))
    semilla   = config.get("semilla") or ""

    try:
        duracion_min = max(15, int(float(config.get("duracion", 90))))
    except Exception:
        duracion_min = 90

    min_por_tema = _densidad_a_minutos(densidad)
    n_objetivo = max(4, int(round(duracion_min / min_por_tema)))

    # 1) FILTRO BASE
    candidatos = []
    for r in pool:
        fn, bpm, func, color, estilo, path, ener, key, conf = r
        if estilo_b != "TODOS" and estilo_b not in (estilo or "").upper():
            continue
        if luz and luz not in (color or "").upper():
            # Permisivo: en warm-up de sesión NOCHE aún admitimos algo de DÍA
            if not (luz == "NOCHE" and "DÍA" in (color or "").upper()):
                continue
        if _bpm_a_int(bpm) <= 0:
            continue
        candidatos.append(r)

    if len(candidatos) < 4:
        # Reintenta sin filtro de estilo
        candidatos = [r for r in pool if _bpm_a_int(r[1]) > 0]
    if not candidatos:
        return []

    # 2) BPM BASE
    bpm_base = 122.0
    if usar_sem and semilla:
        for r in pool:
            if r[5] == semilla:
                bpm_base = max(80.0, float(_bpm_a_int(r[1]) or 122))
                break

    # 3) CONSTRUCCIÓN EN CASCADA
    seleccion = []
    usados = set()

    # Si tenemos semilla, la metemos primero
    if usar_sem and semilla:
        for r in pool:
            if r[5] == semilla:
                seleccion.append({
                    "track": r,
                    "motivo": "Semilla del DJ"
                })
                usados.add(r[5])
                break

    while len(seleccion) < n_objetivo:
        t01 = (len(seleccion)) / max(1, n_objetivo - 1)
        bpm_obj = bpm_base * _curva_bpm(momento, t01)

        prev = seleccion[-1]["track"] if seleccion else None
        prev_key = prev[7] if prev else None
        vecinos = _camelot_vecinos(prev_key) if prev_key else set()

        mejor = None
        mejor_score = -1e9
        mejor_motivo = "Continuidad"

        for r in candidatos:
            if r[5] in usados:
                continue
            fn, bpm, func, color, estilo, path, ener, key, conf = r
            b = _bpm_a_int(bpm)
            if b <= 0:
                continue

            # Score: cercanía al BPM objetivo (penaliza salto >6)
            d_bpm = abs(b - bpm_obj)
            score = -d_bpm * 1.2

            # Compatibilidad armónica
            if vecinos and key in vecinos:
                score += 8.0
                motivo = f"Compat. armónica ({prev_key}→{key})"
            else:
                motivo = f"BPM Δ{d_bpm:.0f}"

            # Energía coherente con momento
            try:
                e = int(ener)
                if "PEAK" in momento and e >= 7: score += 3
                if "WARM" in momento and e <= 5: score += 3
                if "CLOS" in momento and 4 <= e <= 7: score += 2
            except Exception:
                pass

            # Confidence
            try:
                score += int(conf) * 0.02
            except Exception:
                pass

            # Pequeño ruido para no encasillar siempre lo mismo
            score += random.uniform(0, 0.6)

            if score > mejor_score:
                mejor_score = score
                mejor = r
                mejor_motivo = motivo

        if not mejor:
            break
        seleccion.append({"track": mejor, "motivo": mejor_motivo})
        usados.add(mejor[5])

    # 4) MAPEO A SALIDA con tiempos y actos
    salida = []
    minutos_acum = 0.0
    for i, item in enumerate(seleccion):
        t01 = i / max(1, len(seleccion) - 1)
        if t01 < 0.25:   acto = "1·APERTURA"
        elif t01 < 0.55: acto = "2·DESARROLLO"
        elif t01 < 0.80: acto = "3·CÉNIT"
        else:            acto = "4·CIERRE"
        td = timedelta(minutes=int(minutos_acum))
        salida.append({
            "tiempo": str(td)[:-3] if str(td).count(":") == 2 else str(td),
            "acto":   acto,
            "motivo": item["motivo"],
            "data":   item["track"],
        })
        minutos_acum += min_por_tema
    return salida


# =====================================================
# SUGERIR SIGUIENTE TEMA (botón "El Taller")
# =====================================================
def sugerir_siguiente_track(track_actual, pool, n: int = 8):
    """
    Devuelve hasta N candidatos ordenados por compatibilidad.
    Cada item: {nivel, track, delta_bpm, motivo}
    nivel: 1 (perfect), 2 (bueno), 3 (rescate)
    """
    if not track_actual or not pool:
        return []

    fn_a, bpm_a, func_a, color_a, est_a, path_a, ener_a, key_a, conf_a = track_actual
    bpm_base = _bpm_a_int(bpm_a)
    vecinos = _camelot_vecinos(key_a)

    sugs = []
    for r in pool:
        if r[5] == path_a:
            continue
        fn, bpm, func, color, estilo, path, ener, key, conf = r
        b = _bpm_a_int(bpm)
        if b <= 0:
            continue
        d = abs(b - bpm_base)
        if d > 12:
            continue

        if d <= 3 and key in vecinos:
            nivel = 1
            motivo = f"Perfect: Δ={d} y Camelot OK"
        elif d <= 6 and (key in vecinos or not vecinos):
            nivel = 2
            motivo = f"Bueno: Δ={d}" + (" + Camelot" if key in vecinos else "")
        elif d <= 12:
            nivel = 3
            motivo = f"Rescate: Δ={d}"
        else:
            continue

        sugs.append({
            "nivel":     nivel,
            "track":     r,
            "delta_bpm": float(d),
            "motivo":    motivo,
        })

    sugs.sort(key=lambda s: (s["nivel"], s["delta_bpm"]))
    return sugs[:n]


# =====================================================
# GENERAR TEXTO (HOJA DE RUTA / GUÍA DE CABINA)
# =====================================================
def generar_texto_guia(playlist, config: dict) -> str:
    if not playlist:
        return "PLAN DE VUELO VACÍO\n"
    cab = "=" * 64
    out = []
    out.append(cab)
    out.append("UFULU · RODEC EDITION  ·  HOJA DE RUTA DE CABINA")
    out.append(cab)
    out.append(f"MALETA   : {config.get('maleta','GLOBAL')}")
    out.append(f"DURACIÓN : {config.get('duracion','-')} min")
    out.append("")
    out.append(f"{'INICIO':<8} {'ACTO':<14} {'BPM':<5} {'KEY':<4} TRACK")
    out.append("-" * 64)
    for item in playlist:
        d = item.get("data") or [""] * 8
        fn = os.path.basename(str(d[0])) if d and d[0] else "?"
        bpm = str(d[1]) if len(d) > 1 else "?"
        key = str(d[7]) if len(d) > 7 else "-"
        out.append(
            f"{item.get('tiempo','-'):<8} {item.get('acto','-'):<14} "
            f"{bpm:<5} {key:<4} {fn[:42]}"
        )
        out.append(f"         └─ {item.get('motivo','')}")
    out.append("")
    out.append(cab)
    return "\n".join(out)
