"""Reintentos acotados con backoff para llamadas al proveedor LLM.

Puro y testeable: la función de dormir se inyecta. Tras agotar los reintentos
ante errores transitorios (rate limit, 5xx, timeouts), lanza ProveedorLLMError.
"""

import time
from collections.abc import Callable

from app.ia.proveedor import ProveedorLLMError


def reintentar[T](
    fn: Callable[[], T],
    *,
    es_transitorio: Callable[[Exception], bool],
    intentos: int = 3,
    base_segundos: float = 0.5,
    dormir: Callable[[float], None] = time.sleep,
) -> T:
    """Ejecuta ``fn`` reintentando solo ante errores transitorios.

    Los errores NO transitorios se propagan tal cual. Si se agotan los intentos
    ante errores transitorios, lanza :class:`ProveedorLLMError`.
    """
    ultimo: Exception | None = None
    for i in range(intentos):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - se reclasifica abajo
            if not es_transitorio(exc):
                raise
            ultimo = exc
            if i < intentos - 1:
                dormir(base_segundos * (2**i))
    raise ProveedorLLMError(
        f"El servicio de IA no respondió tras {intentos} intentos: {ultimo}"
    ) from ultimo
