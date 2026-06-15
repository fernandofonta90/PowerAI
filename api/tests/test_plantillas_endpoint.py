"""Tests de endpoints M11: descubrimiento, creación/edición gobernada y RBAC."""

from typing import Any

import pytest

pytestmark = pytest.mark.integration

ADMIN = {"X-Mock-User": "admin.otc@powerai.dev"}
UPLOADER = {"X-Mock-User": "uploader.mx@powerai.dev"}
CONSULTA = {"X-Mock-User": "consulta.co@powerai.dev"}
ADMIN_PTP = {"X-Mock-User": "admin.ptp@powerai.dev"}

_CSV_AGING = (
    b"pais,periodo,cliente,factura,fecha_emision,fecha_vencimiento,monto,dias_vencido,moneda\n"
    b"MX,2026-05,ACME,F-1,2026-01-01,2026-02-01,100.00,30,MXN\n"
)

_NUEVA_PLANTILLA = {
    "torre": "OTC",
    "nombre": "Notas de crédito",
    "frecuencia": "mensual",
    "columnas": [
        {"nombre": "pais", "tipo": "texto"},
        {"nombre": "periodo", "tipo": "texto"},
        {"nombre": "nota", "tipo": "texto"},
        {"nombre": "monto", "tipo": "decimal"},
    ],
    "columna_pais": "pais",
    "columna_periodo": "periodo",
    "vista_nombre_negocio": "Notas de crédito emitidas",
    "vista_descripcion": "Notas de crédito por cliente.",
    "descripciones_columnas": {"monto": "Importe de la nota de crédito."},
}


@pytest.fixture(autouse=True)
def _setup(seed_usuarios: Any, seed_vistas: Any) -> None:
    """Usuarios + plantillas/vistas OTC sembradas."""


# --- Inspección -----------------------------------------------------------------------


def test_inspeccionar_detecta_calce(client: Any) -> None:
    resp = client.post(
        "/cargas/inspeccionar",
        data={"torre": "OTC"},
        files={"archivo": ("aging.csv", _CSV_AGING, "text/csv")},
        headers=UPLOADER,
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert "monto" in cuerpo["columnas"]
    assert cuerpo["calce"] is not None
    assert cuerpo["calce"]["codigo"] == "otc_ar_abiertas"


def test_inspeccionar_sugiere_tipos(client: Any) -> None:
    resp = client.post(
        "/cargas/inspeccionar",
        data={"torre": "OTC"},
        files={"archivo": ("aging.csv", _CSV_AGING, "text/csv")},
        headers=UPLOADER,
    )
    assert resp.status_code == 200
    tipos = resp.json()["tipos_sugeridos"]
    # Inferencia sobre la muestra: no todo es 'texto'.
    assert tipos["monto"] == "decimal"
    assert tipos["dias_vencido"] == "entero"
    assert tipos["fecha_emision"] == "fecha"
    assert tipos["cliente"] == "texto"


def test_crear_plantilla_sin_columna_de_periodo(client: Any) -> None:
    payload = {
        "torre": "OTC",
        "nombre": "Sin periodo",
        "frecuencia": "mensual",
        "columnas": [
            {"nombre": "pais", "tipo": "texto"},
            {"nombre": "proveedor", "tipo": "texto"},
            {"nombre": "monto", "tipo": "decimal"},
        ],
        "columna_pais": "pais",
        # columna_periodo omitida a propósito (se declara al cargar)
        "vista_nombre_negocio": "Sin periodo",
    }
    resp = client.post("/plantillas", json=payload, headers=UPLOADER)
    assert resp.status_code == 201, resp.text
    assert resp.json()["plantilla"]["columna_periodo"] is None


def test_inspeccionar_consulta_es_403(client: Any) -> None:
    resp = client.post(
        "/cargas/inspeccionar",
        data={"torre": "OTC"},
        files={"archivo": ("aging.csv", _CSV_AGING, "text/csv")},
        headers=CONSULTA,
    )
    assert resp.status_code == 403


# --- Crear plantilla (gobernado) ------------------------------------------------------


def test_uploader_crea_plantilla_con_vista(client: Any) -> None:
    resp = client.post("/plantillas", json=_NUEVA_PLANTILLA, headers=UPLOADER)
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    assert cuerpo["vista"]["titulo"] == "Notas de crédito emitidas"
    assert cuerpo["plantilla"]["torre"] == "OTC"
    # La vista 1:1 quedó ligada a la plantilla recién creada.
    assert cuerpo["vista"]["plantilla_codigo"] == cuerpo["plantilla"]["codigo"]


def test_crear_plantilla_con_encabezados_reales_no_da_400(client: Any) -> None:
    # Encabezados crudos (mayúsculas/acentos/espacios/símbolos): antes daba 400.
    payload = {
        "torre": "OTC",
        "nombre": "Cartera Perú",
        "frecuencia": "mensual",
        "columnas": [
            {"nombre": "País", "tipo": "texto"},
            {"nombre": "Número Documento", "tipo": "texto"},
            {"nombre": "Monto USD", "tipo": "decimal"},
            {"nombre": "Monto (USD)", "tipo": "decimal"},
        ],
        "columna_pais": "País",
        "vista_nombre_negocio": "Cartera Perú",
    }
    resp = client.post("/plantillas", json=payload, headers=UPLOADER)
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    cols = {c["nombre"] for c in cuerpo["plantilla"]["columnas"]}
    assert cols == {"pais", "numero_documento", "monto_usd", "monto_usd_2"}
    # Colisión 'Monto USD' vs 'Monto (USD)' desambiguada y avisada.
    assert any("monto_usd_2" in a for a in cuerpo["avisos"])


def test_ptp_pais_declarado_sin_columna_fluye_por_rbac(client: Any) -> None:
    # Torre PTP no segmenta por país (admin.ptp tiene países='*'). Crea una plantilla
    # SIN columna de país y carga declarando país=PE: no debe haber fricción de RBAC
    # ni verificación de país contra el contenido.
    plantilla = {
        "torre": "PTP",
        "nombre": "Pagos PTP",
        "frecuencia": "mensual",
        "columnas": [
            {"nombre": "Supplier Name", "tipo": "texto"},
            {"nombre": "Invoice Amount", "tipo": "decimal"},
        ],
        # columna_pais y columna_periodo omitidas (se declaran al cargar)
        "vista_nombre_negocio": "Pagos PTP",
    }
    creada = client.post("/plantillas", json=plantilla, headers=ADMIN_PTP)
    assert creada.status_code == 201, creada.text
    assert creada.json()["plantilla"]["columna_pais"] is None
    codigo = creada.json()["plantilla"]["codigo"]

    archivo = b"Supplier Name,Invoice Amount\nACME,100.00\nGLOBEX,50.00\n"
    resp = client.post(
        "/cargas",
        data={"plantilla_codigo": codigo, "pais": "PE", "periodo": "2025-11"},
        files={"archivo": ("ptp.csv", archivo, "text/csv")},
        headers=ADMIN_PTP,
    )
    assert resp.status_code == 202, resp.text  # aceptada, sin 403 ni 422
    assert resp.json()["pais"] == "PE"


def test_consulta_no_puede_crear_plantilla(client: Any) -> None:
    assert client.post("/plantillas", json=_NUEVA_PLANTILLA, headers=CONSULTA).status_code == 403


def test_crear_plantilla_sin_nombre_de_vista_es_422(client: Any) -> None:
    payload = {**_NUEVA_PLANTILLA, "vista_nombre_negocio": ""}
    # min_length=1 lo rechaza la validación de FastAPI (422).
    assert client.post("/plantillas", json=payload, headers=UPLOADER).status_code == 422


# --- Editar el molde (solo admin) -----------------------------------------------------


def test_editar_molde_requiere_admin(client: Any) -> None:
    edicion = {
        "nombre": "OTC · AR abiertas (v2)",
        "frecuencia": "semanal",
        "columnas": [
            {"nombre": "pais", "tipo": "texto"},
            {"nombre": "periodo", "tipo": "texto"},
            {"nombre": "cliente", "tipo": "texto"},
            {"nombre": "factura", "tipo": "texto"},
            {"nombre": "fecha_emision", "tipo": "fecha"},
            {"nombre": "fecha_vencimiento", "tipo": "fecha"},
            {"nombre": "monto", "tipo": "decimal"},
            {"nombre": "dias_vencido", "tipo": "entero"},
            {"nombre": "moneda", "tipo": "texto"},
            {"nombre": "ejecutivo", "tipo": "texto", "requerida": False},
        ],
        "columna_pais": "pais",
        "columna_periodo": "periodo",
    }
    # Uploader NO puede cambiar el molde.
    assert (
        client.put("/plantillas/otc_ar_abiertas", json=edicion, headers=UPLOADER).status_code == 403
    )
    # Admin sí, y recibe el aviso de impacto.
    resp = client.put("/plantillas/otc_ar_abiertas", json=edicion, headers=ADMIN)
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert "cargas_afectadas" in cuerpo
    assert "ejecutivo" in {c["nombre"] for c in cuerpo["plantilla"]["columnas"]}


def test_impacto_requiere_admin(client: Any) -> None:
    assert client.get("/plantillas/otc_ar_abiertas/impacto", headers=UPLOADER).status_code == 403
    resp = client.get("/plantillas/otc_ar_abiertas/impacto", headers=ADMIN)
    assert resp.status_code == 200
    assert "cargas_afectadas" in resp.json()


# --- Editar vista ---------------------------------------------------------------------


def test_editar_vista_solo_admin(client: Any) -> None:
    # Editar la vista (nombre/descripciones que lee el experto) es SOLO admin,
    # igual que el molde. Ni consulta ni uploader pueden.
    body = {
        "titulo": "Cartera abierta (renombrada)",
        "descripcion": "Saldos por cobrar abiertos.",
        "descripciones_columnas": {"monto": "Saldo pendiente de cobro por factura."},
    }
    assert client.put("/vistas/ar_abiertas", json=body, headers=CONSULTA).status_code == 403
    assert client.put("/vistas/ar_abiertas", json=body, headers=UPLOADER).status_code == 403
    resp = client.put("/vistas/ar_abiertas", json=body, headers=ADMIN)
    assert resp.status_code == 200
    assert resp.json()["titulo"] == "Cartera abierta (renombrada)"


# --- Cadena con el experto (M10): la nueva vista aparece como fuente -------------------


def test_nueva_vista_fluye_al_checklist_de_fuentes_del_experto(client: Any) -> None:
    creada = client.post("/plantillas", json=_NUEVA_PLANTILLA, headers=UPLOADER)
    assert creada.status_code == 201
    vista_nombre = creada.json()["vista"]["nombre"]
    # El admin la ve disponible como fuente en la pantalla del experto (M10).
    exp = client.get("/torres/OTC/experto", headers=ADMIN)
    assert exp.status_code == 200
    assert vista_nombre in {v["nombre"] for v in exp.json()["vistas_torre"]}


def test_inspeccionar_requiere_auth(client: Any) -> None:
    resp = client.post(
        "/cargas/inspeccionar",
        data={"torre": "OTC"},
        files={"archivo": ("aging.csv", _CSV_AGING, "text/csv")},
    )
    assert resp.status_code == 401
