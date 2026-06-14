"""Eval de generación de dashboards (nivel agente, gated por Azure).

Valida semánticamente la spec generada (sin aflojar): debe ser válida, contener los
tipos de visual esperados y, al ejecutar sus queries por el motor, surgir los
valores esperados. Los no respondibles deben declararse con honestidad (spec nula).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.provider import MockAuthProvider
from app.dashboards.generador import generar_spec
from app.evals.runner import FalloEval, ReporteEval
from app.ia.proveedor import LLMProvider
from app.motor.motor import ejecutar_consulta
from app.motor.parquet_reader import ParquetReader

USUARIO_EVAL = "uploader.mx@powerai.dev"


class CasoDashboard(BaseModel):
    id: str
    peticion: str
    respondible: bool
    tipos_esperados: list[str] = []
    valores_esperados: list[str] = []


def cargar_casos() -> list[CasoDashboard]:
    carpeta = Path(__file__).resolve().parents[3] / "evals" / "dashboards"
    casos: list[CasoDashboard] = []
    for archivo in sorted(carpeta.glob("*.yaml")):
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8")) or []
        casos.extend(CasoDashboard.model_validate(d) for d in datos)
    return casos


def evaluar_dashboards(
    db: Session,
    provider: LLMProvider,
    casos: list[CasoDashboard],
    *,
    max_iteraciones: int = 5,
    reader: ParquetReader | None = None,
) -> ReporteEval:
    usuario = MockAuthProvider().autenticar(db, USUARIO_EVAL)
    fallos: list[FalloEval] = []
    aprobadas = 0
    for caso in casos:
        res = generar_spec(
            db, usuario, provider, caso.peticion, max_iteraciones=max_iteraciones, reader=reader
        )
        if not caso.respondible:
            if res.spec is None:
                aprobadas += 1
            else:
                fallos.append(
                    FalloEval(id=caso.id, fraseo=caso.peticion, motivo="generó spec no soportada")
                )
            continue

        if res.spec is None:
            fallos.append(
                FalloEval(id=caso.id, fraseo=caso.peticion, motivo=f"no generó spec: {res.mensaje}")
            )
            continue

        tipos = {v.tipo.value for v in res.spec.visuales}
        faltan_tipos = [t for t in caso.tipos_esperados if t not in tipos]
        if faltan_tipos:
            fallos.append(
                FalloEval(
                    id=caso.id,
                    fraseo=caso.peticion,
                    motivo=f"faltan tipos de visual: {faltan_tipos}",
                )
            )
            continue

        valores: set[str] = set()
        for v in res.spec.visuales:
            r = ejecutar_consulta(db, usuario, v.sql, reader=reader)
            for fila in r.filas:
                valores.update(str(x) for x in fila)
        faltan_valores = [val for val in caso.valores_esperados if val not in valores]
        if faltan_valores:
            fallos.append(
                FalloEval(
                    id=caso.id,
                    fraseo=caso.peticion,
                    motivo="faltan valores esperados",
                    esperado=caso.valores_esperados,
                    obtenido=faltan_valores,
                )
            )
        else:
            aprobadas += 1

    return ReporteEval(nivel="dashboards", total=len(casos), aprobadas=aprobadas, fallos=fallos)
