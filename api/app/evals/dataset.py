"""Dataset sintético de referencia para el banco de preguntas doradas.

Los datos son fijos y se diseñan de modo que la "respuesta correcta verificada"
de cada pregunta quede garantizada POR CONSTRUCCIÓN (no por un cálculo posterior).
Incluye datos de CO que un usuario solo-MX nunca debe ver (prueba de RLS dentro
del propio banco).

Construir requiere las plantillas y vistas ya sembradas.
"""

import hashlib

from sqlalchemy.orm import Session

from app.domain.enums import EstadoCarga
from app.ingesta.lector import leer_tabla
from app.ingesta.normalizador import a_parquet
from app.models.carga import CargaArchivo
from app.models.plantilla import PlantillaReporte
from app.services.rutas import ruta_parquet
from app.storage import CONTENEDOR_DATASETS, AlmacenObjetos

PERIODO = "2026-05"

# Cartera AR abierta — MX (visible para el usuario MX) y CO (invisible: RLS).
_AR_MX = """\
pais,periodo,cliente,factura,fecha_emision,fecha_vencimiento,monto,dias_vencido,moneda
MX,2026-05,ACME,F-1,2026-04-01,2026-05-01,1000.00,10,USD
MX,2026-05,ACME,F-2,2026-03-01,2026-04-01,500.00,40,USD
MX,2026-05,ACME,F-3,2026-02-01,2026-03-01,250.00,80,USD
MX,2026-05,GLOBEX,F-4,2026-04-10,2026-05-10,2000.00,5,USD
MX,2026-05,GLOBEX,F-5,2026-01-15,2026-02-15,1500.00,95,USD
MX,2026-05,INITECH,F-6,2026-05-01,2026-06-01,300.00,0,USD
"""

_AR_CO = """\
pais,periodo,cliente,factura,fecha_emision,fecha_vencimiento,monto,dias_vencido,moneda
CO,2026-05,CONACO,F-8,2026-03-01,2026-04-01,1200.00,70,USD
CO,2026-05,CONACO,F-9,2026-04-15,2026-05-15,400.00,15,USD
CO,2026-05,ANDESCO,F-7,2026-04-05,2026-05-05,800.00,20,USD
"""

# Pagos no aplicados — MX.
_PAGOS_MX = """\
pais,periodo,cliente,referencia_pago,fecha_pago,monto,moneda
MX,2026-05,ACME,PAY-1,2026-05-05,300.00,USD
MX,2026-05,GLOBEX,PAY-2,2026-05-06,700.00,USD
"""

# Revenue reconciliation — MX.
_REVENUE_MX = """\
pais,periodo,cuenta,descripcion,monto_facturado,monto_reconocido,diferencia
MX,2026-05,4000,Servicios,10000.00,9500.00,500.00
MX,2026-05,4001,Productos,5000.00,5000.00,0.00
"""

# (codigo_plantilla, pais, csv)
_CARGAS: list[tuple[str, str, str]] = [
    ("otc_ar_abiertas", "MX", _AR_MX),
    ("otc_ar_abiertas", "CO", _AR_CO),
    ("otc_pagos_unapplied", "MX", _PAGOS_MX),
    ("otc_revenue_recon", "MX", _REVENUE_MX),
]


def _crear_carga(
    db: Session, almacen: AlmacenObjetos, codigo: str, pais: str, contenido: str
) -> None:
    plantilla = db.query(PlantillaReporte).filter_by(codigo=codigo).one()
    datos = contenido.encode()
    parquet = a_parquet(leer_tabla(datos, "ref.csv"), plantilla.columnas)
    n_filas = len(leer_tabla(datos, "ref.csv").filas)
    ruta = ruta_parquet(plantilla.torre, codigo, pais, PERIODO, 1)
    almacen.guardar(CONTENEDOR_DATASETS, ruta, parquet)
    db.add(
        CargaArchivo(
            plantilla_id=plantilla.id,
            torre=plantilla.torre,
            pais=pais,
            periodo=PERIODO,
            responsable_email="evals@powerai.dev",
            nombre_archivo_original=f"{codigo}_{pais}.csv",
            hash_sha256=hashlib.sha256(f"{codigo}{pais}".encode() + parquet).hexdigest(),
            version=1,
            estado=EstadoCarga.DISPONIBLE,
            blob_path_original=f"orig/{ruta}",
            blob_path_parquet=ruta,
            filas=n_filas,
        )
    )


def construir_dataset(db: Session, almacen: AlmacenObjetos) -> None:
    """Crea las cargas DISPONIBLES del dataset de referencia (plantillas/vistas ya sembradas)."""
    for codigo, pais, contenido in _CARGAS:
        _crear_carga(db, almacen, codigo, pais, contenido)
    db.commit()
