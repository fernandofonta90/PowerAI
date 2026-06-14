"""Endpoints por torre. Por ahora: preguntas sugeridas (chips del home)."""

from fastapi import APIRouter, HTTPException, status

from app.auth.deps import CurrentUser
from app.domain.enums import Torre
from app.evals.banco import cargar_banco

router = APIRouter(tags=["torres"])

# Preguntas representativas por torre (ids del banco de preguntas doradas).
_SUGERIDAS_POR_TORRE: dict[Torre, list[str]] = {
    Torre.OTC: [
        "otc-aging-total",
        "otc-top-cliente-deuda",
        "otc-mora-mayor-60-monto",
        "otc-aging-buckets",
    ],
}


@router.get("/torres/{torre}/preguntas-sugeridas", response_model=list[str])
def preguntas_sugeridas(torre: Torre, usuario: CurrentUser) -> list[str]:
    """Devuelve 3-4 preguntas representativas de la torre (desde el banco de evals)."""
    if torre not in usuario.torres_accesibles():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sin acceso a la torre {torre.value}.",
        )
    ids = _SUGERIDAS_POR_TORRE.get(torre, [])
    if not ids:
        return []
    por_id = {p.id: p.pregunta for p in cargar_banco()}
    return [por_id[i] for i in ids if i in por_id]
