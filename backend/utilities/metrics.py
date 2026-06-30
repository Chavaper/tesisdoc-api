# backend/utilities/metrics.py
import re
import os

TARGET_KEYS = [
    "1.1.1", "1.1.2", "1.1.3", "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.3",
    "2.1", "2.2",
    "3.1", "3.2", "3.3", "3.4.1", "3.4.2", "3.4.3", "3.4.4", "3.5", "3.6", "3.7",
    "4",
    "5.1", "5.2",
    "Referencias", "Anexos"
]

def cargar_pesos(pesos_path=None):
    if pesos_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pesos_path = os.path.join(base_dir, "estructuraTesis", "pesos.txt")
    
    pesos = {}
    default_pesos = {
        "1.1.1": 0.025, "1.1.2": 0.02, "1.1.3": 0.025, "1.2.1": 0.02,
        "1.2.2": 0.03, "1.2.3": 0.03, "1.2.4": 0.03, "1.3": 0.02,
        "2.1": 0.03, "2.2": 0.12,
        "3.1": 0.01, "3.2": 0.02, "3.3": 0.02, "3.4.1": 0.01, "3.4.2": 0.01,
        "3.4.3": 0.01, "3.4.4": 0.01, "3.5": 0.03, "3.6": 0.06, "3.7": 0.02,
        "4": 0.30,
        "5.1": 0.075, "5.2": 0.025,
        "Referencias": 0.03, "Anexos": 0.02
    }
    
    try:
        if os.path.exists(pesos_path):
            with open(pesos_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        code = parts[0]
                        weight_str = parts[1].replace("%", "")
                        pesos[code] = float(weight_str) / 100.0
            for key in TARGET_KEYS:
                if key not in pesos:
                    pesos[key] = default_pesos[key]
        else:
            pesos = default_pesos
    except Exception:
        pesos = default_pesos
        
    return pesos

def find_target_key(title):
    if not title:
        return None
    title_lower = title.lower().strip()
    if 'referencia' in title_lower:
        return 'Referencias'
    if 'anexo' in title_lower:
        return 'Anexos'
    if 'capítulo 4' in title_lower or 'capitulo 4' in title_lower or 'capítulo iv' in title_lower or 'capitulo iv' in title_lower:
        return '4'
    
    match = re.match(r'^([0-9]+(\.[0-9]+)*)', title_lower)
    if match:
        code = match.group(1)
        if code in TARGET_KEYS:
            return code
            
    match_any = re.search(r'\b([0-9]+\.[0-9]+(\.[0-9]+)*)\b', title_lower)
    if match_any:
        code = match_any.group(1)
        if code in TARGET_KEYS:
            return code
            
    if title_lower.startswith("4.") or title_lower.startswith("4 "):
        return "4"
        
    return None

def calcular_metricas_version(mapa_actual, mapa_anterior=None):
    """
    Calcula CP, Estabilidad y Profundidad para la versión actual.
    mapa_actual: mapa de path -> seccion del documento actual
    mapa_anterior: mapa de path -> seccion del documento anterior (opcional)
    """
    pesos = cargar_pesos()
    
    # 1. Agrupar secciones del documento por su Target Key matched
    secciones_por_target = {}
    for path, sec in mapa_actual.items():
        key = find_target_key(sec["titulo"])
        if key:
            if key not in secciones_por_target:
                secciones_por_target[key] = {
                    "word_count": 0,
                    "nivel": 1
                }
            secciones_por_target[key]["word_count"] += sec["word_count"]
            secciones_por_target[key]["nivel"] = max(secciones_por_target[key]["nivel"], sec["nivel"])

    # 2. Calcular Cobertura Ponderada (CP) & Profundidad (Depth)
    n = len(TARGET_KEYS) # 25
    sum_p_c = 0.0
    sum_p = 0.0
    sum_d = 0
    
    for key in TARGET_KEYS:
        p_i = pesos.get(key, 0.0)
        sum_p += p_i
        
        c_i = 0
        d_i = 0
        if key in secciones_por_target:
            words = secciones_por_target[key]["word_count"]
            d_i = secciones_por_target[key]["nivel"]
            
            limit = 200 if key == "4" else 15
            if words >= limit:
                c_i = 1
                
        sum_p_c += p_i * c_i
        sum_d += d_i
        
    cobertura_ponderada = sum_p_c / sum_p if sum_p > 0 else 0.0
    profundidad = sum_d / n
    
    # 3. Calcular Estabilidad
    if mapa_anterior is None:
        estabilidad = 0.0
    else:
        total_modified_words = 0
        all_paths = set(mapa_actual.keys()) | set(mapa_anterior.keys())
        for path in all_paths:
            w1 = mapa_anterior[path]["word_count"] if path in mapa_anterior else 0
            w2 = mapa_actual[path]["word_count"] if path in mapa_actual else 0
            total_modified_words += abs(w2 - w1)
            
        total_words = sum(s["word_count"] for s in mapa_actual.values())
        if total_words > 0:
            estabilidad = max(0.0, 1.0 - (total_modified_words / total_words))
        else:
            estabilidad = 0.0
            
    return {
        "cobertura_ponderada": round(cobertura_ponderada, 4),
        "estabilidad": round(estabilidad, 4),
        "profundidad": round(profundidad, 4)
    }
