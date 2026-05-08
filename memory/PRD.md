# UFULU · RODEC EDITION — PRD

## Original problem statement
Aplicación de escritorio Python/PyQt6 para DJs llamada **Ufulu Rodec Edition**.
Lee audios, los analiza por DSP (BPM, RMS, estabilidad rítmica), persiste en
SQLite y genera playlists narrativas. Estética inspirada en mesa Rodec BX-9.

## Scope v33.7
- Análisis forense BPM (rejilla fiel al kick + confidence 0-100%)
- Energía 1-10, función (OPEN/HOLD/SHIFT/PEAK), key Camelot, luz DÍA/NOCHE
- Maleta SQLite con backup diario automático (14 días retención)
- Curaduría narrativa (warm-up / peak / closing) con Camelot
- Exportadores: M3U8, Traktor NML (CUE_V2 inyectados), Rekordbox XML, PDF
- Plantillas + Histórico con rating + Salud + Estadísticas
- Auto-segmentación (Intro/Build/Drop/Break/Outro), Drag&drop, Atajos
- Pre-escucha con QMediaPlayer al soltar el knob
- UI Rodec BX-9 (knobs, faders, LCD, panel grafito)

## Architecture
- `main.py` — Punto de entrada PyQt6, MainApp, MenuBar, Tabs
- `audio_engine.py` — DSP: BPM, RMS, beat, segmentación, key Camelot
- `tag_manager.py` — ID3/Vorbis (lectura y escritura HotCues)
- `collection_manager.py` — SQLite (tracks, config, templates, history)
- `curaduria_engine.py` — Algoritmo narrativo + sugerencias
- `playlist_exporters.py` — M3U8 / NML / XML / PDF
- `ufulu_style.py` — QSS Rodec
- `widgets_rodec.py` — Knobs hardware
- `widgets_ufulu.py` — SplashWelcome, SplashForense, RatingWidget

## DB schema
- `tracks(path PK, filename, bpm, funcion, color, estilo, wave_data, analyzed,
          energia, key_camelot, notas, bpm_confidence, fecha_analisis)`
- `config(clave PK, valor)`
- `templates(name PK, luz, momento, estilo, densidad, duracion)`
- `history(id PK, timestamp, params, rating, notas_sesion, playlist_json)`

## Implemented (May 2026 — sesión actual)
- 2026-02 / Sesión actual:
  - Re-creados los 6 archivos perdidos del repo: `collection_manager.py`,
    `curaduria_engine.py`, `ufulu_style.py`, `widgets_rodec.py`,
    `widgets_ufulu.py`, `playlist_exporters.py`
  - Añadida `QMenuBar` v33.7 cableando Auto-segmentar, Sugerir, Salud,
    Stats, Plantillas, Histórico y los 4 exportadores
  - Inicialización de `_cur_player` (QMediaPlayer) para pre-escucha
  - Llamada a `_instalar_extensiones_v337()` al final de `__init__`
  - Validación funcional: 11/11 tests OK (DB, curaduría, exportadores M3U8/NML/XML/PDF)

## Backlog
- P2: Cola batch nocturna (analizar varias carpetas en background)
- P2: Auto-tagging desde MusicBrainz/AcoustID
- P3: Modo Performance "always on top" (UI más compacta)
- P3: Onda RMS en tiempo real durante pre-escucha

## Notes
- Es una app de escritorio local. NO se sirve por web ni supervisor.
- Validación se hace con `python -m py_compile *.py` y scripts test.
- BD por defecto: `ufulu_almacen.db` junto a `main.py`.
- Backups diarios en `./ufulu_backups/`.
