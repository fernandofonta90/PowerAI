"""Servicio de registro de cargas de archivos.

Flujo (decisión vinculante): valida el esquema de forma SÍNCRONA (feedback
inmediato: aceptado o rechazado con mensaje claro), persiste el original
inmutable y versionado en el storage, y encola la normalización a Parquet como
tarea Celery. El estado de la carga es consultable por API.
"""

import hashlib

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import EstadoCarga
from app.ingesta.lector import ArchivoIlegible, leer_tabla
from app.ingesta.validacion import validar
from app.models.carga import CargaArchivo
from app.models.plantilla import PlantillaReporte
from app.services.rutas import ruta_original
from app.storage import CONTENEDOR_ORIGINALES, AlmacenObjetos


class CargaRechazada(Exception):
    """La carga no pasó la validación síncrona. Lleva los motivos."""

    def __init__(self, errores: list[str]) -> None:
        self.errores = errores
        super().__init__("; ".join(errores))


def _siguiente_version(db: Session, plantilla_id: object, pais: str, periodo: str) -> int:
    actual = db.scalar(
        select(func.max(CargaArchivo.version)).where(
            CargaArchivo.plantilla_id == plantilla_id,
            CargaArchivo.pais == pais,
            CargaArchivo.periodo == periodo,
        )
    )
    return (actual or 0) + 1


def registrar_carga(
    db: Session,
    almacen: AlmacenObjetos,
    *,
    plantilla: PlantillaReporte,
    responsable_email: str,
    pais: str,
    periodo: str,
    nombre_archivo: str,
    datos: bytes,
) -> CargaArchivo:
    """Valida, almacena y encola una carga. Lanza :class:`CargaRechazada` si falla."""
    # 1. Lectura del archivo.
    try:
        tabla = leer_tabla(datos, nombre_archivo)
    except ArchivoIlegible as exc:
        raise CargaRechazada([str(exc)]) from exc

    # 2. Validación de esquema y verificación de país/periodo (síncrona).
    errores = validar(
        tabla,
        plantilla.columnas,
        plantilla.columna_pais,
        plantilla.columna_periodo,
        pais,
        periodo,
    )
    if errores:
        raise CargaRechazada(errores)

    # 3. Deduplicación por contenido (hash) dentro de la plantilla.
    hash_sha256 = hashlib.sha256(datos).hexdigest()
    duplicado = db.scalar(
        select(CargaArchivo).where(
            CargaArchivo.plantilla_id == plantilla.id,
            CargaArchivo.hash_sha256 == hash_sha256,
        )
    )
    if duplicado is not None:
        raise CargaRechazada(
            [
                "Archivo duplicado: este contenido ya fue cargado para la "
                f"plantilla '{plantilla.codigo}' (carga {duplicado.id})."
            ]
        )

    # 4. Versionado e inmutabilidad: nueva versión, nunca sobrescribe.
    version = _siguiente_version(db, plantilla.id, pais, periodo)
    destino = ruta_original(
        plantilla.torre, plantilla.codigo, pais, periodo, version, nombre_archivo
    )
    almacen.guardar(CONTENEDOR_ORIGINALES, destino, datos)

    # 5. Registro en el catálogo (estado procesando) y encolado de la tarea.
    carga = CargaArchivo(
        plantilla_id=plantilla.id,
        torre=plantilla.torre,
        pais=pais,
        periodo=periodo,
        responsable_email=responsable_email,
        nombre_archivo_original=nombre_archivo,
        hash_sha256=hash_sha256,
        version=version,
        estado=EstadoCarga.PROCESANDO,
        blob_path_original=destino,
    )
    db.add(carga)
    db.commit()
    db.refresh(carga)

    from app.ingesta.tareas import normalizar_carga

    normalizar_carga.delay(str(carga.id))
    return carga
