# backend/pruebas/test_metrics.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utilities.parser import procesar_bytes
from utilities.metrics import calcular_metricas_version, cargar_pesos

def test_calculo_metricas():
    v1_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "utilities", "v1.docx")
    v2_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "utilities", "v2.docx")

    # Load weights
    pesos = cargar_pesos()
    print(f"Pesos cargados exitosamente. Cantidad de secciones con pesos: {len(pesos)}")
    
    # Process files
    with open(v1_path, "rb") as f:
        v1_bytes = f.read()
    with open(v2_path, "rb") as f:
        v2_bytes = f.read()
        
    mapa_v1 = procesar_bytes(v1_bytes)
    mapa_v2 = procesar_bytes(v2_bytes)
    
    print("\n--- Métrica Versión 1 (Primera vez subida: estabilidad = 0) ---")
    metricas_v1 = calcular_metricas_version(mapa_v1, mapa_anterior=None)
    print("CP (Weighted Coverage):", metricas_v1["cobertura_ponderada"])
    print("Estabilidad (Stability):", metricas_v1["estabilidad"])
    print("Profundidad (Depth):", metricas_v1["profundidad"])
    
    # Assertions for Version 1
    assert metricas_v1["estabilidad"] == 0.0, "Version 1 stability must be 0"
    assert metricas_v1["cobertura_ponderada"] > 0, "CP must be non-zero"
    assert metricas_v1["profundidad"] > 0, "Depth must be non-zero"

    print("\n--- Métrica Versión 2 (Subida secuencial) ---")
    metricas_v2 = calcular_metricas_version(mapa_v2, mapa_anterior=mapa_v1)
    print("CP (Weighted Coverage):", metricas_v2["cobertura_ponderada"])
    print("Estabilidad (Stability):", metricas_v2["estabilidad"])
    print("Profundidad (Depth):", metricas_v2["profundidad"])
    
    # Assertions for Version 2
    assert metricas_v2["cobertura_ponderada"] > 0
    assert metricas_v2["profundidad"] > 0
    assert metricas_v2["estabilidad"] >= 0.0 and metricas_v2["estabilidad"] <= 1.0, "Stability should be between 0 and 1"
    
    print("\nTodos los tests pasaron exitosamente!")

if __name__ == "__main__":
    test_calculo_metricas()
