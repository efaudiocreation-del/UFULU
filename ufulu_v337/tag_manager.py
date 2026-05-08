from mutagen.id3 import ID3, TBPM, TPE4, TKEY, TCON, COMM, TIT2, TPE1
from mutagen.flac import FLAC
import os


def _str_id3(audio, frame_id, default=""):
    """Lee un frame ID3 con blindaje contra valores corruptos."""
    try:
        v = audio.get(frame_id)
        if v is None:
            return default
        # Algunos frames son listas, otros vienen ya como string
        try:
            txt = v.text[0] if hasattr(v, "text") and v.text else str(v)
        except Exception:
            txt = str(v)
        txt = (txt or "").strip()
        return txt if txt else default
    except Exception:
        return default


def leer_tags_completos(ruta):
    """
    Lectura quirúrgica de metadatos (v33.7) - Blindaje contra Tags corruptos.
    Devuelve la tupla esperada por audio_engine.py:
        (bpm, titulo, artista, cues_data, genero)
    Soporta ID3 (.mp3) y Vorbis Comments (.flac).
    """
    cues_vacia = {i: None for i in range(1, 9)}
    bpm = "0"
    titulo = ""
    artista = ""
    genero = ""
    cues_data = cues_vacia.copy()

    if not ruta:
        return bpm, titulo, artista, cues_vacia, genero

    ext = ruta.lower().rsplit(".", 1)[-1] if "." in ruta else ""

    try:
        # =========================================================
        # MP3 (ID3v2)
        # =========================================================
        if ext == "mp3":
            try:
                audio = ID3(ruta)
            except Exception:
                # Algunos MP3 vienen sin etiqueta ID3 todavía
                titulo = os.path.splitext(os.path.basename(ruta))[0]
                return bpm, titulo, artista, cues_vacia, genero

            bpm     = _str_id3(audio, "TBPM",  "0")
            titulo  = _str_id3(audio, "TIT2",  "")
            artista = _str_id3(audio, "TPE1",  "")
            genero  = _str_id3(audio, "TCON",  "")

            # CUES (UFULU_DATA en COMM) - blindado
            try:
                comentarios = audio.getall("COMM")
            except Exception:
                comentarios = []
            for comment in comentarios:
                try:
                    desc = getattr(comment, "desc", "") or ""
                    text = getattr(comment, "text", [""]) or [""]
                    val_text = text[0] if isinstance(text, list) else str(text)
                    if "UFULU_DATA" in desc or "UFULU_CUES" in val_text:
                        partes = val_text.split("|")[1:]
                        for p in partes:
                            if ":" in p:
                                idx, val = p.split(":")
                                cues_data[int(idx)] = float(val)
                except Exception:
                    continue

        # =========================================================
        # FLAC (Vorbis Comments)
        # =========================================================
        elif ext == "flac":
            try:
                audio = FLAC(ruta)
            except Exception:
                titulo = os.path.splitext(os.path.basename(ruta))[0]
                return bpm, titulo, artista, cues_vacia, genero

            def _vorbis(key):
                try:
                    v = audio.get(key) or audio.get(key.upper())
                    if v and isinstance(v, list) and v[0]:
                        return str(v[0]).strip()
                except Exception:
                    pass
                return ""

            bpm     = _vorbis("bpm")     or "0"
            titulo  = _vorbis("title")
            artista = _vorbis("artist")
            genero  = _vorbis("genre")

            # CUES desde comentario Ufulu (almacenamos en 'comment')
            for clave_ufulu in ("ufulu_cues", "comment", "description"):
                raw = _vorbis(clave_ufulu)
                if raw and "UFULU_CUES" in raw:
                    try:
                        partes = raw.split("|")[1:]
                        for p in partes:
                            if ":" in p:
                                idx, val = p.split(":")
                                cues_data[int(idx)] = float(val)
                    except Exception:
                        pass
                    break

        # Fallback: nombre desde el archivo si no había TIT2/title
        if not titulo:
            titulo = os.path.splitext(os.path.basename(ruta))[0]

        return bpm, titulo, artista, cues_data, genero

    except Exception as e:
        print(f"Aviso técnico en {os.path.basename(ruta)}: {e}")
        # Devolvemos al menos un nombre legible
        if not titulo:
            titulo = os.path.splitext(os.path.basename(ruta))[0]
        return bpm, titulo, artista, cues_vacia, genero


def escribir_tags_ufulu(ruta, bpm, funcion, cues=None):
    """Sella el ADN en el archivo físico compatible con Traktor Pro.
    Soporta MP3 (ID3v2) y FLAC (Vorbis)."""
    try:
        ext = ruta.lower().rsplit(".", 1)[-1] if "." in ruta else ""

        # ---------- MP3 ----------
        if ext == "mp3":
            try:
                audio = ID3(ruta)
            except Exception:
                # Crea ID3 vacío si no existe
                audio = ID3()
            # TBPM = BPM | TPE4 = Remixer (Función Ufulu)
            audio.add(TBPM(encoding=3, text=str(bpm)))
            audio.add(TPE4(encoding=3, text=str(funcion)))

            if cues:
                # Borramos comentarios UFULU previos (evita hinchado)
                try:
                    nuevos = []
                    for c in audio.getall("COMM"):
                        if getattr(c, "desc", "") != "UFULU_DATA":
                            nuevos.append(c)
                    audio.delall("COMM")
                    for c in nuevos:
                        audio.add(c)
                except Exception:
                    pass

                cue_list = [f"{k}:{v:.3f}" for k, v in cues.items() if v is not None]
                if cue_list:
                    serializado = "UFULU_CUES|" + "|".join(cue_list)
                    audio.add(COMM(encoding=3, lang="eng",
                                   desc="UFULU_DATA", text=serializado))

            audio.save(ruta, v2_version=3)
            return True

        # ---------- FLAC ----------
        if ext == "flac":
            audio = FLAC(ruta)
            audio["bpm"] = str(bpm)
            audio["remixer"] = str(funcion)  # campo Vorbis equivalente
            if cues:
                cue_list = [f"{k}:{v:.3f}" for k, v in cues.items() if v is not None]
                if cue_list:
                    audio["ufulu_cues"] = "UFULU_CUES|" + "|".join(cue_list)
            audio.save()
            return True

    except Exception as e:
        print(f"Error escritura física en {os.path.basename(ruta)}: {e}")
        return False
    return False


def inyectar_bloque_ufulu(lista_tareas):
    """Procesador de Inyección Masiva Secuencial (sincronizado con MainApp.save_selected)."""
    exitos, fallos = 0, 0
    for tarea in lista_tareas:
        res = escribir_tags_ufulu(
            tarea["path"],
            tarea["bpm"],
            tarea["func"],
            tarea.get("cues"),
        )
        if res:
            exitos += 1
        else:
            fallos += 1
    return exitos, fallos
