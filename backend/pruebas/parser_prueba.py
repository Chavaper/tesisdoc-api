import zipfile
from lxml import etree
import json

# =========================================
# CONFIGURACIÓN
# =========================================

DOCX_PATH = "v2.docx"

# Namespace de Word
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
}

# =========================================
# EXTRAER document.xml
# =========================================

with zipfile.ZipFile(DOCX_PATH, "r") as docx:
    xml_content = docx.read("word/document.xml")

# Parsear XML
root = etree.fromstring(xml_content)

# =========================================
# MAPA DE ESTILOS → NIVEL
# =========================================

def obtener_nivel_estilo(style_id):

    if not style_id:
        return None

    style_id = style_id.lower()

    # Word en español
    if style_id == "ttulo1":
        return 1

    if style_id == "ttulo2":
        return 2

    if style_id == "ttulo3":
        return 3

    if style_id == "ttulo4":
        return 4

    # Word en inglés
    if style_id == "heading1":
        return 1

    if style_id == "heading2":
        return 2

    if style_id == "heading3":
        return 3

    if style_id == "heading4":
        return 4

    return None

# =========================================
# EXTRAER TÍTULOS
# =========================================

titulos = []

parrafos = root.xpath("//w:body/w:p", namespaces=NS)

for p in parrafos:

    # Obtener estilo
    style = p.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)

    style_id = style[0] if style else None

    nivel = obtener_nivel_estilo(style_id)

    if nivel is None:
        continue

    # Obtener texto completo del párrafo
    textos = p.xpath(".//w:t/text()", namespaces=NS)

    titulo = "".join(textos).strip()

    if not titulo:
        continue

    titulos.append({
        "nivel": nivel,
        "titulo": titulo
    })

# =========================================
# CONSTRUIR ÁRBOL JERÁRQUICO
# =========================================

def construir_jerarquia(items):

    raiz = []
    stack = []

    for item in items:

        nodo = {
            "titulo": item["titulo"],
            "nivel": item["nivel"],
            "subsecciones": []
        }

        # Vaciar stack hasta encontrar padre válido
        while stack and stack[-1]["nivel"] >= nodo["nivel"]:
            stack.pop()

        # Si no hay padre → raíz
        if not stack:
            raiz.append(nodo)

        else:
            stack[-1]["subsecciones"].append(nodo)

        stack.append(nodo)

    return raiz

estructura = construir_jerarquia(titulos)

# =========================================
# MOSTRAR RESULTADO
# =========================================

print(json.dumps(
    estructura,
    indent=4,
    ensure_ascii=False
))