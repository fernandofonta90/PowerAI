"""Siembra la torre PTP de forma persistente: plantilla + vista 1:1 + carga real.

Reproduce lo que se configuró por UI para PTP, con los arreglos de M14/M15/M16, de
modo que sobreviva a un reset de la BD (a diferencia de lo creado a mano por UI):

- PLANTILLA "Pagos a proveedores PTP" desde los 29 encabezados reales del reporte
  de AP, auto-slugificados (M14: "Número Documento" → numero_documento, etc.).
  País y periodo NO son columnas del archivo: se DECLARAN al cargar (PE / 2025-11).
  Todas las columnas son OPCIONALES (M16): las 3 columnas 100% vacías (Payment
  Number, Payment Approver 2, Payment Approval Date 2) entran como nulas sin rechazo.
- TIPOS: Invoice Amount y Paid Amount = decimal; las columnas de fecha = fecha (la
  heurística de formato mixto DD/MM vs MM/DD del M15 resuelve MM/DD aquí). La
  columna 'Payment Approval Date 1' trae datetime con hora: es irresoluble como
  fecha y DEGRADA a texto con aviso (M16), sin rechazar la carga.
- VISTA 1:1 "Pagos a proveedores PTP" con descripciones de negocio en las columnas
  clave (las que guían al experto).
- CARGA de las ~932 filas reales (país=PE, periodo=2025-11).

DATOS REALES DEL SSC: el CSV NUNCA se versiona (el .gitignore excluye *.csv). El
seed lee el archivo desde la variable ``POWERAI_PTP_SEED_FILE`` o, por defecto,
``api/seed_data/ptp_payment_PE_2025-11.csv`` (no commiteado). Si el archivo no
está, la plantilla/vista se crean igual y la CARGA se omite con un aviso claro
(Fernando puede cargar su archivo por la UI cuando lo tenga). Es idempotente.

    uv run python -m app.scripts.seed_ptp
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.columnas import ColumnaSpec
from app.domain.enums import EstadoCarga, Frecuencia, TipoColumna, Torre
from app.ingesta.lector import leer_tabla
from app.ingesta.normalizador import a_parquet
from app.models.carga import CargaArchivo
from app.models.plantilla import PlantillaReporte
from app.services.plantillas import (
    crear_plantilla_con_vista,
    degradar_fechas_ambiguas,
    vista_de_plantilla,
)
from app.services.rutas import ruta_parquet
from app.storage import CONTENEDOR_DATASETS, AlmacenObjetos, get_almacen

TEXTO, ENTERO, DECIMAL, FECHA = (
    TipoColumna.TEXTO,
    TipoColumna.ENTERO,
    TipoColumna.DECIMAL,
    TipoColumna.FECHA,
)

NOMBRE_PLANTILLA = "Pagos a proveedores PTP"
VISTA_NOMBRE = "Pagos a proveedores PTP"
VISTA_DESCRIPCION = (
    "Pagos ejecutados a proveedores (cuentas por pagar) de Manpower Perú: una fila "
    "por pago de factura, con proveedor, montos de factura y pagado, fechas y moneda."
)
# Código determinista de la plantilla (torre + slug del nombre de la vista). Sirve
# para la idempotencia: si ya existe, no se vuelve a crear.
CODIGO = "ptp_pagos_a_proveedores_ptp"
PAIS = "PE"
PERIODO = "2025-11"

# Definición de la plantilla = ESQUEMA (no datos): 29 encabezados EXACTOS del
# archivo, en orden, con su tipo. Los tipos replican lo que sugiere la inferencia
# (M14) más la intención explícita: montos decimal y columnas de fecha = fecha.
# Los encabezados deben coincidir con los que devuelve el lector (que recorta
# espacios); _crear_carga valida la coincidencia exacta y aborta si hay diferencia.
_COLUMNAS: list[tuple[str, TipoColumna]] = [
    ("Business Unit", TEXTO),
    ("Legal Entity", TEXTO),
    ("Supplier Name", TEXTO),
    ("Supplier Number", ENTERO),
    ("Supplier Site", TEXTO),
    ("Supplier Site Status (Active / Inactive)", TEXTO),
    ("Pay Group", TEXTO),
    ("Payment Method - Set Up", TEXTO),
    ("Supplier Terms", TEXTO),
    ("Invoice Number", TEXTO),
    ("Invoice Currency", TEXTO),
    ("Invoice Amount", DECIMAL),
    ("Invoice Date", FECHA),
    ("Invoice Creation Date", FECHA),
    ("Invoice Due Date", FECHA),
    ("Invoice Terms", TEXTO),
    ("Paid Amount", DECIMAL),
    ("Payment Number", TEXTO),
    ("End to End ID", ENTERO),
    ("Payment File Ref Num", ENTERO),
    ("Payment Method - Used", TEXTO),
    ("Payment Date", FECHA),
    ("Payment Process Request", TEXTO),
    ("Payment Creator", TEXTO),
    ("Payment Creation Date", FECHA),
    ("Payment Approver 1", TEXTO),
    ("Payment Approval Date 1", FECHA),
    ("Payment Approver 2", TEXTO),
    ("Payment Approval Date 2", FECHA),
]

# Descripciones de negocio de las columnas clave (indexadas por nombre técnico/slug).
# Guían al experto; el resto recibe una descripción genérica automática.
_DESCRIPCIONES: dict[str, str] = {
    "paid_amount": (
        "Monto efectivamente pagado al proveedor, en la moneda de invoice_currency. "
        "Úsala para sumar pagos."
    ),
    "payment_date": ("Fecha en que se ejecutó el pago. Úsala para filtrar por rango de fechas."),
    "invoice_creation_date": (
        "Fecha de creación de la factura. Úsala para medir días entre creación y pago."
    ),
    "supplier_name": "Nombre del proveedor al que se le paga.",
    "business_unit": "Unidad de negocio (PE001/PE002/PE003 = Manpower Perú).",
    "invoice_currency": "Moneda del pago (PEN, USD).",
}


def _ruta_archivo() -> Path:
    """Ruta del CSV real (datos del SSC, no versionado). Configurable por entorno."""
    env = os.environ.get("POWERAI_PTP_SEED_FILE")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "seed_data" / "ptp_payment_PE_2025-11.csv"


def _crear_plantilla(db: Session) -> PlantillaReporte:
    """Crea la plantilla PTP + su vista 1:1 (idempotente por código determinista)."""
    existente = db.scalar(select(PlantillaReporte).where(PlantillaReporte.codigo == CODIGO))
    if existente is not None:
        return existente

    # País y periodo se declaran al cargar (columna_pais/periodo = None) => ninguna
    # columna es llave => todas quedan OPCIONALES (M16). Se pasan con requerida=False.
    columnas = [
        ColumnaSpec(nombre=encabezado, tipo=tipo, requerida=False, etiqueta=encabezado)
        for encabezado, tipo in _COLUMNAS
    ]
    res = crear_plantilla_con_vista(
        db,
        Torre.PTP,
        nombre_plantilla=NOMBRE_PLANTILLA,
        frecuencia=Frecuencia.MENSUAL,
        columnas=columnas,
        columna_pais=None,
        columna_periodo=None,
        vista_nombre_negocio=VISTA_NOMBRE,
        vista_descripcion=VISTA_DESCRIPCION,
        descripciones_columnas=_DESCRIPCIONES,
    )
    if res.plantilla.codigo != CODIGO:  # pragma: no cover - salvaguarda del slug determinista
        raise RuntimeError(
            f"El código generado ({res.plantilla.codigo}) no coincide con el esperado ({CODIGO})."
        )
    for aviso in res.avisos:
        print(f"  aviso (slug): {aviso}")
    return res.plantilla


def _crear_carga(db: Session, almacen: AlmacenObjetos, plantilla: PlantillaReporte) -> bool:
    """Carga las filas reales (PE/2025-11) de forma síncrona. Devuelve si cargó."""
    ya = db.scalar(
        select(CargaArchivo).where(
            CargaArchivo.plantilla_id == plantilla.id,
            CargaArchivo.pais == PAIS,
            CargaArchivo.periodo == PERIODO,
        )
    )
    if ya is not None:
        print(f"  carga PTP {PAIS}/{PERIODO} ya existe (filas={ya.filas}); no se duplica.")
        return False

    archivo = _ruta_archivo()
    if not archivo.exists():
        print(
            f"  ⚠ No se encontró el archivo de datos en {archivo}. La plantilla y la vista "
            "quedaron creadas, pero SIN carga. Coloca el CSV ahí (o define "
            "POWERAI_PTP_SEED_FILE) y vuelve a correr el seed, o cárgalo por la UI."
        )
        return False

    datos = archivo.read_bytes()
    tabla = leer_tabla(datos, archivo.name)

    # Salvaguarda: los encabezados definidos deben existir EXACTAMENTE en el archivo
    # (atrapa typos y el espacio final de 'Invoice Currency ').
    definidos = {c.etiqueta for c in plantilla.columnas}
    del_archivo = set(tabla.columnas)
    faltan = definidos - del_archivo
    if faltan:
        raise RuntimeError(
            f"Encabezados definidos que NO están en el archivo: {sorted(faltan)}. "
            f"Encabezados del archivo: {sorted(del_archivo)}"
        )

    # M16: degrada a texto las columnas 'fecha' irresolubles (Payment Approval Date 1).
    avisos = degradar_fechas_ambiguas(db, plantilla, tabla)
    for aviso in avisos:
        print(f"  aviso (fecha→texto, M16): {aviso}")

    parquet = a_parquet(tabla, plantilla.columnas)
    n_filas = len(tabla.filas)
    ruta = ruta_parquet(Torre.PTP, plantilla.codigo, PAIS, PERIODO, 1)
    # Robusto a re-seed tras reset de BD: el blob en storage puede persistir aunque
    # la fila de carga se haya borrado. guardar() es inmutable (overwrite=False), así
    # que solo se sube si no existe; si existe, se reutiliza apuntando la nueva carga.
    if not almacen.existe(CONTENEDOR_DATASETS, ruta):
        almacen.guardar(CONTENEDOR_DATASETS, ruta, parquet)

    db.add(
        CargaArchivo(
            plantilla_id=plantilla.id,
            torre=Torre.PTP,
            pais=PAIS,
            periodo=PERIODO,
            responsable_email="seed-ptp@powerai.dev",
            nombre_archivo_original=archivo.name,
            hash_sha256=hashlib.sha256(datos).hexdigest(),
            version=1,
            estado=EstadoCarga.DISPONIBLE,
            blob_path_original=f"orig/{ruta}",
            blob_path_parquet=ruta,
            filas=n_filas,
        )
    )
    db.commit()
    print(f"  carga PTP {PAIS}/{PERIODO}: {n_filas} filas.")
    return True


def sembrar_ptp(db: Session, almacen: AlmacenObjetos) -> int:
    """Siembra plantilla + vista + carga de PTP. Devuelve cuántas plantillas (1)."""
    plantilla = _crear_plantilla(db)
    vista = vista_de_plantilla(db, plantilla)
    _crear_carga(db, almacen, plantilla)
    nombre_vista = vista.nombre if vista is not None else "?"
    print(f"  plantilla '{plantilla.codigo}' + vista '{nombre_vista}' listas.")
    return 1


def main() -> None:
    from app.db import SessionLocal

    with SessionLocal() as db:
        sembrar_ptp(db, get_almacen())
    print("Sembrada la torre PTP (plantilla 'Pagos a proveedores PTP' + vista + carga PE/2025-11).")


if __name__ == "__main__":
    main()
