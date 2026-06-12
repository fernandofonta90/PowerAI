"""Proveedor LLM falso y determinístico, para desarrollo y tests.

En tests se construye con un "guion": una secuencia de :class:`RespuestaLLM` que
el agente irá consumiendo (tool-calls y respuesta final guionizados). Sin guion,
devuelve una respuesta canónica sin tool-calls (útil en dev sin Azure OpenAI).
"""

from app.ia.proveedor import LLMProvider, MensajeChat, RespuestaLLM, ToolSpec


class FakeProvider(LLMProvider):
    """Devuelve respuestas guionizadas en orden; registra los hilos recibidos."""

    def __init__(self, guion: list[RespuestaLLM] | None = None) -> None:
        self._guion = list(guion) if guion is not None else None
        self._i = 0
        self.hilos: list[list[MensajeChat]] = []

    def completar(self, mensajes: list[MensajeChat], tools: list[ToolSpec]) -> RespuestaLLM:
        self.hilos.append(list(mensajes))
        if self._guion is None:
            return RespuestaLLM(
                contenido=(
                    "Proveedor de IA en modo de prueba: configura POWERAI_LLM_PROVIDER"
                    "=azure_openai para respuestas reales."
                )
            )
        if self._i >= len(self._guion):
            return RespuestaLLM(contenido="(fin del guion de prueba)")
        respuesta = self._guion[self._i]
        self._i += 1
        return respuesta
