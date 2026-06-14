"""Proveedor LLM sobre Azure OpenAI (capa adapter).

Traduce los modelos agnósticos del proveedor (MensajeChat/ToolSpec/RespuestaLLM)
al formato del SDK de OpenAI y de vuelta. Es la ÚNICA pieza que importa el SDK.
Reintenta ante errores transitorios (rate limit, 5xx, timeouts) y reclasifica
cualquier fallo terminal como ProveedorLLMError (mensaje claro, sin stack críptico).
"""

import json
from typing import Any

from app.config import get_settings
from app.ia.proveedor import (
    LlamadaTool,
    LLMProvider,
    MensajeChat,
    ProveedorLLMError,
    RespuestaLLM,
    ToolSpec,
    UsoTokens,
)
from app.ia.reintentos import reintentar


def _a_openai(m: MensajeChat) -> dict[str, Any]:
    if m.rol == "tool":
        return {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.contenido or ""}
    msg: dict[str, Any] = {"role": m.rol, "content": m.contenido}
    if m.tool_calls:
        msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.nombre, "arguments": json.dumps(tc.argumentos)},
            }
            for tc in m.tool_calls
        ]
    return msg


def _es_transitorio(exc: Exception) -> bool:
    import openai

    return isinstance(
        exc,
        (
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.APIConnectionError,
            openai.InternalServerError,
        ),
    )


class AzureOpenAIProvider(LLMProvider):
    """Implementación de LLMProvider contra Azure OpenAI."""

    def __init__(self) -> None:
        from openai import AzureOpenAI

        s = get_settings()
        faltantes = [
            n
            for n, v in (
                ("POWERAI_AZURE_OPENAI_ENDPOINT", s.azure_openai_endpoint),
                ("POWERAI_AZURE_OPENAI_API_KEY", s.azure_openai_api_key),
                ("POWERAI_AZURE_OPENAI_DEPLOYMENT", s.azure_openai_deployment),
            )
            if not v
        ]
        if faltantes:
            raise ProveedorLLMError("Faltan variables de Azure OpenAI: " + ", ".join(faltantes))
        self._client = AzureOpenAI(
            azure_endpoint=s.azure_openai_endpoint,
            api_key=s.azure_openai_api_key,
            api_version=s.azure_openai_api_version,
        )
        self._deployment = s.azure_openai_deployment

    def completar(self, mensajes: list[MensajeChat], tools: list[ToolSpec]) -> RespuestaLLM:
        oai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.nombre,
                    "description": t.descripcion,
                    "parameters": t.parametros,
                },
            }
            for t in tools
        ]

        def _llamar() -> Any:
            return self._client.chat.completions.create(
                model=self._deployment,
                messages=[_a_openai(m) for m in mensajes],
                tools=oai_tools or None,
            )

        try:
            resp = reintentar(_llamar, es_transitorio=_es_transitorio)
        except ProveedorLLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - reclasifica a error de proveedor claro
            raise ProveedorLLMError(f"Azure OpenAI: {exc}") from exc

        msg = resp.choices[0].message
        llamadas = [
            LlamadaTool(
                id=tc.id,
                nombre=tc.function.name,
                argumentos=json.loads(tc.function.arguments or "{}"),
            )
            for tc in (msg.tool_calls or [])
        ]
        uso = None
        if resp.usage is not None:
            uso = UsoTokens(
                entrada=resp.usage.prompt_tokens or 0,
                salida=resp.usage.completion_tokens or 0,
            )
        return RespuestaLLM(contenido=msg.content, tool_calls=llamadas, uso=uso)
