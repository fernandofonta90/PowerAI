"""Tareas Celery de ingesta.

``normalizar_carga`` toma una carga ya validada y persistida (estado procesando),
lee el archivo original del storage, lo normaliza a Parquet y publica el dataset,
actualizando el estado a disponible (o fallida con el motivo).
"""

import uuid

from app.domain.enums import EstadoCarga
from app.ingesta.lector import leer_tabla
from app.ingesta.normalizador import a_parquet
from app.services.rutas import ruta_parquet
from app.storage import CONTENEDOR_DATASETS, CONTENEDOR_ORIGINALES, get_almacen
from app.worker import celery_app


@celery_app.task(name="powerai.normalizar_carga")  # type: ignore[untyped-decorator]
def normalizar_carga(carga_id: str) -> None:
    """Normaliza a Parquet la carga ``carga_id`` y actualiza su estado."""
    from app.db import SessionLocal
    from app.models.carga import CargaArchivo

    with SessionLocal() as db:
        carga = db.get(CargaArchivo, uuid.UUID(carga_id))
        if carga is None or carga.estado is not EstadoCarga.PROCESANDO:
            return

        try:
            almacen = get_almacen()
            datos = almacen.leer(CONTENEDOR_ORIGINALES, carga.blob_path_original)
            tabla = leer_tabla(datos, carga.nombre_archivo_original)
            parquet = a_parquet(tabla, carga.plantilla.columnas)

            destino = ruta_parquet(
                carga.torre,
                carga.plantilla.codigo,
                carga.pais,
                carga.periodo,
                carga.version,
            )
            almacen.guardar(CONTENEDOR_DATASETS, destino, parquet)

            carga.blob_path_parquet = destino
            carga.filas = len(tabla.filas)
            carga.estado = EstadoCarga.DISPONIBLE
            carga.mensaje_error = None
        except Exception as exc:  # noqa: BLE001 - se registra el motivo en el estado
            carga.estado = EstadoCarga.FALLIDA
            carga.mensaje_error = str(exc)[:1000]

        db.commit()
