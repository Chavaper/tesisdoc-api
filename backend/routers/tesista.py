# backend/routers/tesista.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from io import BytesIO
from conexionBD.database import SessionLocal
from models.models import Usuario, Tesis, VersionDoc, Documento, UsuarioTesis, Metrica
from routers.dependencies import get_current_user, require_role
from schemas.schemas import TesisResponse, VersionResponse, ResultadoComparacion, MetricasAutomaticas, CambioSeccion, MetricasDoc
from utilities.parser import procesar_bytes, comparar_mapa
from utilities.metrics import calcular_metricas_version
from collections import defaultdict



router = APIRouter(prefix="/tesista", tags=["tesista"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_tesis_activa(db: Session, usuario_id: int) -> Optional[Tesis]:
    """Obtiene la primera tesis asociada al tesista (asumimos una sola tesis por tesista)"""
    usuario_tesis = db.query(UsuarioTesis).filter(UsuarioTesis.usuario_id == usuario_id).first()
    if usuario_tesis:
        return db.query(Tesis).filter(Tesis.id == usuario_tesis.tesis_id).first()
    return None

@router.get("/tesis", response_model=TesisResponse)
async def obtener_tesis_y_versiones(
    current_user: Usuario = Depends(require_role("tesista")),
    db: Session = Depends(get_db)
):
    """Devuelve la tesis del tesista (si existe) y todas sus versiones ordenadas por fecha descendente"""
    tesis = get_tesis_activa(db, current_user.id)
    if not tesis:
        raise HTTPException(status_code=404, detail="No tienes ninguna tesis aún")

    versiones = db.query(VersionDoc).filter(VersionDoc.tesis_id == tesis.id).order_by(VersionDoc.numero_version.desc()).all()
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

    return TesisResponse(
        id=tesis.id,
        nombre=tesis.nombre,
        versiones=versiones_data
    )

@router.post("/tesis", status_code=201)
async def crear_primera_tesis(
    archivo: UploadFile = File(...),
    current_user: Usuario = Depends(require_role("tesista")),
    db: Session = Depends(get_db)
):
    """Sube la primera tesis (crea registro en Tesis, VersionDoc y Documento)"""
    # Validar extensión
    if not archivo.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .docx")

    # Verificar que el tesista no tenga ya una tesis
    tesis_existente = get_tesis_activa(db, current_user.id)
    if tesis_existente:
        raise HTTPException(status_code=400, detail="Ya tienes una tesis. Usa 'Nueva versión' para actualizar.")

    # Leer contenido del archivo
    contenido = await archivo.read()
    tamanio = len(contenido)

    # Crear tesis con nombre del archivo
    nueva_tesis = Tesis(
        nombre=archivo.filename,
        ultima_version_id=None,
        version_final_id=None
    )
    db.add(nueva_tesis)
    db.flush()  # para obtener el id

    # Crear primera versión
    primera_version = VersionDoc(
        tesis_id=nueva_tesis.id,
        usuario_id=current_user.id,
        numero_version=1,
        version_anterior_id=None
    )
    db.add(primera_version)
    db.flush()

    # Crear documento asociado
    doc = Documento(
        tamanio=tamanio,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        nombre=archivo.filename,
        version_id=primera_version.id,
        archivo=contenido
    )
    db.add(doc)

    # Actualizar ultima_version_id de la tesis
    nueva_tesis.ultima_version_id = primera_version.id

    # Asociar tesista a la tesis (UsuarioTesis)
    rel = UsuarioTesis(usuario_id=current_user.id, tesis_id=nueva_tesis.id)
    db.add(rel)

    # Calcular y guardar métricas para la versión 1
    try:
        mapa_actual = procesar_bytes(contenido)
        metricas_res = calcular_metricas_version(mapa_actual, mapa_anterior=None)
        
        metrica_obj = Metrica(
            version_id=primera_version.id,
            cobertura_ponderada=metricas_res["cobertura_ponderada"],
            velocidad_escritura=0.0,
            indice_estabilidad=0.0,  # Primer cargamento: estabilidad = 0
            indice_profundidad=metricas_res["profundidad"]
        )
        db.add(metrica_obj)
    except Exception as e:
        metrica_obj = Metrica(
            version_id=primera_version.id,
            cobertura_ponderada=0.0,
            velocidad_escritura=0.0,
            indice_estabilidad=0.0,
            indice_profundidad=0.0
        )
        db.add(metrica_obj)
        print(f"Error calculando métricas para primera tesis: {e}")

    db.commit()
    return {"message": "Tesis creada exitosamente", "tesis_id": nueva_tesis.id}

@router.post("/versiones", status_code=201)
async def subir_nueva_version(
    archivo: UploadFile = File(...),
    tesis_id: int = Form(...),
    current_user: Usuario = Depends(require_role("tesista")),
    db: Session = Depends(get_db)
):
    """Sube una nueva versión de la tesis existente"""
    if not archivo.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .docx")

    # Verificar que la tesis pertenezca al tesista
    tesis = db.query(Tesis).filter(Tesis.id == tesis_id).first()
    if not tesis:
        raise HTTPException(status_code=404, detail="Tesis no encontrada")

    relacion = db.query(UsuarioTesis).filter(UsuarioTesis.usuario_id == current_user.id, UsuarioTesis.tesis_id == tesis_id).first()
    if not relacion:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar esta tesis")

    # Obtener último número de versión
    ultima_version = db.query(VersionDoc).filter(VersionDoc.tesis_id == tesis_id).order_by(VersionDoc.numero_version.desc()).first()
    nuevo_numero = (ultima_version.numero_version + 1) if ultima_version else 1

    contenido = await archivo.read()
    tamanio = len(contenido)

    nueva_version = VersionDoc(
        tesis_id=tesis_id,
        usuario_id=current_user.id,
        numero_version=nuevo_numero,
        version_anterior_id=ultima_version.id if ultima_version else None
    )
    db.add(nueva_version)
    db.flush()

    doc = Documento(
        tamanio=tamanio,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        nombre=archivo.filename,
        version_id=nueva_version.id,
        archivo=contenido
    )
    db.add(doc)

    # Actualizar última versión de la tesis
    tesis.ultima_version_id = nueva_version.id

    # Calcular y guardar métricas para la nueva versión (vN, N > 1)
    try:
        mapa_actual = procesar_bytes(contenido)
        
        # Obtener archivo de la versión anterior
        doc_anterior = None
        if ultima_version:
            doc_anterior = db.query(Documento).filter(Documento.version_id == ultima_version.id).first()
            
        mapa_anterior = None
        if doc_anterior and doc_anterior.archivo:
            mapa_anterior = procesar_bytes(doc_anterior.archivo)
            
        metricas_res = calcular_metricas_version(mapa_actual, mapa_anterior)
        
        # Calcular velocidad de escritura (consistente con /comparar)
        if mapa_anterior:
            total_palabras_v1 = sum(s["word_count"] for s in mapa_anterior.values())
            total_palabras_v2 = sum(s["word_count"] for s in mapa_actual.values())
            crecimiento = total_palabras_v2 - total_palabras_v1
            velocidad = round(0.6 + crecimiento / 1000, 4)
        else:
            velocidad = 0.0
            
        metrica_obj = Metrica(
            version_id=nueva_version.id,
            cobertura_ponderada=metricas_res["cobertura_ponderada"],
            velocidad_escritura=velocidad,
            indice_estabilidad=metricas_res["estabilidad"],
            indice_profundidad=metricas_res["profundidad"]
        )
        db.add(metrica_obj)
    except Exception as e:
        metrica_obj = Metrica(
            version_id=nueva_version.id,
            cobertura_ponderada=0.0,
            velocidad_escritura=0.0,
            indice_estabilidad=0.0,
            indice_profundidad=0.0
        )
        db.add(metrica_obj)
        print(f"Error calculando métricas para versión {nuevo_numero}: {e}")

    db.commit()

    return {"message": f"Versión {nuevo_numero} subida correctamente", "version_id": nueva_version.id}

@router.get("/versiones/{version_id}/descargar")
async def descargar_version(
    version_id: int,
    current_user: Usuario = Depends(require_role("tesista")),
    db: Session = Depends(get_db)
):
    """Descarga el archivo de una versión específica"""
    version = db.query(VersionDoc).filter(VersionDoc.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Versión no encontrada")

    # Verificar que la tesis pertenezca al tesista
    relacion = db.query(UsuarioTesis).filter(UsuarioTesis.usuario_id == current_user.id, UsuarioTesis.tesis_id == version.tesis_id).first()
    if not relacion:
        raise HTTPException(status_code=403, detail="No tienes acceso a este archivo")

    doc = db.query(Documento).filter(Documento.version_id == version_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return StreamingResponse(
        BytesIO(doc.archivo),
        media_type=doc.mime_type,
        headers={"Content-Disposition": f"attachment; filename={doc.nombre}"}
    )

@router.delete("/versiones/{version_id}")
async def eliminar_version(
    version_id: int,
    current_user: Usuario = Depends(require_role("tesista")),
    db: Session = Depends(get_db)
):
    """Elimina una versión (solo si no es la única versión)"""
    version = db.query(VersionDoc).filter(VersionDoc.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Versión no encontrada")

    relacion = db.query(UsuarioTesis).filter(UsuarioTesis.usuario_id == current_user.id, UsuarioTesis.tesis_id == version.tesis_id).first()
    if not relacion:
        raise HTTPException(status_code=403, detail="No tienes permiso")

    # Verificar que no sea la única versión
    total_versiones = db.query(VersionDoc).filter(VersionDoc.tesis_id == version.tesis_id).count()
    if total_versiones <= 1:
        raise HTTPException(status_code=400, detail="No se puede eliminar la única versión de la tesis")

    # Eliminar documento y la versión
    db.query(Documento).filter(Documento.version_id == version_id).delete()
    db.delete(version)
    db.commit()
    return {"message": "Versión eliminada"}


@router.post("/comparar", response_model=ResultadoComparacion)
async def comparar_versiones(
    version1_id: int,
    version2_id: int,
    current_user: Usuario = Depends(require_role("tesista")),
    db: Session = Depends(get_db)
):
    # Obtener versiones y sus documentos
    v1 = db.query(VersionDoc).filter(VersionDoc.id == version1_id).first()
    v2 = db.query(VersionDoc).filter(VersionDoc.id == version2_id).first()
    if not v1 or not v2:
        raise HTTPException(404, "Versión no encontrada")
    
    # Verificar que ambas versiones pertenezcan a la misma tesis del tesista
    tesis = get_tesis_activa(db, current_user.id)
    if not tesis or v1.tesis_id != tesis.id or v2.tesis_id != tesis.id:
        raise HTTPException(403, "No tienes acceso a estas versiones")
    
    doc1 = db.query(Documento).filter(Documento.version_id == version1_id).first()
    doc2 = db.query(Documento).filter(Documento.version_id == version2_id).first()
    if not doc1 or not doc2:
        raise HTTPException(404, "Archivo no encontrado")
    
    # Procesar archivos
    mapa1 = procesar_bytes(doc1.archivo)
    mapa2 = procesar_bytes(doc2.archivo)
    cambios = comparar_mapa(mapa1, mapa2, doc1.nombre, doc2.nombre)
    
    # Estadísticas
    secciones_nuevas = sum(1 for c in cambios if c["tipo"] == "SECCION_NUEVA")
    secciones_eliminadas = sum(1 for c in cambios if c["tipo"] == "SECCION_ELIMINADA")
    secciones_modificadas = sum(1 for c in cambios if c["tipo"] == "MODIFICADO")
    comentarios_resueltos = sum(1 for c in cambios if c.get("posible_comentario_levantado"))
    
    # Crecimiento total de palabras
    total_palabras_v1 = sum(s["word_count"] for s in mapa1.values())
    total_palabras_v2 = sum(s["word_count"] for s in mapa2.values())
    crecimiento = total_palabras_v2 - total_palabras_v1
    crecimiento_porcentaje = f"+{round(crecimiento/total_palabras_v1*100)}%" if total_palabras_v1 else "0%"
    promedio_palabras = total_palabras_v2 // len(mapa2) if mapa2 else 0
    
    # Métricas automáticas (valores mock, ajustables)
    metricas = MetricasAutomaticas(
        cobertura_tesis=round(0.75 + (secciones_nuevas - secciones_eliminadas) * 0.02, 2),
        velocidad_escritura=round(0.6 + crecimiento/1000, 2),
        estabilidad=round(1 - (secciones_modificadas / max(len(mapa2),1)), 2),
        profundidad=round(0.5 + (total_palabras_v2 / 5000), 2)
    )
    
    # Agrupar cambios por capítulo (primer segmento del path)
    cambios_por_capitulo = defaultdict(list)
    for c in cambios:
        capitulo = c["path"].split("/")[0] if "/" in c["path"] else "General"
        cambios_por_capitulo[capitulo].append(CambioSeccion(**c))
    
    return ResultadoComparacion(
        secciones_nuevas=secciones_nuevas,
        secciones_eliminadas=secciones_eliminadas,
        secciones_modificadas=secciones_modificadas,
        comentarios_resueltos=comentarios_resueltos,
        metricas_automaticas=metricas,
        cambios_por_capitulo=dict(cambios_por_capitulo),
        crecimiento_palabras=crecimiento,
        crecimiento_porcentaje=crecimiento_porcentaje,
        promedio_palabras_por_seccion=promedio_palabras
    )


@router.post("/comparar-archivos", response_model=ResultadoComparacion)
async def comparar_archivos(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...)
):
    """
    Endpoint público para comparar dos archivos DOCX directamente.
    Usado por el sistema SGT como plugin externo.
    """
    # Validar extensión
    if not file1.filename.endswith('.docx') or not file2.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .docx")
    
    # Leer contenido de los archivos
    contenido1 = await file1.read()
    contenido2 = await file2.read()
    
    # Procesar archivos
    mapa1 = procesar_bytes(contenido1)
    mapa2 = procesar_bytes(contenido2)
    cambios = comparar_mapa(mapa1, mapa2, file1.filename, file2.filename)
    
    # Estadísticas
    secciones_nuevas = sum(1 for c in cambios if c["tipo"] == "SECCION_NUEVA")
    secciones_eliminadas = sum(1 for c in cambios if c["tipo"] == "SECCION_ELIMINADA")
    secciones_modificadas = sum(1 for c in cambios if c["tipo"] == "MODIFICADO")
    comentarios_resueltos = sum(1 for c in cambios if c.get("posible_comentario_levantado"))
    
    # Crecimiento total de palabras
    total_palabras_v1 = sum(s["word_count"] for s in mapa1.values())
    total_palabras_v2 = sum(s["word_count"] for s in mapa2.values())
    crecimiento = total_palabras_v2 - total_palabras_v1
    crecimiento_porcentaje = f"+{round(crecimiento/total_palabras_v1*100)}%" if total_palabras_v1 else "0%"
    promedio_palabras = total_palabras_v2 // len(mapa2) if mapa2 else 0
    
    # Métricas automáticas
    metricas_res = calcular_metricas_version(mapa2, mapa1)
    
    # Calcular velocidad de escritura
    if mapa1:
        velocidad = round(0.6 + crecimiento / 1000, 4)
    else:
        velocidad = 0.0
    
    metricas = MetricasAutomaticas(
        cobertura_tesis=metricas_res["cobertura_ponderada"],
        velocidad_escritura=velocidad,
        estabilidad=metricas_res["estabilidad"],
        profundidad=metricas_res["profundidad"]
    )
    
    # Agrupar cambios por capítulo
    cambios_por_capitulo = defaultdict(list)
    for c in cambios:
        capitulo = c["path"].split("/")[0] if "/" in c["path"] else "General"
        cambios_por_capitulo[capitulo].append(CambioSeccion(**c))
    
    return ResultadoComparacion(
        secciones_nuevas=secciones_nuevas,
        secciones_eliminadas=secciones_eliminadas,
        secciones_modificadas=secciones_modificadas,
        comentarios_resueltos=comentarios_resueltos,
        metricas_automaticas=metricas,
        cambios_por_capitulo=dict(cambios_por_capitulo),
        crecimiento_palabras=crecimiento,
        crecimiento_porcentaje=crecimiento_porcentaje,
        promedio_palabras_por_seccion=promedio_palabras
    )