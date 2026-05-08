# playlist_exporters.py
# UFULU RODEC EDITION - EXPORTADORES DE PLAN DE VUELO v33.7
# =========================================================
# - M3U8                    (compatibles VLC, foobar, Mixxx)
# - Traktor NML  + HotCues  (CUE_V2 inyectados)
# - Rekordbox XML + HotCues (POSITION_MARK)
# - PDF Sesión              (reportlab)
# =========================================================

import os
import urllib.parse
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime


# =========================================================
# Helpers
# =========================================================
def _row(item):
    """Devuelve la tupla de datos del track desde el item de playlist."""
    return item.get("data") or []


def _safe(val, default=""):
    return str(val) if val is not None else default


def _ruta_a_uri(path: str) -> str:
    """file:// con encoding correcto para Traktor / Rekordbox."""
    p = os.path.abspath(path).replace("\\", "/")
    return "file://localhost/" + urllib.parse.quote(p, safe="/:")


def _xml_pretty(root) -> bytes:
    raw = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(raw).toprettyxml(indent="  ", encoding="utf-8")


# =========================================================
# 1) M3U8 (UTF-8 con BOM, listo para VLC/Mixxx)
# =========================================================
def exportar_m3u8(playlist, ruta_salida: str):
    if not playlist:
        raise ValueError("Plan de vuelo vacío.")
    if not ruta_salida.lower().endswith(".m3u8"):
        ruta_salida += ".m3u8"
    with open(ruta_salida, "w", encoding="utf-8-sig") as f:
        f.write("#EXTM3U\n")
        f.write(f"# UFULU RODEC EDITION  ·  {datetime.now().isoformat(timespec='seconds')}\n")
        for item in playlist:
            d = _row(item)
            if len(d) < 6:
                continue
            path = _safe(d[5])
            if not path:
                continue
            nombre = _safe(d[0]) or os.path.basename(path)
            bpm = _safe(d[1])
            f.write(f"#EXTINF:-1, {nombre}  [{bpm} BPM]\n")
            f.write(f"{os.path.abspath(path)}\n")
    return ruta_salida


# =========================================================
# 2) Traktor NML (con CUE_V2 inyectados)
# =========================================================
# Tipos CUE_V2 Traktor:
#   0 = Cue,  1 = Fade-In, 2 = Fade-Out,
#   3 = Load, 4 = Grid, 5 = Loop
def exportar_nml_traktor(playlist, ruta_salida: str, cues_por_path: dict = None):
    if not playlist:
        raise ValueError("Plan de vuelo vacío.")
    if not ruta_salida.lower().endswith(".nml"):
        ruta_salida += ".nml"
    cues_por_path = cues_por_path or {}

    nml = ET.Element("NML", attrib={"VERSION": "19"})
    ET.SubElement(nml, "HEAD", attrib={
        "COMPANY": "Native Instruments",
        "PROGRAM": "Traktor"
    })
    collection = ET.SubElement(nml, "COLLECTION", attrib={
        "ENTRIES": str(len(playlist))
    })

    for item in playlist:
        d = _row(item)
        if len(d) < 6:
            continue
        path = _safe(d[5])
        if not path:
            continue
        path_abs = os.path.abspath(path)
        bpm = _safe(d[1], "0")
        key = _safe(d[7], "") if len(d) > 7 else ""
        titulo = _safe(d[0]) or os.path.basename(path)

        drive, rest = os.path.splitdrive(path_abs)
        carpeta_padre = os.path.dirname(rest).replace("\\", "/").lstrip("/")
        if carpeta_padre and not carpeta_padre.endswith("/"):
            carpeta_padre += "/"
        volumen = drive.replace(":", "") if drive else ""

        entry = ET.SubElement(collection, "ENTRY", attrib={
            "MODIFIED_DATE": datetime.now().strftime("%Y/%m/%d"),
            "MODIFIED_TIME": datetime.now().strftime("%H:%M:%S"),
            "TITLE": titulo,
            "ARTIST": "",
        })
        ET.SubElement(entry, "LOCATION", attrib={
            "DIR": "/:" + carpeta_padre.replace("/", "/:"),
            "FILE": os.path.basename(path_abs),
            "VOLUME": volumen,
            "VOLUMEID": volumen,
        })
        ET.SubElement(entry, "ALBUM", attrib={"TITLE": ""})
        try:
            tempo_val = float(bpm) if bpm else 0.0
        except Exception:
            tempo_val = 0.0
        ET.SubElement(entry, "TEMPO", attrib={
            "BPM": f"{tempo_val:.6f}",
            "BPM_QUALITY": "100.000000",
        })
        if key:
            ET.SubElement(entry, "MUSICAL_KEY", attrib={"VALUE": "0"})
            ET.SubElement(entry, "INFO", attrib={"KEY": key})

        # === HOTCUES (UFULU) ===
        cues = cues_por_path.get(path_abs) or cues_por_path.get(path) or {}
        for n_cue, t_seg in sorted(cues.items()):
            try:
                start_ms = float(t_seg) * 1000.0
            except Exception:
                continue
            ET.SubElement(entry, "CUE_V2", attrib={
                "NAME":     f"UFULU M{n_cue}",
                "DISPL_ORDER": "0",
                "TYPE":     "0",          # cue normal
                "START":    f"{start_ms:.6f}",
                "LEN":      "0.000000",
                "REPEATS":  "-1",
                "HOTCUE":   str(int(n_cue) - 1),  # Traktor 0..7
            })

    # PLAYLIST nodo
    playlists = ET.SubElement(nml, "PLAYLISTS")
    node = ET.SubElement(playlists, "NODE", attrib={
        "TYPE": "FOLDER", "NAME": "$ROOT"
    })
    subnodes = ET.SubElement(node, "SUBNODES", attrib={"COUNT": "1"})
    pnode = ET.SubElement(subnodes, "NODE", attrib={
        "TYPE": "PLAYLIST", "NAME": "UFULU SESSION"
    })
    pl = ET.SubElement(pnode, "PLAYLIST", attrib={
        "ENTRIES": str(len(playlist)),
        "TYPE": "LIST",
        "UUID": "ufulu-" + datetime.now().strftime("%Y%m%d%H%M%S"),
    })
    for item in playlist:
        d = _row(item)
        if len(d) < 6:
            continue
        path = _safe(d[5])
        if not path:
            continue
        path_abs = os.path.abspath(path)
        drive, rest = os.path.splitdrive(path_abs)
        rest_n = rest.replace("\\", "/")
        if not rest_n.startswith("/"):
            rest_n = "/" + rest_n
        primary = ET.SubElement(pl, "ENTRY")
        primary_key = (drive.replace(":", "") if drive else "") + "/:" + rest_n.replace("/", "/:")
        ET.SubElement(primary, "PRIMARYKEY", attrib={
            "TYPE": "TRACK",
            "KEY":  primary_key,
        })

    pretty = _xml_pretty(nml)
    with open(ruta_salida, "wb") as f:
        f.write(pretty)
    return ruta_salida


# =========================================================
# 3) Rekordbox XML (con POSITION_MARK)
# =========================================================
def exportar_xml_rekordbox(playlist, ruta_salida: str, cues_por_path: dict = None):
    if not playlist:
        raise ValueError("Plan de vuelo vacío.")
    if not ruta_salida.lower().endswith(".xml"):
        ruta_salida += ".xml"
    cues_por_path = cues_por_path or {}

    root = ET.Element("DJ_PLAYLISTS", attrib={"Version": "1.0.0"})
    ET.SubElement(root, "PRODUCT", attrib={
        "Name": "rekordbox", "Version": "6.0", "Company": "AlphaTheta"
    })
    collection = ET.SubElement(root, "COLLECTION", attrib={
        "Entries": str(len(playlist))
    })

    track_id_map = {}
    for i, item in enumerate(playlist, 1):
        d = _row(item)
        if len(d) < 6:
            continue
        path = _safe(d[5])
        if not path:
            continue
        path_abs = os.path.abspath(path)
        bpm = _safe(d[1], "0")
        key = _safe(d[7], "") if len(d) > 7 else ""
        titulo = _safe(d[0]) or os.path.basename(path_abs)

        try: bpm_f = float(bpm)
        except Exception: bpm_f = 0.0

        track = ET.SubElement(collection, "TRACK", attrib={
            "TrackID":  str(i),
            "Name":     titulo,
            "Artist":   "",
            "Album":    "",
            "Genre":    _safe(d[4]) if len(d) > 4 else "",
            "Kind":     "MP3 File" if path.lower().endswith(".mp3") else "FLAC File",
            "Size":     str(os.path.getsize(path_abs)) if os.path.exists(path_abs) else "0",
            "TotalTime": "0",
            "AverageBpm": f"{bpm_f:.2f}",
            "DateAdded": datetime.now().strftime("%Y-%m-%d"),
            "BitRate":   "320",
            "SampleRate": "44100",
            "Tonality": key,
            "Location":  _ruta_a_uri(path_abs),
        })

        cues = cues_por_path.get(path_abs) or cues_por_path.get(path) or {}
        for n_cue, t_seg in sorted(cues.items()):
            try:
                start = float(t_seg)
            except Exception:
                continue
            ET.SubElement(track, "POSITION_MARK", attrib={
                "Name":  f"UFULU M{n_cue}",
                "Type":  "0",
                "Start": f"{start:.3f}",
                "Num":   str(int(n_cue) - 1),  # 0..7
            })
        track_id_map[path_abs] = i

    # NODO PLAYLIST
    playlists = ET.SubElement(root, "PLAYLISTS")
    node_root = ET.SubElement(playlists, "NODE", attrib={
        "Type": "0", "Name": "ROOT", "Count": "1"
    })
    node_pl = ET.SubElement(node_root, "NODE", attrib={
        "Name": "UFULU SESSION",
        "Type": "1",
        "KeyType": "0",
        "Entries": str(len(track_id_map)),
    })
    for tid in track_id_map.values():
        ET.SubElement(node_pl, "TRACK", attrib={"Key": str(tid)})

    pretty = _xml_pretty(root)
    with open(ruta_salida, "wb") as f:
        f.write(pretty)
    return ruta_salida


# =========================================================
# 4) PDF (reportlab)
# =========================================================
def exportar_pdf_sesion(playlist, ruta_salida: str,
                        params: dict = None,
                        rating: int = 0,
                        notas_sesion: str = "",
                        notas_por_path: dict = None):
    """
    Genera un informe imprimible de la sesión.
    Requiere `reportlab`.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        )
    except ImportError as e:
        raise ImportError("Falta `reportlab`. Instálalo con: pip install reportlab") from e

    if not playlist:
        raise ValueError("Plan de vuelo vacío.")
    if not ruta_salida.lower().endswith(".pdf"):
        ruta_salida += ".pdf"

    params = params or {}
    notas_por_path = notas_por_path or {}

    doc = SimpleDocTemplate(
        ruta_salida, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=15 * mm,  bottomMargin=15 * mm,
        title="UFULU SESSION", author="UFULU Rodec Edition"
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"],
                        textColor=colors.HexColor("#00875a"),
                        fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"],
                        textColor=colors.HexColor("#444"), fontSize=12)
    body = ParagraphStyle("body", parent=styles["BodyText"],
                          fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=styles["BodyText"],
                           fontSize=8, leading=10,
                           textColor=colors.HexColor("#666"))

    story = []
    story.append(Paragraph("UFULU · RODEC EDITION", h1))
    story.append(Paragraph(
        f"Hoja de Cabina · {datetime.now().strftime('%Y-%m-%d %H:%M')}", h2))
    story.append(Spacer(1, 6))

    # Parámetros sesión
    p_lines = [
        f"<b>Iluminación:</b> {params.get('luz','-')}",
        f"<b>Momento:</b> {params.get('momento','-')}",
        f"<b>Estilo base:</b> {params.get('estilo','-')}",
        f"<b>Densidad:</b> {params.get('densidad','-')}",
        f"<b>Duración:</b> {params.get('duracion','-')} min",
    ]
    story.append(Paragraph(" &nbsp; · &nbsp; ".join(p_lines), body))
    if rating:
        story.append(Paragraph(
            f"<b>Rating:</b> {'★' * int(rating)}{'☆' * (5 - int(rating))}", body))
    if notas_sesion:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Notas:</b> {notas_sesion}", body))
    story.append(Spacer(1, 8))

    # Tabla de tracks
    cab = ["#", "Inicio", "Acto", "Track", "BPM", "KEY", "Motivo"]
    data = [cab]
    for i, item in enumerate(playlist, 1):
        d = _row(item)
        track_name = os.path.basename(_safe(d[0])) if d else "?"
        bpm = _safe(d[1]) if len(d) > 1 else "-"
        key = _safe(d[7]) if len(d) > 7 else "-"
        data.append([
            str(i),
            _safe(item.get("tiempo")),
            _safe(item.get("acto")),
            Paragraph(track_name[:60], body),
            bpm,
            key,
            Paragraph(_safe(item.get("motivo"))[:60], small),
        ])
    tabla = Table(data, colWidths=[10 * mm, 16 * mm, 24 * mm,
                                   60 * mm, 12 * mm, 12 * mm, 38 * mm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#00ffcc")),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fafafa")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.HexColor("#fafafa"), colors.HexColor("#eef0ef")]),
        ("FONTSIZE",   (0, 1), (-1, -1), 8),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor("#bbb")),
    ]))
    story.append(tabla)

    # Notas por tema
    if notas_por_path:
        story.append(PageBreak())
        story.append(Paragraph("NOTAS POR TEMA", h2))
        story.append(Spacer(1, 4))
        for path, notas in notas_por_path.items():
            if not notas:
                continue
            story.append(Paragraph(
                f"<b>{os.path.basename(path)}</b>", body))
            story.append(Paragraph(notas, small))
            story.append(Spacer(1, 4))

    doc.build(story)
    return ruta_salida
