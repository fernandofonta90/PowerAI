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
#
# Cartera enriquecida para la demo: 13 clientes MX con facturas repartidas en los
# cuatro tramos de aging (corriente / 1-30 / 31-60 / 60+) y montos realistas en USD.
# GLOBEX es el mayor deudor (20 000); STARK tiene la factura individual más grande
# (15 000) y MASSIVE la mora máxima (120 días). Los decimales son exactos a 2.
_AR_MX = """\
pais,periodo,cliente,factura,fecha_emision,fecha_vencimiento,monto,dias_vencido,moneda
MX,2026-05,GLOBEX,F-101,2026-04-22,2026-05-23,12500.00,8,USD
MX,2026-05,GLOBEX,F-102,2026-03-14,2026-04-14,5000.00,47,USD
MX,2026-05,GLOBEX,F-103,2026-01-25,2026-02-25,2500.00,95,USD
MX,2026-05,ACME,F-104,2026-05-10,2026-06-10,3200.50,0,USD
MX,2026-05,ACME,F-105,2026-04-08,2026-05-09,1800.00,22,USD
MX,2026-05,ACME,F-106,2026-02-17,2026-03-19,950.00,73,USD
MX,2026-05,INITECH,F-107,2026-05-05,2026-06-05,4100.00,0,USD
MX,2026-05,INITECH,F-108,2026-03-27,2026-04-26,2200.75,35,USD
MX,2026-05,UMBRELLA,F-109,2026-01-10,2026-02-10,8800.00,110,USD
MX,2026-05,UMBRELLA,F-110,2026-04-16,2026-05-17,1500.00,14,USD
MX,2026-05,WAYNE,F-111,2026-04-25,2026-05-26,6400.00,5,USD
MX,2026-05,WAYNE,F-112,2026-03-03,2026-04-03,3300.00,58,USD
MX,2026-05,STARK,F-113,2026-05-12,2026-06-12,15000.00,0,USD
MX,2026-05,WONKA,F-114,2026-02-01,2026-03-03,720.00,90,USD
MX,2026-05,WONKA,F-115,2026-04-18,2026-05-19,430.25,12,USD
MX,2026-05,SOYLENT,F-116,2026-03-10,2026-04-10,2750.00,41,USD
MX,2026-05,HOOLI,F-117,2026-04-27,2026-05-28,5600.00,3,USD
MX,2026-05,HOOLI,F-118,2026-02-23,2026-03-26,1200.00,65,USD
MX,2026-05,PIEDPIPER,F-119,2026-05-08,2026-06-08,340.00,0,USD
MX,2026-05,MASSIVE,F-120,2026-01-05,2026-02-05,9100.00,120,USD
MX,2026-05,VEHEMENT,F-121,2026-04-02,2026-05-03,1850.00,28,USD
MX,2026-05,VEHEMENT,F-122,2026-03-08,2026-04-08,2600.00,52,USD
MX,2026-05,GEKKO,F-123,2026-04-24,2026-05-25,7250.00,7,USD
"""

_AR_CO = """\
pais,periodo,cliente,factura,fecha_emision,fecha_vencimiento,monto,dias_vencido,moneda
CO,2026-05,CONACO,F-201,2026-02-28,2026-03-30,4200.00,70,USD
CO,2026-05,CONACO,F-202,2026-04-15,2026-05-16,1600.00,15,USD
CO,2026-05,ANDESCO,F-203,2026-04-06,2026-05-07,2800.00,25,USD
CO,2026-05,BOGOTANA,F-204,2026-05-09,2026-06-09,6500.00,0,USD
CO,2026-05,CARIBE,F-205,2026-02-10,2026-03-12,3100.00,88,USD
"""

# Pagos no aplicados — MX.
_PAGOS_MX = """\
pais,periodo,cliente,referencia_pago,fecha_pago,monto,moneda
MX,2026-05,ACME,PAY-1,2026-05-05,1200.00,USD
MX,2026-05,GLOBEX,PAY-2,2026-05-06,3400.00,USD
MX,2026-05,STARK,PAY-3,2026-05-11,800.00,USD
MX,2026-05,HOOLI,PAY-4,2026-05-18,1500.00,USD
MX,2026-05,WAYNE,PAY-5,2026-05-21,650.50,USD
"""

# Revenue reconciliation — MX.
_REVENUE_MX = """\
pais,periodo,cuenta,descripcion,monto_facturado,monto_reconocido,diferencia
MX,2026-05,4000,Servicios,50000.00,48500.00,1500.00
MX,2026-05,4001,Productos,30000.00,30000.00,0.00
MX,2026-05,4002,Licencias,18000.00,17200.00,800.00
MX,2026-05,4003,Soporte,12000.00,12000.00,0.00
MX,2026-05,4004,Consultoría,22000.00,21500.00,500.00
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
