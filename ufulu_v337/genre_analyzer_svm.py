# genre_analyzer_svm.py
# CLAP + SVM — Sustituye al XGBoost antiguo
# =====================================================
# Extrae 3 embeddings CLAP (inicio, centro, final) de
# 15s cada uno a 48kHz y los promedia antes de clasificar.
# =====================================================

import os
import sys
import json
import numpy as np
import torch
import laion_clap
import librosa
import joblib

# --- RUTAS A LOS ARTEFACTOS (ajustar cuando tengas los .pkl) ---
BASE = os.path.dirname(__file__)
SCALER_FILE = os.path.join(BASE, "scaler_clap.pkl")
SVM_FILE    = os.path.join(BASE, "svm_clap.pkl")
CLASSES_FILE = os.path.join(BASE, "clases_clap.pkl")
EMBEDDINGS_CACHE = os.path.join(BASE, "embeddings_v2.npz")

# --- VARIABLES GLOBALES (carga lazy) ---
clap_model = None
scaler = None
svm = None
clases = None
cache_embeddings = {}  # ruta -> embedding

# --- CONSTANTES ---
SR = 48000
DURACION = 15  # segundos por muestra


def _cargar_clap():
    global clap_model
    if clap_model is None:
        print("[CLAP] Cargando modelo HTSAT-tiny...")
        clap_model = laion_clap.CLAP_Module(enable_fusion=True, amodel='HTSAT-tiny')
        clap_model.load_ckpt()
        clap_model.eval()
        print("[CLAP] Listo.")


def _cargar_modelo_svm():
    global scaler, svm, clases, cache_embeddings
    if svm is not None:
        return
    _cargar_clap()
    if os.path.exists(SCALER_FILE) and os.path.exists(SVM_FILE):
        scaler = joblib.load(SCALER_FILE)
        svm = joblib.load(SVM_FILE)
        clases = joblib.load(CLASSES_FILE)
        print(f"[SVM] Modelo cargado: {len(clases)} clases")
    # Cargar caché de embeddings desde embeddings_v2.npz (1788 muestras)
    if os.path.exists(EMBEDDINGS_CACHE):
        try:
            data = np.load(EMBEDDINGS_CACHE, allow_pickle=True)
            rutas_c = data['rutas']
            embs = data['embeddings']
            cache_embeddings = dict(zip(rutas_c, embs))
            print(f"[CACHE] {len(cache_embeddings)} embeddings cacheados desde {EMBEDDINGS_CACHE}")
        except Exception as e:
            print(f"[CACHE] Error cargando {EMBEDDINGS_CACHE}: {e}")


def _extraer_ventana(y, sr, inicio_seg):
    """Extrae una ventana de DURACION segundos desde inicio_seg."""
    largo = int(sr * DURACION)
    inicio = int(inicio_seg * sr)
    if inicio + largo > len(y):
        # Si no cabe, tomar los últimos DURACION segundos disponibles
        inicio = max(0, len(y) - largo)
    ventana = y[inicio:inicio + largo]
    if len(ventana) < largo:
        ventana = np.pad(ventana, (0, largo - len(ventana)), mode='constant')
    return ventana


def _extraer_embedding(ruta):
    """
    Extrae embedding CLAP promediando 3 ventanas de 15s:
      - Inicio:     [0s - 15s]
      - Centro:     [centro - 7.5s : centro + 7.5s]
      - Final:      [final - 15s : final]
    """
    if ruta in cache_embeddings:
        return cache_embeddings[ruta]
    try:
        if not os.path.exists(ruta):
            return None
        y, _ = librosa.load(ruta, sr=SR, mono=True)
        duracion_total = len(y) / SR

        # Calcular puntos de inicio de las 3 ventanas
        inicio_1 = 0.0
        inicio_2 = max(0.0, duracion_total / 2 - DURACION / 2)
        inicio_3 = max(0.0, duracion_total - DURACION)

        ventanas = []
        for inicio_seg in [inicio_1, inicio_2, inicio_3]:
            v = _extraer_ventana(y, SR, inicio_seg)
            ventanas.append(v)

        # Obtener embedding para cada ventana
        embeddings = []
        with torch.no_grad():
            for v in ventanas:
                audio_tensor = torch.from_numpy(v).unsqueeze(0).float()
                emb = clap_model.get_audio_embedding_from_data(
                    x=audio_tensor, use_tensor=True
                )
                embeddings.append(emb.squeeze().cpu().numpy())

        # Promediar los 3 embeddings
        emb_promedio = np.mean(embeddings, axis=0)
        cache_embeddings[ruta] = emb_promedio
        return emb_promedio
    except Exception as e:
        print(f"[CLAP] Error con {os.path.basename(ruta)}: {e}")
        return None


def analizar_archivos_svm(rutas, progress_callback=None):
    """
    Analiza una lista de rutas de audio usando CLAP + SVM.
    Devuelve dict {ruta: genero_predicho}.
    main.py no necesita ningún cambio.
    """
    _cargar_modelo_svm()
    resultados = {}
    total = len(rutas)
    
    for i, ruta in enumerate(rutas, 1):
        emb = _extraer_embedding(ruta)
        if emb is None:
            resultados[ruta] = "Error al procesar"
        else:
            emb_scaled = scaler.transform(emb.reshape(1, -1))
            probas = svm.predict_proba(emb_scaled)[0]
            idx = np.argmax(probas)
            conf = probas[idx]
            if conf >= 0.6:
                resultados[ruta] = clases[idx]
            else:
                resultados[ruta] = "Desconocido"

        if progress_callback is not None:
            progress_callback(i, total)
    
    return resultados


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python genre_analyzer_svm.py <archivo_json_con_rutas>")
        sys.exit(1)
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        rutas = json.load(f)
    res = analizar_archivos_svm(rutas)
    print(json.dumps(res))