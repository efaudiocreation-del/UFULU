# UFULU RODEC EDITION v33.7
# ===========================
# Sistema de gestión de maleta musical con análisis forense
# y curaduría narrativa para DJs.

## Requisitos
Ver `requirements.txt`

## Instalación
```bash
pip install -r requirements.txt
```

## Ejecución
```bash
python main.py
```

## Estructura
- `main.py` — Punto de entrada (interfaz PyQt6)
- `audio_engine.py` — Motor forense (BPM, ADN, segmentación)
- `collection_manager.py` — SQLite (persistencia de tracks)
- `curaduria_engine.py` — Motor narrativo (plan de vuelo)
- `genre_definitions.py` — Estilos Amapiano y rangos BPM
- `genre_analyzer_svm.py` — Clasificador CLAP + SVM
- `tag_manager.py` — Lectura/escritura de tags ID3/FLAC
- `playlist_exporters.py` — Exportación M3U8/NML/XML/PDF
- `ufulu_style.py` — Temas visuales (piel Rodec BX-9)
- `widgets_ufulu.py` — SplashWelcome, SplashForense
- `widgets_rodec.py` — Knobs, faders, LCD (look hardware)
- `utils.py` — Función normalizar()
- `scripts/` — Scripts legacy (ML independientes)
