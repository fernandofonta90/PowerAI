"""Tests de integración del flujo de carga, catálogo y frescura (con Postgres).

Celery corre en modo eager y el storage es en memoria (fixtures de conftest).
Cubre happy paths y rechazos: esquema inválido, país declarado ≠ contenido,
columnas faltantes, duplicado por hash, formato no soportado, y RBAC.
"""

from typing import Any

import pytest
from app.domain.enums import Torre
from app.scripts.muestras import generar_csv
from app.scripts.seed_plantillas import PLANTILLAS_OTC
from app.services.rutas import ruta_parquet
from app.storage import CONTENEDOR_DATASETS

pytestmark = pytest.mark.integration

AR = PLANTILLAS_OTC[0]  # otc_ar_abiertas

ADMIN = "admin.otc@powerai.dev"  # OTC, todos los países (admin)
UPLOADER_MX = "uploader.mx@powerai.dev"  # OTC/MX (uploader)
CONSULTA_CO = "consulta.co@powerai.dev"  # OTC/CO (consulta)


def _csv(pais: str = "MX", periodo: str = "2026-05", filas: int = 4) -> bytes:
    return generar_csv(AR.columnas, AR.columna_pais, AR.columna_periodo, pais, periodo, filas)


def _subir(
    client: Any,
    usuario: str,
    *,
    plantilla: str = "otc_ar_abiertas",
    pais: str = "MX",
    periodo: str = "2026-05",
    contenido: bytes | None = None,
    nombre: str = "aging.csv",
) -> Any:
    if contenido is None:
        contenido = _csv(pais=pais, periodo=periodo)
    return client.post(
        "/cargas",
        data={"plantilla_codigo": plantilla, "pais": pais, "periodo": periodo},
        files={"archivo": (nombre, contenido, "text/csv")},
        headers={"X-Mock-User": usuario},
    )


@pytest.fixture(autouse=True)
def _datos(seed_usuarios: Any, seed_plantillas: Any) -> None:
    """Siembra usuarios y plantillas para todos los tests del módulo."""


# --- happy path -------------------------------------------------------------


def test_carga_exitosa_se_normaliza_a_parquet(client: Any, almacen_memoria: Any) -> None:
    resp = _subir(client, UPLOADER_MX)
    assert resp.status_code == 202
    cuerpo = resp.json()
    assert cuerpo["estado"] == "procesando"
    assert cuerpo["version"] == 1
    assert cuerpo["plantilla_codigo"] == "otc_ar_abiertas"

    # Tras la tarea (eager), el estado es disponible y el Parquet está en storage.
    detalle = client.get(f"/cargas/{cuerpo['id']}", headers={"X-Mock-User": UPLOADER_MX}).json()
    assert detalle["estado"] == "disponible"
    assert detalle["filas"] == 4

    ruta = ruta_parquet(Torre.OTC, "otc_ar_abiertas", "MX", "2026-05", 1)
    assert almacen_memoria.existe(CONTENEDOR_DATASETS, ruta)


def test_segunda_carga_distinta_incrementa_version(client: Any) -> None:
    r1 = _subir(client, ADMIN, pais="PE", contenido=_csv(pais="PE", filas=4))
    r2 = _subir(client, ADMIN, pais="PE", contenido=_csv(pais="PE", filas=6))
    assert r1.json()["version"] == 1
    assert r2.json()["version"] == 2


# --- rechazos de validación (422) ------------------------------------------


def test_rechazo_columnas_faltantes(client: Any) -> None:
    csv = b"pais,periodo,cliente\nMX,2026-05,ACME\n"
    resp = _subir(client, UPLOADER_MX, contenido=csv)
    assert resp.status_code == 422
    errores = resp.json()["detail"]["errores"]
    assert any("Falta la columna requerida" in e for e in errores)


def test_rechazo_pais_declarado_distinto_del_contenido(client: Any) -> None:
    # admin puede declarar CO; el contenido es MX → mismatch.
    resp = _subir(client, ADMIN, pais="CO", contenido=_csv(pais="MX"))
    assert resp.status_code == 422
    assert any("país declarado" in e for e in resp.json()["detail"]["errores"])


def test_rechazo_tipo_invalido(client: Any) -> None:
    cols = ",".join(c.nombre for c in AR.columnas)
    fila = "MX,2026-05,ACME,F-1,2026-01-01,2026-02-01,NO_NUMERO,10,USD"
    resp = _subir(client, UPLOADER_MX, contenido=f"{cols}\n{fila}\n".encode())
    assert resp.status_code == 422
    assert any("monto" in e for e in resp.json()["detail"]["errores"])


def test_rechazo_duplicado_por_hash(client: Any) -> None:
    contenido = _csv(pais="MX")
    primera = _subir(client, UPLOADER_MX, contenido=contenido)
    assert primera.status_code == 202
    segunda = _subir(client, UPLOADER_MX, contenido=contenido)
    assert segunda.status_code == 422
    assert any("duplicado" in e.lower() for e in segunda.json()["detail"]["errores"])


def test_rechazo_formato_no_soportado(client: Any) -> None:
    resp = _subir(client, UPLOADER_MX, contenido=b"hola", nombre="aging.txt")
    assert resp.status_code == 422


# --- RBAC -------------------------------------------------------------------


def test_rol_consulta_no_puede_cargar(client: Any) -> None:
    resp = _subir(client, CONSULTA_CO, pais="CO", contenido=_csv(pais="CO"))
    assert resp.status_code == 403


def test_uploader_no_puede_cargar_pais_sin_grant(client: Any) -> None:
    resp = _subir(client, UPLOADER_MX, pais="CO", contenido=_csv(pais="CO"))
    assert resp.status_code == 403


def test_plantilla_desconocida_404(client: Any) -> None:
    resp = _subir(client, UPLOADER_MX, plantilla="no_existe")
    assert resp.status_code == 404


def test_carga_requiere_autenticacion(client: Any) -> None:
    resp = client.post(
        "/cargas",
        data={"plantilla_codigo": "otc_ar_abiertas", "pais": "MX", "periodo": "2026-05"},
        files={"archivo": ("aging.csv", _csv(), "text/csv")},
    )
    assert resp.status_code == 401


# --- catálogo y frescura ----------------------------------------------------


def test_catalogo_filtra_por_rbac(client: Any) -> None:
    _subir(client, ADMIN, pais="MX", contenido=_csv(pais="MX"))
    _subir(client, ADMIN, pais="CO", contenido=_csv(pais="CO"))

    # consulta.co solo ve CO.
    co = client.get("/catalogo", headers={"X-Mock-User": CONSULTA_CO}).json()
    assert {c["pais"] for c in co} == {"CO"}

    # uploader.mx solo ve MX.
    mx = client.get("/catalogo", headers={"X-Mock-User": UPLOADER_MX}).json()
    assert {c["pais"] for c in mx} == {"MX"}


def test_obtener_carga_fuera_de_alcance_es_404(client: Any) -> None:
    creada = _subir(client, ADMIN, pais="CO", contenido=_csv(pais="CO")).json()
    # uploader.mx no tiene acceso a CO.
    resp = client.get(f"/cargas/{creada['id']}", headers={"X-Mock-User": UPLOADER_MX})
    assert resp.status_code == 404


def test_frescura_marca_al_dia_tras_carga(client: Any) -> None:
    _subir(client, UPLOADER_MX, pais="MX", contenido=_csv(pais="MX"))
    resp = client.get(
        "/catalogo/frescura", params={"torre": "OTC"}, headers={"X-Mock-User": UPLOADER_MX}
    )
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["pais"] == "MX"
    assert items[0]["estado"] == "al_dia"
