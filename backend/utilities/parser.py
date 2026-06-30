# backend/utilities/parser.py
import zipfile
from lxml import etree
from io import BytesIO
from collections import defaultdict

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

def obtener_nivel_estilo(style_id):
    if not style_id:
        return None
    style_id = style_id.lower()
    mapping = {
        "ttulo1": 1, "heading1": 1,
        "ttulo2": 2, "heading2": 2,
        "ttulo3": 3, "heading3": 3,
        "ttulo4": 4, "heading4": 4,
    }
    return mapping.get(style_id)

def extraer_xml(contenido_bytes):
    with zipfile.ZipFile(BytesIO(contenido_bytes), "r") as docx:
        xml_content = docx.read("word/document.xml")
    return etree.fromstring(xml_content)

def extraer_secciones(root):
    parrafos = root.xpath("//w:body/w:p", namespaces=NS)
    secciones = []
    current_section = None
    current_text = []

    for p in parrafos:
        style = p.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
        style_id = style[0] if style else None
        nivel = obtener_nivel_estilo(style_id)

        textos = p.xpath(".//w:t/text()", namespaces=NS)
        texto = "".join(textos).strip()

        if nivel is not None:
            if current_section:
                current_section["text"] = " ".join(current_text).strip()
                current_section["word_count"] = len(current_section["text"].split())
                secciones.append(current_section)
            current_section = {
                "titulo": texto,
                "nivel": nivel,
                "path": None,
                "text": "",
                "word_count": 0
            }
            current_text = []
        else:
            if current_section and texto:
                current_text.append(texto)

    if current_section:
        current_section["text"] = " ".join(current_text).strip()
        current_section["word_count"] = len(current_section["text"].split())
        secciones.append(current_section)
    return secciones

def construir_paths(secciones):
    stack = []
    for sec in secciones:
        while stack and stack[-1]["nivel"] >= sec["nivel"]:
            stack.pop()
        parent_path = "/".join([s["titulo"] for s in stack])
        sec["path"] = parent_path + "/" + sec["titulo"] if parent_path else sec["titulo"]
        stack.append(sec)
    return secciones

def crear_mapa(secciones):
    return {s["path"]: s for s in secciones}

def procesar_bytes(contenido_bytes):
    root = extraer_xml(contenido_bytes)
    secciones = extraer_secciones(root)
    secciones = construir_paths(secciones)
    return crear_mapa(secciones)

def comparar_mapa(v1_map, v2_map, doc1_nombre, doc2_nombre):
    cambios = []
    all_paths = set(v1_map.keys()) | set(v2_map.keys())
    for path in all_paths:
        s1 = v1_map.get(path)
        s2 = v2_map.get(path)

        if not s1:
            cambios.append({"tipo": "SECCION_NUEVA", "path": path, "existe_en": doc2_nombre})
            continue
        if not s2:
            cambios.append({"tipo": "SECCION_ELIMINADA", "path": path, "existe_en": doc1_nombre})
            continue

        diff = s2["word_count"] - s1["word_count"]
        if diff != 0:
            cambio = {
                "tipo": "MODIFICADO",
                "path": path,
                "documento_1": doc1_nombre,
                "documento_2": doc2_nombre,
                "palabras_doc1": s1["word_count"],
                "palabras_doc2": s2["word_count"],
                "delta": diff,
                "cambio_detectado_en": doc2_nombre if diff > 0 else doc1_nombre,
                "posible_comentario_levantado": abs(diff) > 5
            }
            cambios.append(cambio)
    return cambios