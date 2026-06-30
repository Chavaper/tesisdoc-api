# backend/schemas/schemas.py
from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional, Dict, Any


class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str

class GoogleAuthRequest(BaseModel):
    credential: str  # ID token de Google

class UserResponse(BaseModel):
    id: int
    nombre: str
    correo: str
    rol: str

    class Config:
        from_attributes = True   # permite convertir modelo SQLAlchemy


class AlumnoInfo(BaseModel):
    nombre: str
    correo: str

class TesisAsesorResponse(BaseModel):
    id: int
    nombre: str
    alumnos: List[str]   # lista de nombres de alumnos
    ultima_version_numero: int
    ultima_version_fecha: date
    salud: str
    ultima_version_id: Optional[int] = None


class MetricasDoc(BaseModel):
    cobertura_ponderada: Optional[float] = None
    velocidad_escritura: Optional[float] = None
    indice_estabilidad: Optional[float] = None
    indice_profundidad: Optional[float] = None

class VersionResponse(BaseModel):
    id: int
    numero_version: int
    fecha: datetime
    nombre_archivo: str
    tamanio: int  # en bytes
    metricas: Optional[MetricasDoc] = None

class TesisResponse(BaseModel):
    id: int
    nombre: str
    versiones: List[VersionResponse]


class CambioSeccion(BaseModel):
    tipo: str  # "SECCION_NUEVA", "SECCION_ELIMINADA", "MODIFICADO"
    path: str
    existe_en: Optional[str] = None
    documento_1: Optional[str] = None
    documento_2: Optional[str] = None
    palabras_doc1: Optional[int] = None
    palabras_doc2: Optional[int] = None
    delta: Optional[int] = None
    cambio_detectado_en: Optional[str] = None
    posible_comentario_levantado: Optional[bool] = None

class MetricasAutomaticas(BaseModel):
    cobertura_tesis: float
    velocidad_escritura: float
    estabilidad: float
    profundidad: float

class ResultadoComparacion(BaseModel):
    secciones_nuevas: int
    secciones_eliminadas: int
    secciones_modificadas: int
    comentarios_resueltos: int
    metricas_automaticas: MetricasAutomaticas
    cambios_por_capitulo: Dict[str, List[CambioSeccion]]
    crecimiento_palabras: int
    crecimiento_porcentaje: str
    promedio_palabras_por_seccion: int