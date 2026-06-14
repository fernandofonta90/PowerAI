"""Tests de integración: descubrimiento de plantillas y barandales (M11).

Cubren la cadena plantilla→archivo→vista→consulta de extremo a extremo y los dos
barandales: el mapeo acomoda la carga sin mutar el molde; crear/editar son actos
gobernados.
"""

import copy
from typing import Any

import pytest
from app.auth.provider import MockAuthProvider
from app.domain.columnas import ColumnaSpec
from app.domain.enums import EstadoCarga, Frecuencia, TipoColumna, Torre
from app.models.plantilla import PlantillaReporte
from app.motor.motor import ejecutar_consulta
from app.scripts.muestras import generar_csv
from app.services.cargas import registrar_carga
from app.services.plantillas import (
    crear_plantilla_con_vista,
    editar_plantilla,
    emparejar,
    vista_de_plantilla,
)
from sqlalchemy import select

pytestmark = pytest.mark.integration


def _plantilla(db: Any, codigo: str) -> PlantillaReporte:
    return db.scalars(select(PlantillaReporte).where(PlantillaReporte.codigo == codigo)).one()


def _mx(db: Any) -> Any:
    return MockAuthProvider().autenticar(db, "uploader.mx@powerai.dev")


# --- Emparejamiento -------------------------------------------------------------------


def test_emparejar_calce_y_no_calce(seed_vistas: Any) -> None:
    db = seed_vistas
    headers_ok = [
        "pais",
        "periodo",
        "cliente",
        "factura",
        "fecha_emision",
        "fecha_vencimiento",
        "monto",
        "dias_vencido",
        "moneda",
    ]
    cands = emparejar(db, Torre.OTC, headers_ok)
    calce = next(c for c in cands if c.plantilla.codigo == "otc_ar_abiertas")
    assert calce.calza and not calce.faltantes

    # Sin 'monto' (requerida): ya no calza y lo reporta como faltante.
    headers_falta = [h for h in headers_ok if h != "monto"]
    cands2 = emparejar(db, Torre.OTC, headers_falta)
    ar = next(c for c in cands2 if c.plantilla.codigo == "otc_ar_abiertas")
    assert not ar.calza
    assert "monto" in ar.faltantes


# --- Primera carga: nace plantilla + vista 1:1 y queda consultable ---------------------


def test_crear_plantilla_con_vista_cierra_la_cadena(
    seed_usuarios: Any, almacen_memoria: Any, reader_local: Any
) -> None:
    db = seed_usuarios
    columnas = [
        ColumnaSpec(nombre="pais", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="periodo", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="proveedor", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="monto", tipo=TipoColumna.DECIMAL),
    ]
    res = crear_plantilla_con_vista(
        db,
        Torre.OTC,
        nombre_plantilla="Pagos a proveedores",
        frecuencia=Frecuencia.MENSUAL,
        columnas=columnas,
        columna_pais="pais",
        columna_periodo="periodo",
        vista_nombre_negocio="Pagos a proveedores",
        vista_descripcion="Pagos emitidos por proveedor.",
        descripciones_columnas={"monto": "Importe pagado al proveedor."},
    )
    # Vista 1:1 generada con nombre de negocio = título y SQL sobre la plantilla.
    assert res.vista.titulo == "Pagos a proveedores"
    assert res.vista.sql == f"SELECT pais, periodo, proveedor, monto FROM {res.plantilla.codigo}"
    assert res.vista.torre == Torre.OTC
    cols = {c.nombre: c.descripcion for c in res.vista.columnas}
    assert cols["monto"] == "Importe pagado al proveedor."
    assert cols["proveedor"]  # genérica, no vacía

    # Una carga contra la nueva plantilla queda consultable por la nueva vista.
    csv = generar_csv(columnas, "pais", "periodo", "MX", "2026-05", filas=3)
    carga = registrar_carga(
        db,
        almacen_memoria,
        plantilla=res.plantilla,
        responsable_email="uploader.mx@powerai.dev",
        pais="MX",
        periodo="2026-05",
        nombre_archivo="pagos.csv",
        datos=csv,
    )
    db.refresh(carga)  # la normalización (eager) corrió en otra sesión
    assert carga.estado is EstadoCarga.DISPONIBLE
    resultado = ejecutar_consulta(db, _mx(db), f"SELECT count(*) AS n FROM {res.vista.nombre}")
    assert resultado.filas == [[3]]


# --- Barandal 2: el mapeo acomoda la carga, NO redefine la plantilla -------------------


def test_mapeo_no_muta_la_plantilla(
    seed_usuarios: Any, seed_vistas: Any, almacen_memoria: Any, reader_local: Any
) -> None:
    db = seed_vistas
    plantilla = _plantilla(db, "otc_ar_abiertas")
    esquema_antes = copy.deepcopy(plantilla.columnas_json)

    # Archivo con 'importe' en vez de 'monto'; se mapea a la columna esperada.
    cabeceras = (
        "pais,periodo,cliente,factura,fecha_emision,fecha_vencimiento,importe,dias_vencido,moneda"
    )
    fila = "MX,2026-05,ACME,F-1,2026-01-01,2026-02-01,100.00,30,MXN"
    datos = f"{cabeceras}\n{fila}\n".encode()

    carga = registrar_carga(
        db,
        almacen_memoria,
        plantilla=plantilla,
        responsable_email="uploader.mx@powerai.dev",
        pais="MX",
        periodo="2026-05",
        nombre_archivo="aging.csv",
        datos=datos,
        mapeo={"monto": "importe"},
    )
    db.refresh(carga)
    assert carga.estado is EstadoCarga.DISPONIBLE
    assert carga.mapeo_json == {"monto": "importe"}

    # El molde NO cambió por haber mapeado una carga.
    db.refresh(plantilla)
    assert plantilla.columnas_json == esquema_antes

    # Y el dato quedó bajo el nombre esperado 'monto'.
    resultado = ejecutar_consulta(db, _mx(db), "SELECT sum(monto) AS t FROM ar_abiertas")
    assert resultado.filas == [["100.00"]]


# --- Barandal 1 (parte): editar el molde SÍ lo cambia (acto explícito) -----------------


def test_editar_plantilla_cambia_molde_y_sincroniza_vista(seed_vistas: Any) -> None:
    db = seed_vistas
    plantilla = _plantilla(db, "otc_pagos_unapplied")
    nuevas = [
        ColumnaSpec(nombre="pais", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="periodo", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="cliente", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="referencia_pago", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="fecha_pago", tipo=TipoColumna.FECHA),
        ColumnaSpec(nombre="monto", tipo=TipoColumna.DECIMAL),
        ColumnaSpec(nombre="moneda", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="banco", tipo=TipoColumna.TEXTO, requerida=False),
    ]
    editar_plantilla(
        db,
        plantilla,
        nombre_plantilla="OTC · Pagos no aplicados (v2)",
        frecuencia=Frecuencia.SEMANAL,
        columnas=nuevas,
        columna_pais="pais",
        columna_periodo="periodo",
    )
    db.refresh(plantilla)
    assert "banco" in {c.nombre for c in plantilla.columnas}
    # La vista 1:1 se re-sincroniza para incluir la nueva columna.
    vista = vista_de_plantilla(db, plantilla)
    assert vista is not None and "banco" in vista.sql
