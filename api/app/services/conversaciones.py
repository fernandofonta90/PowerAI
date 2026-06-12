"""Orquestación de conversaciones del chat analítico.

Persiste el mensaje del usuario, ejecuta el agente, persiste la respuesta del
asistente con su citación y la liga a las entradas de bitácora que generó.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UsuarioAutenticado
from app.ia.agente import ResultadoAgente, responder
from app.ia.proveedor import LLMProvider, MensajeChat
from app.models.bitacora import BitacoraConsulta
from app.models.conversacion import Conversacion, Mensaje
from app.motor.parquet_reader import ParquetReader


def crear_conversacion(db: Session, usuario: UsuarioAutenticado, titulo: str = "") -> Conversacion:
    conversacion = Conversacion(usuario_email=usuario.email, titulo=titulo)
    db.add(conversacion)
    db.commit()
    db.refresh(conversacion)
    return conversacion


def _historial(conversacion: Conversacion) -> list[MensajeChat]:
    """Mapea los mensajes persistidos (usuario/asistente) al hilo del modelo."""
    return [
        MensajeChat(rol=m.rol, contenido=m.contenido)
        for m in conversacion.mensajes
        if m.rol in ("user", "assistant")
    ]


def enviar_mensaje(
    db: Session,
    usuario: UsuarioAutenticado,
    provider: LLMProvider,
    conversacion: Conversacion,
    pregunta: str,
    *,
    max_iteraciones: int = 5,
    max_filas: int = 1000,
    reader: ParquetReader | None = None,
) -> tuple[Mensaje, ResultadoAgente]:
    """Procesa la pregunta del usuario y devuelve el mensaje del asistente."""
    historial = _historial(conversacion)

    db.add(Mensaje(conversacion_id=conversacion.id, rol="user", contenido=pregunta))
    db.commit()

    resultado = responder(
        db,
        usuario,
        provider,
        historial,
        pregunta,
        max_iteraciones=max_iteraciones,
        max_filas=max_filas,
        reader=reader,
    )

    mensaje = Mensaje(
        conversacion_id=conversacion.id,
        rol="assistant",
        contenido=resultado.texto,
        citacion_json=resultado.citacion.model_dump(mode="json"),
    )
    if resultado.citacion.sql_ejecutado_ids:
        mensaje.consultas = list(
            db.scalars(
                select(BitacoraConsulta).where(
                    BitacoraConsulta.id.in_(resultado.citacion.sql_ejecutado_ids)
                )
            )
        )
    db.add(mensaje)
    db.commit()
    db.refresh(mensaje)
    return mensaje, resultado
