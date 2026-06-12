"""Siembra de las 3 plantillas del Aging OTC.

Los esquemas son SINTÉTICOS (definidos por nosotros): los reales de OTC llegarán
después y ajustarlos será un update de datos, no un refactor (plantillas = datos,
no código). Idempotente por código de plantilla.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.domain.columnas import ColumnaSpec
from app.domain.enums import Frecuencia, TipoColumna, Torre
from app.models.plantilla import PlantillaReporte

TEXTO = TipoColumna.TEXTO
ENTERO = TipoColumna.ENTERO
DECIMAL = TipoColumna.DECIMAL
FECHA = TipoColumna.FECHA


@dataclass
class DefPlantilla:
    codigo: str
    nombre: str
    descripcion: str
    frecuencia: Frecuencia
    columnas: list[ColumnaSpec]
    columna_pais: str = "pais"
    columna_periodo: str = "periodo"


PLANTILLAS_OTC: list[DefPlantilla] = [
    DefPlantilla(
        codigo="otc_ar_abiertas",
        nombre="OTC · AR abiertas (cuentas por cobrar)",
        descripcion="Facturas abiertas de cuentas por cobrar con antigüedad.",
        frecuencia=Frecuencia.SEMANAL,
        columnas=[
            ColumnaSpec(nombre="pais", tipo=TEXTO, descripcion="País ISO alpha-2."),
            ColumnaSpec(nombre="periodo", tipo=TEXTO, descripcion="Periodo del corte."),
            ColumnaSpec(nombre="cliente", tipo=TEXTO),
            ColumnaSpec(nombre="factura", tipo=TEXTO),
            ColumnaSpec(nombre="fecha_emision", tipo=FECHA),
            ColumnaSpec(nombre="fecha_vencimiento", tipo=FECHA),
            ColumnaSpec(nombre="monto", tipo=DECIMAL),
            ColumnaSpec(nombre="dias_vencido", tipo=ENTERO),
            ColumnaSpec(nombre="moneda", tipo=TEXTO),
        ],
    ),
    DefPlantilla(
        codigo="otc_pagos_unapplied",
        nombre="OTC · Pagos no aplicados (unapplied)",
        descripcion="Pagos recibidos sin aplicar a una factura.",
        frecuencia=Frecuencia.SEMANAL,
        columnas=[
            ColumnaSpec(nombre="pais", tipo=TEXTO),
            ColumnaSpec(nombre="periodo", tipo=TEXTO),
            ColumnaSpec(nombre="cliente", tipo=TEXTO),
            ColumnaSpec(nombre="referencia_pago", tipo=TEXTO),
            ColumnaSpec(nombre="fecha_pago", tipo=FECHA),
            ColumnaSpec(nombre="monto", tipo=DECIMAL),
            ColumnaSpec(nombre="moneda", tipo=TEXTO),
        ],
    ),
    DefPlantilla(
        codigo="otc_revenue_recon",
        nombre="OTC · Revenue reconciliation",
        descripcion="Conciliación de ingreso facturado vs reconocido.",
        frecuencia=Frecuencia.MENSUAL,
        columnas=[
            ColumnaSpec(nombre="pais", tipo=TEXTO),
            ColumnaSpec(nombre="periodo", tipo=TEXTO),
            ColumnaSpec(nombre="cuenta", tipo=TEXTO),
            ColumnaSpec(nombre="descripcion", tipo=TEXTO, requerida=False),
            ColumnaSpec(nombre="monto_facturado", tipo=DECIMAL),
            ColumnaSpec(nombre="monto_reconocido", tipo=DECIMAL),
            ColumnaSpec(nombre="diferencia", tipo=DECIMAL),
        ],
    ),
]


def sembrar_plantillas(db: Session) -> int:
    """Crea o actualiza las plantillas OTC. Devuelve cuántas procesó."""
    for d in PLANTILLAS_OTC:
        plantilla = db.scalar(select(PlantillaReporte).where(PlantillaReporte.codigo == d.codigo))
        columnas_json = [c.model_dump(mode="json") for c in d.columnas]
        if plantilla is None:
            plantilla = PlantillaReporte(codigo=d.codigo, torre=Torre.OTC)
            db.add(plantilla)
        plantilla.nombre = d.nombre
        plantilla.descripcion = d.descripcion
        plantilla.frecuencia = d.frecuencia
        plantilla.columnas_json = columnas_json
        plantilla.columna_pais = d.columna_pais
        plantilla.columna_periodo = d.columna_periodo
    db.commit()
    return len(PLANTILLAS_OTC)


def main() -> None:
    with SessionLocal() as db:
        total = sembrar_plantillas(db)
    print(f"Sembradas {total} plantillas OTC.")


if __name__ == "__main__":
    main()
