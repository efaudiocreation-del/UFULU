from mutagen.id3 import ID3, TBPM, TPE4, TKEY, TCON, COMM
import os

def leer_tags_completos(ruta):
    """Lectura quirúrgica de metadatos (v33.3) - Blindaje contra Tags corruptos"""
    cues_vacia = {i: None for i in range(1, 9)}
    bpm, key, func, gen = "0", "-", "-", "*"
    try:
        if ruta.lower().endswith(('.mp3', '.flac')):
            audio = ID3(ruta)
            
            # Blindaje individual para cada campo crítico
            bpm = str(audio.get('TBPM', '0'))
            func = str(audio.get('TPE4', '-'))
            key = str(audio.get('TKEY', '-'))
            
            # Género con fallback de asterisco por si el campo TCON falla
            try:
                gen = str(audio.get('TCON', '*'))
            except:
                gen = "*"

            cues_data = cues_vacia.copy()
            
            # BLOQUE DE SEGURIDAD PARA COMENTARIOS (CUES)
            # Evita el error 'No comment text' de mpg123
            comentarios = audio.getall('COMM')
            for comment in comentarios:
                try:
                    # Usamos getattr para evitar errores si desc o text no existen
                    desc = getattr(comment, 'desc', "")
                    text = getattr(comment, 'text', [""])
                    # Aseguramos que text sea un string para el split
                    val_text = text[0] if isinstance(text, list) else str(text)
                    
                    if 'UFULU_DATA' in desc or 'UFULU_CUES' in val_text:
                        parts = val_text.split('|')[1:]
                        for p in parts:
                            if ':' in p:
                                idx, val = p.split(':')
                                cues_data[int(idx)] = float(val)
                except:
                    continue # Si un comentario está corrupto, saltamos al siguiente
                    
            return bpm, key, func, cues_data, gen
    except Exception as e:
        # Si el archivo está muy dañado, devolvemos estructura limpia para no romper el Main
        print(f"Aviso técnico en {os.path.basename(ruta)}: {e}")
    
    return bpm, key, func, cues_vacia, gen

def escribir_tags_ufulu(ruta, bpm, funcion, cues=None):
    """Sella el ADN en el archivo físico compatible con Traktor Pro"""
    try:
        if ruta.lower().endswith('.mp3'):
            audio = ID3(ruta)
            # TBPM: BPM | TPE4: Remixer (Función Ufulu)
            audio.add(TBPM(encoding=3, text=str(bpm)))
            audio.add(TPE4(encoding=3, text=str(funcion)))
            
            if cues:
                # Borramos comentarios previos de UFULU para evitar duplicados e hinchado del archivo
                audio.delall('COMM')
                cue_list = [f"{k}:{v:.3f}" for k, v in cues.items() if v is not None]
                if cue_list:
                    serializado = "UFULU_CUES|" + "|".join(cue_list)
                    audio.add(COMM(encoding=3, lang='eng', desc='UFULU_DATA', text=serializado))
            
            audio.save(v2_version=3)
            return True
    except Exception as e:
        print(f"Error escritura física en {os.path.basename(ruta)}: {e}")
        return False
    return False

def inyectar_bloque_ufulu(lista_tareas):
    """
    Procesador de Inyección Masiva Secuencial.
    Sincronizado con MainApp.save_selected
    """
    exitos, fallos = 0, 0
    for tarea in lista_tareas:
        # Sincronizamos los 4 parámetros: path, bpm, func y cues
        res = escribir_tags_ufulu(
            tarea['path'], 
            tarea['bpm'], 
            tarea['func'],
            tarea.get('cues') # Recuperamos los marcadores si existen
        )
        if res: 
            exitos += 1
        else: 
            fallos += 1
    return exitos, fallos
