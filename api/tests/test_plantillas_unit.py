"""Tests unitarios de plantillas por descubrimiento (sin BD)."""

from app.auth.schemas import Grant, UsuarioAutenticado
from app.domain.enums import Rol, Torre
from app.ingesta.lector import Tabla
from app.services.plantillas import aplicar_mapeo, es_admin_torre, puede_definir


def _usuario(rol: Rol, torre: Torre = Torre.OTC) -> UsuarioAutenticado:
    return UsuarioAutenticado(
        email="x@powerai.dev", nombre="X", grants=[Grant(torre=torre, pais="*", rol=rol)]
    )


def test_aplicar_mapeo_renombra_sin_perder_datos() -> None:
    tabla = Tabla(
        columnas=["importe", "pais", "periodo"],
        filas=[{"importe": "100.00", "pais": "MX", "periodo": "2026-05"}],
    )
    mapeada = aplicar_mapeo(tabla, {"monto": "importe"})
    # La columna esperada aparece con el valor del archivo...
    assert "monto" in mapeada.columnas
    assert mapeada.filas[0]["monto"] == "100.00"
    # ...y la original se conserva (mapear copia, no destruye).
    assert mapeada.filas[0]["importe"] == "100.00"


def test_aplicar_mapeo_vacio_es_identidad() -> None:
    tabla = Tabla(columnas=["a"], filas=[{"a": "1"}])
    assert aplicar_mapeo(tabla, {}) is tabla


def test_puede_definir_admin_y_uploader_si_consulta_no() -> None:
    assert puede_definir(_usuario(Rol.ADMIN), Torre.OTC)
    assert puede_definir(_usuario(Rol.UPLOADER), Torre.OTC)
    assert not puede_definir(_usuario(Rol.CONSULTA), Torre.OTC)
    # Otra torre: sin grant, no puede.
    assert not puede_definir(_usuario(Rol.ADMIN, Torre.OTC), Torre.PTP)


def test_es_admin_torre_solo_admin() -> None:
    assert es_admin_torre(_usuario(Rol.ADMIN), Torre.OTC)
    assert not es_admin_torre(_usuario(Rol.UPLOADER), Torre.OTC)
    assert not es_admin_torre(_usuario(Rol.CONSULTA), Torre.OTC)
