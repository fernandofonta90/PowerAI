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
from app.services.cargas import CargaRechazada, registrar_carga
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


def _admin(db: Any) -> Any:
    # Admin OTC tiene país '*': ve todos los países (incluido uno declarado como PE).
    return MockAuthProvider().autenticar(db, "admin.otc@powerai.dev")


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


# --- M16: columnas opcionales + fechas que degradan a texto ----------------------------


def test_columnas_opcionales_aceptan_celdas_vacias(
    seed_usuarios: Any, almacen_memoria: Any, reader_local: Any
) -> None:
    db = seed_usuarios
    columnas = [
        ColumnaSpec(nombre="Proveedor", tipo=TipoColumna.TEXTO, requerida=False),
        ColumnaSpec(nombre="Monto", tipo=TipoColumna.DECIMAL, requerida=False),
        ColumnaSpec(nombre="Nota", tipo=TipoColumna.TEXTO, requerida=False),  # 100% vacía
    ]
    res = crear_plantilla_con_vista(
        db,
        Torre.OTC,
        nombre_plantilla="Opcionales",
        frecuencia=Frecuencia.MENSUAL,
        columnas=columnas,
        columna_pais=None,
        columna_periodo=None,
        vista_nombre_negocio="Opcionales",
    )
    # Monto y Nota vacíos en algunas filas; toda la columna Nota vacía.
    datos = b"Proveedor,Monto,Nota\nACME,100.00,\nGLOBEX,,\n"
    carga = registrar_carga(
        db,
        almacen_memoria,
        plantilla=res.plantilla,
        responsable_email="uploader.mx@powerai.dev",
        pais="MX",
        periodo="2026-05",
        nombre_archivo="x.csv",
        datos=datos,
    )
    db.refresh(carga)
    assert carga.estado is EstadoCarga.DISPONIBLE  # vacíos NO rechazan
    r = ejecutar_consulta(
        db, _mx(db), f"SELECT count(*) AS n, count(monto) AS con_monto FROM {res.vista.nombre}"
    )
    assert r.filas == [[2, 1]]  # 2 filas; las celdas vacías entraron como NULL


def test_llave_pais_como_columna_sigue_requerida(
    seed_usuarios: Any, almacen_memoria: Any, reader_local: Any
) -> None:
    db = seed_usuarios
    columnas = [
        ColumnaSpec(nombre="Pais", tipo=TipoColumna.TEXTO, requerida=False),
        ColumnaSpec(nombre="Monto", tipo=TipoColumna.DECIMAL, requerida=False),
    ]
    res = crear_plantilla_con_vista(
        db,
        Torre.OTC,
        nombre_plantilla="Con llave",
        frecuencia=Frecuencia.MENSUAL,
        columnas=columnas,
        columna_pais="Pais",  # elegida como columna → debe quedar requerida
        columna_periodo=None,
        vista_nombre_negocio="Con llave",
    )
    pais_col = next(c for c in res.plantilla.columnas if c.etiqueta == "Pais")
    assert pais_col.requerida is True  # la llave no puede faltar
    # Una fila con país vacío → rechazo (la llave que particiona no puede estar vacía).
    datos = b"Pais,Monto\nMX,100.00\n,50.00\n"
    with pytest.raises(CargaRechazada):
        registrar_carga(
            db,
            almacen_memoria,
            plantilla=res.plantilla,
            responsable_email="uploader.mx@powerai.dev",
            pais="MX",
            periodo="2026-05",
            nombre_archivo="x.csv",
            datos=datos,
        )


def test_fecha_ambigua_degrada_a_texto_con_aviso(
    seed_usuarios: Any, almacen_memoria: Any, reader_local: Any
) -> None:
    db = seed_usuarios
    columnas = [
        ColumnaSpec(nombre="Fecha Pago", tipo=TipoColumna.FECHA, requerida=False),
        ColumnaSpec(nombre="Monto", tipo=TipoColumna.DECIMAL, requerida=False),
    ]
    res = crear_plantilla_con_vista(
        db,
        Torre.OTC,
        nombre_plantilla="Con fecha rara",
        frecuencia=Frecuencia.MENSUAL,
        columnas=columnas,
        columna_pais=None,
        columna_periodo=None,
        vista_nombre_negocio="Con fecha rara",
    )
    # Fechas genuinamente ambiguas (todos los campos ≤ 12): no rechaza, degrada.
    datos = b"Fecha Pago,Monto\n10/06/2025,100.00\n07/08/2025,50.00\n"
    carga = registrar_carga(
        db,
        almacen_memoria,
        plantilla=res.plantilla,
        responsable_email="uploader.mx@powerai.dev",
        pais="MX",
        periodo="2026-05",
        nombre_archivo="x.csv",
        datos=datos,
    )
    db.refresh(carga)
    assert carga.estado is EstadoCarga.DISPONIBLE  # no rechaza
    assert any("no se pudo interpretar como fecha" in a for a in carga.avisos)
    # La columna quedó como TEXTO en la plantilla (el usuario puede editarla luego).
    fp = next(c for c in res.plantilla.columnas if c.etiqueta == "Fecha Pago")
    assert fp.tipo is TipoColumna.TEXTO
    # Y el dato se cargó tal cual (texto), sin corromperse.
    r = ejecutar_consulta(db, _mx(db), f"SELECT count(*) AS n FROM {res.vista.nombre}")
    assert r.filas == [[2]]


def test_archivo_ptp_completo_sin_rechazo(
    seed_usuarios: Any, almacen_memoria: Any, reader_local: Any
) -> None:
    """Reproduce la estructura del reporte PTP real: columnas opcionales (3 vacías),
    fechas mixtas (una DD/MM nítida, una ambigua que degrada), país declarado PE sin
    columna y periodo 2025-11. La carga completa entra sin rechazo."""
    db = seed_usuarios
    columnas = [
        ColumnaSpec(nombre="Supplier Name", tipo=TipoColumna.TEXTO, requerida=False),
        ColumnaSpec(nombre="Invoice Amount", tipo=TipoColumna.DECIMAL, requerida=False),
        ColumnaSpec(nombre="Invoice Date", tipo=TipoColumna.FECHA, requerida=False),
        ColumnaSpec(nombre="Payment Approval Date 1", tipo=TipoColumna.FECHA, requerida=False),
        ColumnaSpec(nombre="Payment Number", tipo=TipoColumna.TEXTO, requerida=False),  # vacía
        ColumnaSpec(nombre="Payment Approver 2", tipo=TipoColumna.TEXTO, requerida=False),  # vacía
        ColumnaSpec(
            nombre="Payment Approval Date 2", tipo=TipoColumna.FECHA, requerida=False
        ),  # vacía
    ]
    res = crear_plantilla_con_vista(
        db,
        Torre.OTC,
        nombre_plantilla="Pagos PTP",
        frecuencia=Frecuencia.MENSUAL,
        columnas=columnas,
        columna_pais=None,  # país declarado, sin columna
        columna_periodo=None,
        vista_nombre_negocio="Pagos PTP",
    )
    # Invoice Date DD/MM nítida (31 desambigua); Payment Approval Date 1 ambigua (degrada);
    # Payment Number / Approver 2 / Approval Date 2 vacías al 100%.
    datos = (
        b"Supplier Name,Invoice Amount,Invoice Date,Payment Approval Date 1,"
        b"Payment Number,Payment Approver 2,Payment Approval Date 2\n"
        b"ACME,100.00,31/12/2025,10/06/2025,,,\n"
        b"GLOBEX,,15/11/2025,07/08/2025,,,\n"
    )
    carga = registrar_carga(
        db,
        almacen_memoria,
        plantilla=res.plantilla,
        responsable_email="uploader.mx@powerai.dev",
        pais="PE",
        periodo="2025-11",
        nombre_archivo="ptp.csv",
        datos=datos,
    )
    db.refresh(carga)
    assert carga.estado is EstadoCarga.DISPONIBLE  # carga COMPLETA, sin rechazo
    assert carga.pais == "PE" and carga.periodo == "2025-11"
    assert carga.filas == 2
    # La fecha ambigua (Payment Approval Date 1) degradó con aviso; Invoice Date no.
    assert any("Payment Approval Date 1" in a for a in carga.avisos)
    # Invoice Date sí se parseó como fecha (DD/MM).
    r = ejecutar_consulta(
        db, _admin(db), f"SELECT invoice_date FROM {res.vista.nombre} ORDER BY invoice_date"
    )
    assert r.filas == [["2025-11-15"], ["2025-12-31"]]


# --- M15: archivo PTP real (país declarado sin columna + fechas mixtas) ----------------


def test_carga_ptp_pais_declarado_y_fechas_mixtas_sin_rechazo(
    seed_usuarios: Any, almacen_memoria: Any, reader_local: Any
) -> None:
    """Reproduce el caso PTP: sin columna de país (declarado al cargar) y fechas en
    formatos mixtos por columna (Invoice Date DD/MM, Payment Date MM/DD)."""
    db = seed_usuarios
    columnas = [
        ColumnaSpec(nombre="Supplier Name", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="Invoice Amount", tipo=TipoColumna.DECIMAL),
        ColumnaSpec(nombre="Invoice Date", tipo=TipoColumna.FECHA),
        ColumnaSpec(nombre="Payment Date", tipo=TipoColumna.FECHA),
    ]
    res = crear_plantilla_con_vista(
        db,
        Torre.OTC,  # da igual la torre para este test del motor de ingesta
        nombre_plantilla="Pagos PTP",
        frecuencia=Frecuencia.MENSUAL,
        columnas=columnas,
        columna_pais=None,  # PTP no trae el código de país literal
        columna_periodo=None,
        vista_nombre_negocio="Pagos PTP",
    )
    # Invoice Date en DD/MM/YYYY (con 31 que desambigua); Payment Date en MM/DD/YYYY.
    datos = (
        b"Supplier Name,Invoice Amount,Invoice Date,Payment Date\n"
        b"ACME,100.00,10/06/2025,10/31/2025\n"
        b"GLOBEX,50.00,31/12/2025,12/15/2025\n"
    )
    carga = registrar_carga(
        db,
        almacen_memoria,
        plantilla=res.plantilla,
        responsable_email="uploader.mx@powerai.dev",
        pais="PE",  # declarado, no verificado contra columna
        periodo="2025-11",
        nombre_archivo="ptp.csv",
        datos=datos,
    )
    db.refresh(carga)
    assert carga.estado is EstadoCarga.DISPONIBLE  # ¡sin rechazo!
    assert carga.pais == "PE"

    # Las fechas se parsearon correcto a ISO por columna (consulta con acceso a PE).
    r = ejecutar_consulta(
        db,
        _admin(db),
        f"SELECT invoice_date, payment_date FROM {res.vista.nombre} ORDER BY invoice_amount DESC",
    )
    assert r.filas == [
        ["2025-06-10", "2025-10-31"],  # 10/06 dmy → 10-jun ; 10/31 mdy → 31-oct
        ["2025-12-31", "2025-12-15"],  # 31/12 dmy → 31-dic ; 12/15 mdy → 15-dic
    ]


# --- M14: encabezados reales (mayúsculas/acentos/espacios) → slug, sin 400 -------------


def test_crear_plantilla_con_encabezados_reales_slugifica_y_consulta(
    seed_usuarios: Any, almacen_memoria: Any, reader_local: Any
) -> None:
    db = seed_usuarios
    # Encabezados crudos de un reporte real (lo que antes daba HTTP 400).
    columnas = [
        ColumnaSpec(nombre="País", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="Número Documento", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="Importe S/", tipo=TipoColumna.DECIMAL),
    ]
    res = crear_plantilla_con_vista(
        db,
        Torre.OTC,
        nombre_plantilla="Cartera Perú",
        frecuencia=Frecuencia.MENSUAL,
        columnas=columnas,
        columna_pais="País",  # el usuario elige el encabezado real
        columna_periodo=None,
        vista_nombre_negocio="Cartera Perú",
        descripciones_columnas={"Importe S/": "Importe pendiente en soles."},
    )
    # Nombres técnicos SQL-seguros; encabezados conservados como etiqueta.
    nombres = {c.nombre for c in res.plantilla.columnas}
    assert nombres == {"pais", "numero_documento", "importe_s"}
    etiquetas = {c.etiqueta for c in res.plantilla.columnas}
    assert etiquetas == {"País", "Número Documento", "Importe S/"}
    # La descripción dada por encabezado quedó en la columna slug correcta.
    cols_vista = {c.nombre: c.descripcion for c in res.vista.columnas}
    assert cols_vista["importe_s"] == "Importe pendiente en soles."

    # Una carga con los ENCABEZADOS REALES queda consultable por el slug.
    datos = "País,Número Documento,Importe S/\nMX,F-1,100.00\nMX,F-2,50.00\n".encode()
    carga = registrar_carga(
        db,
        almacen_memoria,
        plantilla=res.plantilla,
        responsable_email="uploader.mx@powerai.dev",
        pais="MX",
        periodo="2026-05",
        nombre_archivo="cartera.csv",
        datos=datos,
    )
    db.refresh(carga)
    assert carga.estado is EstadoCarga.DISPONIBLE
    resultado = ejecutar_consulta(
        db, _mx(db), f"SELECT sum(importe_s) AS t FROM {res.vista.nombre}"
    )
    assert resultado.filas == [["150.00"]]


# --- M12: plantilla sin columna de periodo (periodo declarado al cargar) ---------------


def test_carga_sin_columna_de_periodo_usa_el_declarado(
    seed_usuarios: Any, almacen_memoria: Any, reader_local: Any
) -> None:
    db = seed_usuarios
    columnas = [
        ColumnaSpec(nombre="pais", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="proveedor", tipo=TipoColumna.TEXTO),
        ColumnaSpec(nombre="monto", tipo=TipoColumna.DECIMAL),
    ]
    res = crear_plantilla_con_vista(
        db,
        Torre.OTC,
        nombre_plantilla="Pagos sin periodo",
        frecuencia=Frecuencia.MENSUAL,
        columnas=columnas,
        columna_pais="pais",
        columna_periodo=None,  # el reporte no trae periodo en columna
        vista_nombre_negocio="Pagos sin periodo",
    )
    assert res.plantilla.columna_periodo is None

    # Archivo sin columna de periodo; el periodo se declara al cargar.
    datos = b"pais,proveedor,monto\nMX,ACME,100.00\nMX,GLOBEX,50.00\n"
    carga = registrar_carga(
        db,
        almacen_memoria,
        plantilla=res.plantilla,
        responsable_email="uploader.mx@powerai.dev",
        pais="MX",
        periodo="2026-05",
        nombre_archivo="pagos.csv",
        datos=datos,
    )
    db.refresh(carga)
    assert carga.estado is EstadoCarga.DISPONIBLE
    assert carga.periodo == "2026-05"  # tomado del declarado

    # Una segunda carga del mismo periodo versiona correctamente (v2).
    carga2 = registrar_carga(
        db,
        almacen_memoria,
        plantilla=res.plantilla,
        responsable_email="uploader.mx@powerai.dev",
        pais="MX",
        periodo="2026-05",
        nombre_archivo="pagos.csv",
        datos=b"pais,proveedor,monto\nMX,ACME,101.00\n",
    )
    db.refresh(carga2)
    assert carga2.version == 2
    assert carga2.periodo == "2026-05"


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
