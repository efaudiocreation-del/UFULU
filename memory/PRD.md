# UFULU · RODEC EDITION — PRD

## Original problem statement
Aplicación de escritorio Python/PyQt6 para DJs llamada **Ufulu Rodec Edition**.
Lee audios, los analiza por DSP (BPM, RMS, estabilidad rítmica), persiste en
SQLite y genera playlists narrativas. Estética inspirada en mesa Rodec BX-9.

## Scope v33.7
- Análisis forense BPM (rejilla fiel al kick + confidence 0-100%)
- Energía 1-10, función (OPEN/HOLD/SHIFT/PEAK), key Camelot, luz DÍA/NOCHE
- Maleta SQLite con backup diario automático (14 días retención)
- Curaduría narrativa v28.0 (cascada 4 niveles + arco 6 actos)
- Exportadores: M3U8, Traktor NML (CUE_V2 inyectados), Rekordbox XML, PDF
- Plantillas + Histórico con rating + Salud + Estadísticas
- Auto-segmentación (Intro/Build/Drop/Break/Outro), Drag&drop, Atajos
- Pre-escucha con QMediaPlayer al soltar el knob
- UI Rodec BX-9 (knobs antracita, faders, LCD, panel azul antracita)

## Architecture (checkpoint 2026-02 — sesión actual)
- `main.py` — Entrada PyQt6, MainApp, MenuBar v33.7, 3 tabs, knobs Rodec
- `audio_engine.py` — DSP DJ propio (NO TOCAR — lógica del usuario)
- `tag_manager.py` — ID3 + FLAC, lectura/escritura HotCues UFULU
- `collection_manager.py` — SQLite (tracks, config, templates, history) + backup
- `curaduria_engine.py` — Camelot Pro + arco 6 actos + cascada 4 niveles (v28.0)
- `playlist_exporters.py` — M3U8 / NML / XML / PDF
- `ufulu_style.py` — QSS antracita BX-9
- `widgets_rodec.py` — RodecKnob + RodecKnobSelector + RodecLCD + RodecVUMeter
- `widgets_ufulu.py` — SplashWelcome + SplashForense + RatingWidget

## DB schema
- `tracks(path PK, filename, bpm, funcion, color, estilo, wave_data, analyzed,
          energia, key_camelot, notas, bpm_confidence, fecha_analisis)`
- `config(clave PK, valor)`
- `templates(name PK, luz, momento, estilo, densidad, duracion)`
- `history(id PK, timestamp, params, rating, notas_sesion, playlist_json)`

## Implemented (sesión actual — feb 2026)
- 2026-02:
  - Re-creados los 6 archivos perdidos del repo
  - QMenuBar v33.7 cableando todas las acciones avanzadas
  - Bug título "-" corregido en tag_manager (orden de retorno + soporte FLAC)
  - Estética Rodec BX-9 real: panel antracita #485059, anillo plata cepillada,
    aguja triangular roja, tablas LCD verde fósforo, mini-LCD bajo cada knob
  - Sustitución de los 4 QComboBox de Curaduría por knobs Rodec (drop-in API)
  - **curaduria_engine.py restaurado literalmente a la v28.0 del usuario**
    (cascada 4 niveles + arco 6 actos + Camelot Pro)

## CHECKPOINT — punto de control 2026-02
Estado: **APP COMPILABLE Y FUNCIONAL**.
Confirmado por usuario: arranca, analiza, muestra nombres, genera playlists.
Lógicas críticas (audio_engine, curaduria_engine) intactas y verificadas.

## Backlog
### P1 — Mejoras altas
- Pre-escucha de tema en la tabla de Curaduría (doble clic → reproducir 30s
  desde el primer hotcue, con barra de transporte mini)
- Reordenar playlist de Curaduría con drag&drop entre filas
- Botón "REEMPLAZAR" por candidato compatible en cada fila

### P2 — Mejoras medias
- Cola batch nocturna (analizar varias carpetas en background)
- Auto-tagging desde MusicBrainz/AcoustID
- Detección de duplicados en la maleta (mismo BPM+key+duración)
- Histograma visual de Camelot keys en Stats
- Replay Gain / LUFS para coherencia de volumen entre tracks

### P3 — Pulido
- Modo Performance "always on top" más compacto
- Onda RMS en tiempo real durante pre-escucha
- Modo "Cabina oscura" con tipografía XL
- Comparador A/B de dos tracks lado a lado

## Notes
- App de escritorio local. NO se sirve por web ni supervisor.
- Validación con `python -m py_compile *.py` y scripts test.
- BD por defecto: `ufulu_almacen.db` junto a `main.py`.
- Backups diarios en `./ufulu_backups/`.
- **NO TOCAR sin pedir permiso**: `audio_engine.py` y `curaduria_engine.py`
  contienen la lógica musical del DJ.
