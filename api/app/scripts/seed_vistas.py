"""Siembra de las vistas curadas del catálogo semántico para OTC.

Las vistas son DATOS: nombre de negocio, descripción (redactada para el LLM de
M4), SQL sobre la "fuente" de su plantilla (referenciada por el codigo de la
plantilla) y descripción por columna. Idempotente por nombre de vista.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.domain.columnas import ColumnaDescrita
from app.domain.enums import Torre
from app.models.plantilla import PlantillaReporte
from app.models.vista import VistaCatalogo


@dataclass
class DefVista:
    nombre: str
    titulo: str
    descripcion: str
    plantilla_codigo: str
    sql: str
    columnas: list[ColumnaDescrita] = field(default_factory=list)


def _col(nombre: str, descripcion: str) -> ColumnaDescrita:
    return ColumnaDescrita(nombre=nombre, descripcion=descripcion)


VISTAS_OTC: list[DefVista] = [
    DefVista(
        nombre="ar_abiertas",
        titulo="Cartera de cuentas por cobrar abiertas",
        descripcion=(
            "Facturas de clientes pendientes de cobro (cuentas por cobrar abiertas) "
            "con su antigüedad. Úsala para cartera vencida, aging, días de mora y "
            "saldos por cliente."
        ),
        plantilla_codigo="otc_ar_abiertas",
        sql=(
            "SELECT pais, periodo, cliente, factura, fecha_emision, "
            "fecha_vencimiento, monto, dias_vencido, moneda FROM otc_ar_abiertas"
        ),
        columnas=[
            _col("pais", "País ISO alpha-2 del saldo."),
            _col("periodo", "Periodo del corte de cartera."),
            _col("cliente", "Nombre del cliente deudor."),
            _col("factura", "Número de factura abierta."),
            _col("fecha_emision", "Fecha de emisión de la factura."),
            _col("fecha_vencimiento", "Fecha de vencimiento de la factura."),
            _col("monto", "Saldo abierto de la factura (DECIMAL al centavo)."),
            _col("dias_vencido", "Días transcurridos desde el vencimiento."),
            _col("moneda", "Moneda del saldo."),
        ],
    ),
    DefVista(
        nombre="pagos_unapplied",
        titulo="Pagos no aplicados",
        descripcion=(
            "Pagos recibidos de clientes que aún no se han aplicado a una factura. "
            "Úsala para identificar efectivo sin conciliar por cliente y periodo."
        ),
        plantilla_codigo="otc_pagos_unapplied",
        sql=(
            "SELECT pais, periodo, cliente, referencia_pago, fecha_pago, monto, "
            "moneda FROM otc_pagos_unapplied"
        ),
        columnas=[
            _col("pais", "País ISO alpha-2 del pago."),
            _col("periodo", "Periodo del corte."),
            _col("cliente", "Cliente que realizó el pago."),
            _col("referencia_pago", "Referencia del pago recibido."),
            _col("fecha_pago", "Fecha en que se recibió el pago."),
            _col("monto", "Importe del pago no aplicado (DECIMAL al centavo)."),
            _col("moneda", "Moneda del pago."),
        ],
    ),
    DefVista(
        nombre="revenue_recon",
        titulo="Conciliación de ingreso (revenue reconciliation)",
        descripcion=(
            "Comparación entre el ingreso facturado y el reconocido por cuenta. "
            "Úsala para detectar diferencias de reconocimiento de ingreso."
        ),
        plantilla_codigo="otc_revenue_recon",
        sql=(
            "SELECT pais, periodo, cuenta, descripcion, monto_facturado, "
            "monto_reconocido, diferencia FROM otc_revenue_recon"
        ),
        columnas=[
            _col("pais", "País ISO alpha-2."),
            _col("periodo", "Periodo contable."),
            _col("cuenta", "Cuenta contable."),
            _col("descripcion", "Descripción de la cuenta."),
            _col("monto_facturado", "Ingreso facturado (DECIMAL al centavo)."),
            _col("monto_reconocido", "Ingreso reconocido (DECIMAL al centavo)."),
            _col("diferencia", "Diferencia facturado − reconocido."),
        ],
    ),
]


def sembrar_vistas(db: Session) -> int:
    """Crea o actualiza las vistas OTC. Devuelve cuántas procesó."""
    for d in VISTAS_OTC:
        plantilla = db.scalar(
            select(PlantillaReporte).where(PlantillaReporte.codigo == d.plantilla_codigo)
        )
        if plantilla is None:
            raise RuntimeError(
                f"Plantilla '{d.plantilla_codigo}' no existe; siembra plantillas primero."
            )
        vista = db.scalar(select(VistaCatalogo).where(VistaCatalogo.nombre == d.nombre))
        if vista is None:
            vista = VistaCatalogo(nombre=d.nombre)
            db.add(vista)
        vista.titulo = d.titulo
        vista.descripcion = d.descripcion
        vista.torre = Torre.OTC
        vista.plantilla_id = plantilla.id
        vista.sql = d.sql
        vista.columnas_json = [c.model_dump(mode="json") for c in d.columnas]
    db.commit()
    return len(VISTAS_OTC)


def main() -> None:
    with SessionLocal() as db:
        total = sembrar_vistas(db)
    print(f"Sembradas {total} vistas del catálogo OTC.")


if __name__ == "__main__":
    main()
