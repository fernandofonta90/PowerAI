"""Diagnóstico de conexión con Azure OpenAI.

Confirma que el AzureOpenAIProvider se construye con las variables presentes, se
conecta, hace un tool-call simple y responde. Falla con un mensaje CLARO (qué
variable falta, qué dijo Azure) en vez de un stack trace críptico.

    uv run python -m app.scripts.check_llm
"""

import sys

from app.ia.proveedor import (
    MensajeChat,
    ProveedorLLMError,
    ToolSpec,
)

_TOOL_ECO = ToolSpec(
    nombre="eco",
    descripcion="Devuelve el texto recibido. Úsala para responder.",
    parametros={
        "type": "object",
        "properties": {"texto": {"type": "string"}},
        "required": ["texto"],
        "additionalProperties": False,
    },
)


def main() -> None:
    from app.ia.azure_openai import AzureOpenAIProvider

    print("Diagnóstico de Azure OpenAI…")
    try:
        provider = AzureOpenAIProvider()
    except ProveedorLLMError as exc:
        print(f"✗ Configuración incompleta: {exc}")
        print("  Define las variables POWERAI_AZURE_OPENAI_* en api/.env y reintenta.")
        sys.exit(1)

    mensajes = [
        MensajeChat(
            rol="user",
            contenido="Llama a la herramienta eco con texto='ok' para confirmar.",
        )
    ]
    try:
        resp = provider.completar(mensajes, [_TOOL_ECO])
    except ProveedorLLMError as exc:
        print(f"✗ No se pudo completar contra Azure OpenAI: {exc}")
        print("  Verifica el endpoint, la API key, el nombre del deployment y la api_version.")
        sys.exit(1)

    print("✓ Conexión exitosa.")
    print(f"  tool_calls: {[t.nombre for t in resp.tool_calls]}")
    if resp.contenido:
        print(f"  texto: {resp.contenido[:80]}")
    if resp.uso:
        print(f"  tokens: entrada={resp.uso.entrada} salida={resp.uso.salida}")
    sys.exit(0)


if __name__ == "__main__":
    main()
