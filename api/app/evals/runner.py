"""Runner del banco de preguntas doradas — niveles motor y agente.

- Nivel MOTOR (determinístico, corre en CI): ejecuta el ``sql_canonico`` de cada
  pregunta por el motor M3 y compara contra la aserción. Umbral 100%: aquí no hay
  probabilidad, solo correctitud.
- Nivel AGENTE (gated por credenciales de Azure, no corre en CI): la pregunta en
  lenguaje natural (y sus variantes) entra por el agente M4 completo y su resultado
  se compara contra la misma aserción. Umbral ≥95%.

Invocable por CLI (``python -m app.evals.runner --nivel motor|agente``) y por pytest
(funciones ``evaluar_motor`` / ``evaluar_agente``).
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.provider import MockAuthProvider
from app.auth.schemas import UsuarioAutenticado
from app.evals.banco import PreguntaDorada, cargar_banco
from app.ia.agente import responder
from app.ia.proveedor import LLMProvider
from app.motor.motor import ejecutar_consulta
from app.motor.parquet_reader import ParquetReader

UMBRAL_AGENTE = 0.95


class FalloEval(BaseModel):
    id: str
    fraseo: str
    motivo: str
    esperado: Any = None
    obtenido: Any = None
    sql_generado: list[str] | None = None
    sql_esperado: str | None = None


class ReporteEval(BaseModel):
    nivel: str
    total: int
    aprobadas: int
    fallos: list[FalloEval]

    @property
    def tasa(self) -> float:
        return self.aprobadas / self.total if self.total else 1.0

    def resumen(self) -> str:
        lineas = [f"Nivel {self.nivel}: {self.aprobadas}/{self.total} aprobadas ({self.tasa:.1%})."]
        for f in self.fallos:
            lineas.append(f"  ✗ [{f.id}] «{f.fraseo}»: {f.motivo}")
            if f.esperado is not None:
                lineas.append(f"      esperado={f.esperado} obtenido={f.obtenido}")
            if f.sql_esperado is not None:
                lineas.append(f"      SQL esperado: {f.sql_esperado}")
            if f.sql_generado is not None:
                lineas.append(f"      SQL generado: {f.sql_generado}")
        return "\n".join(lineas)


def _usuario(db: Session, email: str) -> UsuarioAutenticado:
    return MockAuthProvider().autenticar(db, email)


def _sql_de_bitacora(db: Session, ids: list[Any]) -> list[str]:
    """SQL realmente ejecutado por el agente (para comparar contra el esperado)."""
    from app.models.bitacora import BitacoraConsulta

    if not ids:
        return []
    return [
        b.sql_ejecutado
        for b in db.scalars(select(BitacoraConsulta).where(BitacoraConsulta.id.in_(ids)))
    ]


def evaluar_motor(
    db: Session, preguntas: list[PreguntaDorada], *, reader: ParquetReader | None = None
) -> ReporteEval:
    """Evalúa el nivel motor: SQL canónico vs aserción (solo preguntas respondibles)."""
    respondibles = [p for p in preguntas if p.respondible]
    fallos: list[FalloEval] = []
    aprobadas = 0
    for p in respondibles:
        if p.sql_canonico is None or p.asercion is None:
            fallos.append(FalloEval(id=p.id, fraseo=p.pregunta, motivo="sin sql/aserción"))
            continue
        usuario = _usuario(db, p.usuario)
        try:
            resultado = ejecutar_consulta(db, usuario, p.sql_canonico, reader=reader)
        except Exception as exc:  # noqa: BLE001
            fallos.append(FalloEval(id=p.id, fraseo=p.pregunta, motivo=f"error: {exc}"))
            continue
        if resultado.filas == p.asercion.filas:
            aprobadas += 1
        else:
            fallos.append(
                FalloEval(
                    id=p.id,
                    fraseo=p.pregunta,
                    motivo="resultado no coincide",
                    esperado=p.asercion.filas,
                    obtenido=resultado.filas,
                )
            )
    return ReporteEval(nivel="motor", total=len(respondibles), aprobadas=aprobadas, fallos=fallos)


def evaluar_agente(
    db: Session,
    provider: LLMProvider,
    preguntas: list[PreguntaDorada],
    *,
    max_iteraciones: int = 5,
    max_filas: int = 1000,
    reader: ParquetReader | None = None,
) -> ReporteEval:
    """Evalúa el nivel agente: cada fraseo NL por el agente M4 vs aserción/honestidad."""
    fallos: list[FalloEval] = []
    total = 0
    aprobadas = 0
    for p in preguntas:
        usuario = _usuario(db, p.usuario)
        for fraseo in p.fraseos():
            total += 1
            res = responder(
                db,
                usuario,
                provider,
                [],
                fraseo,
                max_iteraciones=max_iteraciones,
                max_filas=max_filas,
                reader=reader,
            )
            if p.respondible:
                obtenido = res.datos_tabulares.filas if res.datos_tabulares else None
                esperado = p.asercion.filas if p.asercion else None
                if obtenido == esperado:
                    aprobadas += 1
                else:
                    fallos.append(
                        FalloEval(
                            id=p.id,
                            fraseo=fraseo,
                            motivo="datos no coinciden",
                            esperado=esperado,
                            obtenido=obtenido,
                            sql_generado=_sql_de_bitacora(db, res.citacion.sql_ejecutado_ids),
                            sql_esperado=p.sql_canonico,
                        )
                    )
            else:
                # Honestidad: no debe inventar (sin fuentes ni datos).
                if not res.citacion.fuentes and res.datos_tabulares is None:
                    aprobadas += 1
                else:
                    fallos.append(
                        FalloEval(id=p.id, fraseo=fraseo, motivo="respondió algo no soportado")
                    )
    return ReporteEval(nivel="agente", total=total, aprobadas=aprobadas, fallos=fallos)


def _preparar_db_real() -> Session:
    """Siembra plantillas/vistas/usuarios y construye el dataset en la BD configurada."""
    from app.db import SessionLocal
    from app.evals.dataset import construir_dataset
    from app.scripts.seed_dev import sembrar as sembrar_usuarios
    from app.scripts.seed_plantillas import sembrar_plantillas
    from app.scripts.seed_vistas import sembrar_vistas
    from app.storage import get_almacen

    db = SessionLocal()
    sembrar_usuarios(db)
    sembrar_plantillas(db)
    sembrar_vistas(db)
    construir_dataset(db, get_almacen())
    return db


def main() -> None:
    parser = argparse.ArgumentParser(description="Runner de preguntas doradas")
    parser.add_argument("--nivel", choices=["motor", "agente"], required=True)
    args = parser.parse_args()

    preguntas = cargar_banco()
    db = _preparar_db_real()
    try:
        if args.nivel == "motor":
            reporte = evaluar_motor(db, preguntas)
            ok = reporte.tasa >= 1.0
        else:
            from app.config import get_settings
            from app.ia.proveedor import get_llm_provider

            s = get_settings()
            reporte = evaluar_agente(
                db,
                get_llm_provider(),
                preguntas,
                max_iteraciones=s.agente_max_iteraciones,
                max_filas=s.agente_max_filas,
            )
            ok = reporte.tasa >= UMBRAL_AGENTE
    finally:
        db.close()

    print(reporte.resumen())
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
