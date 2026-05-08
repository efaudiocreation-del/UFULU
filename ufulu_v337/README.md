# UFULU RODEC EDITION v33.7

Aplicación de escritorio Python/PyQt6 para análisis forense de audio y curaduría narrativa de sesiones DJ. Estética hardware del Rodec BX-9.

## Características

- **Motor BPM v33.7** con rejilla fiel al kick + confidence score (resuelve drift en Amapiano/Tribal/Psy Trance)
- **Análisis triple sondeo** con función, energía 1-10, luz Día/Noche, estilo y Camelot Key
- **Mi Maleta** SQLite con notas DJ, filtros avanzados, salud auditada y backups diarios automáticos
- **Curaduría narrativa** con cascada UFULU (BPM ±4/±6/±8, Camelot, arco) + plantillas y histórico+rating
- **Auto-segmentación estructural** (INTRO/BUILD/DROP/BREAK/OUTRO como CUEs)
- **Modo AB** y **Modo Performance** always-on-top
- **Exportación a Traktor NML / Rekordbox XML / M3U8 / PDF profesional** (con HotCues nativos)
- UI hardware-style: knobs Rodec custom, selectores rotativos, LCD frames, scrollbars como faders

## Instalación

```bash
git clone https://github.com/TUUSUARIO/ufulu-rodec.git
cd ufulu-rodec
pip install -r requirements.txt
python main.py
```

## Compilación a `.exe` (Windows)

Doble clic sobre `compilar_ufulu.bat` o:

```cmd
pyinstaller --onefile --windowed --name "UfuluRodec" ^
  --hidden-import "scipy.signal" --hidden-import "librosa" ^
  --hidden-import "PyQt6.QtMultimedia" --collect-data "librosa" main.py
```

Resultado: `dist\UfuluRodec.exe` (~150-300 MB con todas las dependencias).

## Estructura del proyecto

| Archivo | Descripción |
|---|---|
| `main.py` | UI PyQt6 — 3 tabs (El Taller, Mi Maleta, Curaduría) |
| `audio_engine.py` | Motor DSP (Librosa+Scipy) con segmentación estructural |
| `collection_manager.py` | SQLite — tracks, plantillas, histórico, stats, backups |
| `curaduria_engine.py` | Cascada narrativa con Camelot + BPM strict |
| `tag_manager.py` | Lectura/escritura de tags MP3+FLAC con HotCues persistidos |
| `playlist_exporters.py` | M3U8 / NML+CUE_V2 / XML+POSITION_MARK / PDF |
| `widgets_rodec.py` | RodecKnob, RodecKnobSelector, RodecFader |
| `widgets_ufulu.py` | Splash screens y componentes visuales |
| `ufulu_style.py` | Hoja QSS con paleta Rodec BX-9 |
| `compilar_ufulu.bat` | Script Windows para generar el `.exe` |

## Uso típico (workflow)

1. **El Taller** → arrastra carpeta de música → motor analiza BPM/función/energía/key
2. **AUTO-SEGMENTAR** → cues automáticos en INTRO/BUILD/DROP/BREAK/OUTRO
3. **FIJAR ADN ACTUAL** → graba metadatos en el archivo físico
4. **Mi Maleta** → filtros avanzados, notas DJ, ESTADÍSTICAS, SALUD
5. **Curaduría** → 4 knobs (Luz/Arco/Estilo/Densidad) → GENERAR PLAN DE VUELO
6. **Reproductor integrado** con mini-waveform turquesa para pre-escucha
7. **EXPORTAR .NML / .XML / .PDF** → carga directa en Traktor/Rekordbox con hotcues nativos

## Atajos de teclado

| Tecla | Acción |
|---|---|
| `P` / `Space` | Play/Pause reproductor Curaduría |
| `S` | Stop |
| `←` / `→` | Tema anterior/siguiente del Plan |
| `Ctrl+G` | Generar Plan de Vuelo |
| `Ctrl+1/2/3` | Cambiar pestaña |

## Licencia

Uso personal. Sin afiliación con Native Instruments, Pioneer DJ ni Rodec NV.
