"""Tests unitarios de plantillas por descubrimiento (sin BD)."""

from app.auth.schemas import Grant, UsuarioAutenticado
from app.domain.columnas import ColumnaSpec
from app.domain.enums import Rol, TipoColumna, Torre
from app.ingesta.lector import Tabla
from app.services.plantillas import (
    _slug,
    aplicar_mapeo,
    es_admin_torre,
    puede_definir,
    slugificar_columnas,
)


def test_slug_pliega_acentos_espacios_y_simbolos() -> None:
    # Casos del reporte real (Manpower Perú).
    assert _slug("Número Documento") == "numero_documento"
    assert _slug("Importe S/") == "importe_s"
    assert _slug("RUC") == "ruc"
    assert _slug("País") == "pais"
    # Un encabezado que empieza por número recibe prefijo (debe empezar por letra).
    assert _slug("2026 Total")[0].isalpha()


def test_slugificar_columnas_conserva_etiqueta_y_desambigua_colisiones() -> None:
    cols = [
        ColumnaSpec(nombre="Monto USD", tipo=TipoColumna.DECIMAL),
        ColumnaSpec(nombre="Monto (USD)", tipo=TipoColumna.DECIMAL),
        ColumnaSpec(nombre="Número Documento", tipo=TipoColumna.TEXTO),
    ]
    salida, avisos = slugificar_columnas(cols)
    nombres = [c.nombre for c in salida]
    # Colisión desambiguada con sufijo numérico (ambos slugifican a 'monto_usd').
    assert nombres == ["monto_usd", "monto_usd_2", "numero_documento"]
    # La etiqueta de negocio (encabezado original) se conserva.
    assert [c.etiqueta for c in salida] == ["Monto USD", "Monto (USD)", "Número Documento"]
    # Y se avisa de la desambiguación.
    assert any("monto_usd_2" in a for a in avisos)


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
