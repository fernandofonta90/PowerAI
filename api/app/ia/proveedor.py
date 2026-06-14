"""Interfaz de proveedor LLM (capa adapter) y modelos agnósticos del proveedor.

La lógica de negocio nunca importa SDKs de un proveedor: depende de esta
interfaz (regla 5 del CLAUDE.md). Implementaciones: FakeProvider (tests) y
AzureOpenAIProvider (producción), seleccionadas por configuración.
"""

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel


class ToolSpec(BaseModel):
    """Definición de una herramienta disponible para el modelo."""

    nombre: str
    descripcion: str
    parametros: dict[str, Any]  # JSON Schema de los argumentos


class LlamadaTool(BaseModel):
    """Una invocación de herramienta emitida por el modelo."""

    id: str
    nombre: str
    argumentos: dict[str, Any]


class MensajeChat(BaseModel):
    """Mensaje en el hilo de conversación con el modelo."""

    rol: Literal["system", "user", "assistant", "tool"]
    contenido: str | None = None
    tool_calls: list[LlamadaTool] = []
    tool_call_id: str | None = None


class UsoTokens(BaseModel):
    """Tokens consumidos por una llamada al modelo (insumo del control de costos)."""

    entrada: int = 0
    salida: int = 0


class RespuestaLLM(BaseModel):
    """Respuesta del modelo: texto final y/o llamadas a herramientas."""

    contenido: str | None = None
    tool_calls: list[LlamadaTool] = []
    uso: UsoTokens | None = None


class ProveedorLLMError(Exception):
    """Fallo terminal del proveedor LLM (tras reintentos): no se pudo completar."""


class LLMProvider(ABC):
    """Contrato de un proveedor LLM con soporte de tool-calling."""

    @abstractmethod
    def completar(self, mensajes: list[MensajeChat], tools: list[ToolSpec]) -> RespuestaLLM:
        """Devuelve la siguiente respuesta del modelo.

        Lanza :class:`ProveedorLLMError` si no puede completar tras reintentos.
        """


_provider: LLMProvider | None = None


def set_llm_provider(provider: LLMProvider | None) -> None:
    """Fija (o limpia) el proveedor global. Usado por los tests."""
    global _provider
    _provider = provider


def get_llm_provider() -> LLMProvider:
    """Devuelve el proveedor configurado, construyéndolo de forma perezosa."""
    global _provider
    if _provider is None:
        from app.config import get_settings

        _provider = build_llm_provider(get_settings().llm_provider)
    return _provider


def build_llm_provider(nombre: str) -> LLMProvider:
    """Fábrica de proveedores según la configuración (POWERAI_LLM_PROVIDER)."""
    if nombre == "fake":
        from app.ia.fake import FakeProvider

        return FakeProvider()
    if nombre == "azure_openai":
        from app.ia.azure_openai import AzureOpenAIProvider

        return AzureOpenAIProvider()
    raise NotImplementedError(f"Proveedor LLM no soportado: {nombre}")
