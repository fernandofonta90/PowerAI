"""Tests unitarios del loader del catálogo (parseo del seed real, sin BD)."""

from app.scripts.seed_catalogo import ESTADOS_VALIDOS, cargar_filas


def test_seed_se_parsea_y_no_esta_vacio() -> None:
    filas = cargar_filas()
    assert len(filas) > 0
    # Todas las preguntas tienen los campos esperados y un estado válido.
    for fila in filas:
        assert fila["codigo"]
        assert fila["texto"]
        assert fila["torre_clave"]
        assert fila["categoria"]
        assert fila["estado"] in ESTADOS_VALIDOS


def test_codigos_son_unicos() -> None:
    filas = cargar_filas()
    codigos = [f["codigo"] for f in filas]
    assert len(codigos) == len(set(codigos))


def test_otc_tiene_activas_y_resto_solo_proximamente() -> None:
    filas = cargar_filas()
    por_torre: dict[str, set[str]] = {}
    for fila in filas:
        por_torre.setdefault(fila["torre_clave"], set()).add(fila["estado"])
    # Hoy solo OTC está activa (Fase 1 / piloto).
    assert "activa" in por_torre["OTC"]
    for torre, estados in por_torre.items():
        if torre != "OTC":
            assert estados == {"proximamente"}, f"{torre} no debería tener activas todavía"


def test_orden_es_estable_y_creciente() -> None:
    filas = cargar_filas()
    ordenes = [f["orden"] for f in filas]
    assert ordenes == list(range(len(filas)))
