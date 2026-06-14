"""Proveedor LLM falso y determinístico, para desarrollo, demo y tests.

Dos modos:
- Con ``guion`` (tests): devuelve en orden la secuencia de :class:`RespuestaLLM`
  (tool-calls y respuesta final guionizados).
- Sin guion (dev/demo/E2E): ejercita el flujo completo de forma determinística —
  ejecuta una consulta representativa sobre el catálogo y luego redacta una
  respuesta. Así el producto se ve y se prueba sin Azure OpenAI.
"""

from app.ia.proveedor import (
    LlamadaTool,
    LLMProvider,
    MensajeChat,
    RespuestaLLM,
    ToolSpec,
    UsoTokens,
)

# Uso de tokens simulado por llamada (para ejercitar el registro de consumo).
_USO_FAKE = UsoTokens(entrada=10, salida=5)

# Consulta representativa para la demo: saldo por cliente de la cartera abierta.
# Si el usuario no tiene datos visibles (RLS), devuelve vacío (respuesta honesta).
_SQL_DEMO = (
    "SELECT cliente, sum(monto) AS saldo FROM ar_abiertas GROUP BY cliente ORDER BY saldo DESC"
)


class FakeProvider(LLMProvider):
    """Devuelve respuestas guionizadas o, sin guion, un flujo demo determinístico."""

    def __init__(self, guion: list[RespuestaLLM] | None = None) -> None:
        self._guion = list(guion) if guion is not None else None
        self._i = 0
        self.hilos: list[list[MensajeChat]] = []

    def completar(self, mensajes: list[MensajeChat], tools: list[ToolSpec]) -> RespuestaLLM:
        self.hilos.append(list(mensajes))
        if self._guion is not None:
            if self._i >= len(self._guion):
                respuesta = RespuestaLLM(contenido="(fin del guion de prueba)")
            else:
                respuesta = self._guion[self._i]
                self._i += 1
        else:
            respuesta = self._demo(mensajes, tools)
        if respuesta.uso is None:
            respuesta.uso = _USO_FAKE
        return respuesta

    def _demo(self, mensajes: list[MensajeChat], tools: list[ToolSpec]) -> RespuestaLLM:
        # Si ya hay un resultado de herramienta en el hilo, redacta la respuesta final.
        if any(m.rol == "tool" for m in mensajes):
            return RespuestaLLM(
                contenido=(
                    "Según las vistas disponibles para tu alcance, este es el saldo de "
                    "cartera abierta por cliente. Revisa el detalle y las fuentes citadas."
                )
            )
        # Primer turno: ejecuta la consulta de demostración si la tool existe.
        if any(t.nombre == "ejecutar_sql" for t in tools):
            return RespuestaLLM(
                tool_calls=[
                    LlamadaTool(id="demo", nombre="ejecutar_sql", argumentos={"sql": _SQL_DEMO})
                ]
            )
        return RespuestaLLM(contenido="No hay herramientas disponibles en este entorno.")
