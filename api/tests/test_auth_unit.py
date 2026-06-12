"""Tests unitarios de la lógica de autorización (sin base de datos)."""

from app.auth.schemas import Grant, UsuarioAutenticado
from app.domain.enums import Pais, Rol, Torre


def _usuario(grants: list[Grant]) -> UsuarioAutenticado:
    return UsuarioAutenticado(email="x@powerai.dev", nombre="X", grants=grants)


def test_grant_cubre_pais_exacto() -> None:
    g = Grant(torre=Torre.OTC, pais="MX", rol=Rol.CONSULTA)
    assert g.cubre(Torre.OTC, Pais.MX)
    assert not g.cubre(Torre.OTC, Pais.CO)
    assert not g.cubre(Torre.PTP, Pais.MX)


def test_grant_comodin_cubre_todos_los_paises_de_la_torre() -> None:
    g = Grant(torre=Torre.OTC, pais="*", rol=Rol.ADMIN)
    assert g.cubre(Torre.OTC, Pais.MX)
    assert g.cubre(Torre.OTC, Pais.AR)
    assert not g.cubre(Torre.PTP, Pais.MX)


def test_tiene_acceso_respeta_torre_y_pais() -> None:
    u = _usuario([Grant(torre=Torre.OTC, pais="MX", rol=Rol.CONSULTA)])
    assert u.tiene_acceso(Torre.OTC, Pais.MX)
    assert not u.tiene_acceso(Torre.OTC, Pais.CO)
    assert not u.tiene_acceso(Torre.PTP, Pais.MX)


def test_tiene_acceso_filtra_por_rol() -> None:
    u = _usuario([Grant(torre=Torre.OTC, pais="MX", rol=Rol.CONSULTA)])
    assert u.tiene_acceso(Torre.OTC, Pais.MX, roles={Rol.CONSULTA})
    assert not u.tiene_acceso(Torre.OTC, Pais.MX, roles={Rol.UPLOADER})
    # Sin filtro de rol, cualquier grant basta.
    assert u.tiene_acceso(Torre.OTC, Pais.MX)


def test_admin_comodin_concede_y_respeta_rol() -> None:
    u = _usuario([Grant(torre=Torre.OTC, pais="*", rol=Rol.ADMIN)])
    assert u.tiene_acceso(Torre.OTC, Pais.PE, roles={Rol.ADMIN})
    assert not u.tiene_acceso(Torre.OTC, Pais.PE, roles={Rol.UPLOADER})


def test_torres_y_paises_accesibles() -> None:
    u = _usuario(
        [
            Grant(torre=Torre.OTC, pais="MX", rol=Rol.CONSULTA),
            Grant(torre=Torre.PTP, pais="AR", rol=Rol.CONSULTA),
        ]
    )
    assert u.torres_accesibles() == {Torre.OTC, Torre.PTP}
    assert u.paises_en(Torre.OTC) == {"MX"}
    assert u.paises_en(Torre.PTP) == {"AR"}
