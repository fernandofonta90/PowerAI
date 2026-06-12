"""Proveedor LLM sobre Azure OpenAI (capa adapter).

Traduce los modelos agnósticos del proveedor (MensajeChat/ToolSpec/RespuestaLLM)
al formato del SDK de OpenAI y de vuelta. Es la ÚNICA pieza que importa el SDK.
"""

import json
from typing import Any

from app.config import get_settings
from app.ia.proveedor import (
    LlamadaTool,
    LLMProvider,
    MensajeChat,
    RespuestaLLM,
    ToolSpec,
)


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


class AzureOpenAIProvider(LLMProvider):
    """Implementación de LLMProvider contra Azure OpenAI."""

    def __init__(self) -> None:
        from openai import AzureOpenAI

        s = get_settings()
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
        resp = self._client.chat.completions.create(
            model=self._deployment,
            messages=[_a_openai(m) for m in mensajes],
            tools=oai_tools or None,
        )
        msg = resp.choices[0].message
        llamadas = [
            LlamadaTool(
                id=tc.id,
                nombre=tc.function.name,
                argumentos=json.loads(tc.function.arguments or "{}"),
            )
            for tc in (msg.tool_calls or [])
        ]
        return RespuestaLLM(contenido=msg.content, tool_calls=llamadas)
