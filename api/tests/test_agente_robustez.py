"""Robustez del agente ante fallos del proveedor LLM y registro de tokens."""

from typing import Any

import pytest
from app.auth.schemas import Grant, UsuarioAutenticado
from app.domain.enums import Rol, Torre
from app.ia.agente import responder
from app.ia.proveedor import (
    LLMProvider,
    MensajeChat,
    ProveedorLLMError,
    RespuestaLLM,
    ToolSpec,
)

pytestmark = pytest.mark.integration


def _mx() -> UsuarioAutenticado:
    return UsuarioAutenticado(
        email="uploader.mx@powerai.dev",
        nombre="MX",
        grants=[Grant(torre=Torre.OTC, pais="MX", rol=Rol.CONSULTA)],
    )


class _ProviderCaido(LLMProvider):
    def completar(self, mensajes: list[MensajeChat], tools: list[ToolSpec]) -> RespuestaLLM:
        raise ProveedorLLMError("503 del servicio")


def test_agente_responde_honesto_si_el_proveedor_falla(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any, seed_usuarios: Any
) -> None:
    res = responder(db_session, _mx(), _ProviderCaido(), [], "¿cartera?")
    assert "problema temporal" in res.texto.lower()
    # No inventó: sin fuentes ni datos.
    assert res.citacion.fuentes == []
    assert res.datos_tabulares is None


def test_agente_acumula_tokens(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any, seed_usuarios: Any
) -> None:
    from app.ia.fake import FakeProvider

    crear_carga(pais="MX", filas=3)
    # FakeProvider demo: 2 llamadas (tool + final), 10/5 tokens cada una.
    res = responder(db_session, _mx(), FakeProvider(), [], "¿cartera?")
    assert res.uso.entrada == 20
    assert res.uso.salida == 10
