# backend/routers/asesor.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from conexionBD.database import SessionLocal
from models.models import Usuario, Tesis, UsuarioTesis, VersionDoc, Metrica, Documento
from routers.dependencies import get_current_user, require_role
from schemas.schemas import TesisAsesorResponse, AlumnoInfo, VersionResponse, MetricasDoc

router = APIRouter(prefix="/asesor", tags=["asesor"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def calcular_salud(metrica: Metrica | None) -> str:
    """Calcula el estado de salud basado en la métrica de cobertura_ponderada."""
    if metrica is None or metrica.cobertura_ponderada is None:
        return "Bien"  # por defecto
    cobertura = float(metrica.cobertura_ponderada)
    if cobertura >= 0.8:
        return "Bien"
    elif cobertura >= 0.5:
        return "En camino"
    else:
        return "Crítico"

@router.get("/tesis", response_model=List[TesisAsesorResponse])
async def get_tesis_asesor(
    current_user: Usuario = Depends(require_role("asesor")),
    db: Session = Depends(get_db)
):
    """Lista todas las tesis asociadas al asesor autenticado."""
    # Buscar todas las relaciones UsuarioTesis donde el usuario es el asesor
    relaciones = db.query(UsuarioTesis).filter(UsuarioTesis.usuario_id == current_user.id).all()
    tesis_ids = [rel.tesis_id for rel in relaciones]
    tesis = db.query(Tesis).filter(Tesis.id.in_(tesis_ids)).all()

    resultado = []
    for t in tesis:
        # Obtener los alumnos (usuarios con rol 'tesista') asociados a esta tesis
        alumnos = (
            db.query(Usuario)
            .join(UsuarioTesis, UsuarioTesis.usuario_id == Usuario.id)
            .filter(UsuarioTesis.tesis_id == t.id, Usuario.rol == "tesista")
            .all()
        )
        nombres_alumnos = [a.nombre for a in alumnos]

        # Obtener la última versión de la tesis
        ultima_version = (
            db.query(VersionDoc)
            .filter(VersionDoc.tesis_id == t.id)
            .order_by(VersionDoc.numero_version.desc())
            .first()
        )

        if ultima_version:
            ultimo_numero = ultima_version.numero_version
            ultima_fecha = ultima_version.fecha.date() if ultima_version.fecha else date.today()
            # Obtener métrica asociada a esa versión
            metrica = db.query(Metrica).filter(Metrica.version_id == ultima_version.id).first()
            salud = calcular_salud(metrica)
            ultima_version_id = ultima_version.id
        else:
            ultimo_numero = 1
            ultima_fecha = date.today()
            salud = "Bien"
            ultima_version_id = None

        resultado.append(TesisAsesorResponse(
            id=t.id,
            nombre=t.nombre,
            alumnos=nombres_alumnos,
            ultima_version_numero=ultimo_numero,
            ultima_version_fecha=ultima_fecha,
            salud=salud,
            ultima_version_id=ultima_version_id
        ))

    return resultado

@router.get("/tesis/{tesis_id}/versiones", response_model=List[VersionResponse])
async def obtener_versiones_tesis_asesor(
    tesis_id: int,
    current_user: Usuario = Depends(require_role("asesor")),
    db: Session = Depends(get_db)
):
    """Devuelve la lista de versiones con sus métricas para una tesis específica, accesible por el asesor"""
    # Verificar que el asesor tenga acceso a esta tesis
    relacion = db.query(UsuarioTesis).filter(UsuarioTesis.usuario_id == current_user.id, UsuarioTesis.tesis_id == tesis_id).first()
    if not relacion:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta tesis")
        
    versiones = db.query(VersionDoc).filter(VersionDoc.tesis_id == tesis_id).order_by(VersionDoc.numero_version.desc()).all()
    versiones_data = []
    for v in versiones:
        doc = db.query(Documento).filter(Documento.version_id == v.id).first()
        metrica = db.query(Metrica).filter(Metrica.version_id == v.id).first()
        
        metricas_data = None
        if metrica:
            metricas_data = MetricasDoc(
                cobertura_ponderada=float(metrica.cobertura_ponderada) if metrica.cobertura_ponderada is not None else None,
                velocidad_escritura=float(metrica.velocidad_escritura) if metrica.velocidad_escritura is not None else None,
                indice_estabilidad=float(metrica.indice_estabilidad) if metrica.indice_estabilidad is not None else None,
                indice_profundidad=float(metrica.indice_profundidad) if metrica.indice_profundidad is not None else None
            )
            
        versiones_data.append(VersionResponse(
            id=v.id,
            numero_version=v.numero_version,
            fecha=v.fecha,
            nombre_archivo=doc.nombre if doc else f"version_{v.numero_version}.docx",
            tamanio=doc.tamanio if doc else 0,
            metricas=metricas_data
        ))
        
    return versiones_data

@router.get("/versiones/{version_id}/descargar")
async def descargar_version_asesor(
    version_id: int,
    current_user: Usuario = Depends(require_role("asesor")),
    db: Session = Depends(get_db)
):
    """Descarga el archivo de una versión específica para el asesor"""
    version = db.query(VersionDoc).filter(VersionDoc.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Versión no encontrada")

    # Verificar que el asesor tenga acceso a esta tesis
    relacion = db.query(UsuarioTesis).filter(UsuarioTesis.usuario_id == current_user.id, UsuarioTesis.tesis_id == version.tesis_id).first()
    if not relacion:
        raise HTTPException(status_code=403, detail="No tienes acceso a este archivo")

    doc = db.query(Documento).filter(Documento.version_id == version_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    from io import BytesIO
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        BytesIO(doc.archivo),
        media_type=doc.mime_type,
        headers={"Content-Disposition": f"attachment; filename={doc.nombre}"}
    )