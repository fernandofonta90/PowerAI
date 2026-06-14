"""Servicio de plantillas por descubrimiento (M11).

La primera carga enseña la estructura: se leen los encabezados, el admin/uploader
confirma el mapeo (nombre de negocio + tipo) y las llaves de país/periodo, y nace
la plantilla junto con una VISTA 1:1 automática que el admin nombra. Las cargas
siguientes comparan contra la plantilla; si no calzan, se MAPEAN (se acomoda la
carga a la plantilla, nunca se redefine el molde). Cambiar el molde es edición
explícita de admin, con aviso de impacto.

Cadena cerrada: plantilla → archivo → vista → fuente del experto (M10), sin SQL manual.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.schemas import UsuarioAutenticado
from app.domain.columnas import ColumnaDescrita, ColumnaSpec
from app.domain.enums import Frecuencia, Rol, Torre
from app.ingesta.lector import Tabla, leer_tabla
from app.models.carga import CargaArchivo
from app.models.plantilla import PlantillaReporte
from app.models.vista import VistaCatalogo

_FILAS_MUESTRA = 5
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


class DefinicionInvalida(Exception):
    """La definición de plantilla/vista propuesta no es válida."""


# --- RBAC de gobierno -----------------------------------------------------------------


def puede_definir(usuario: UsuarioAutenticado, torre: Torre) -> bool:
    """Crear plantilla/vista = admin O uploader de la torre (acto gobernado)."""
    return any(g.torre == torre and g.rol in (Rol.UPLOADER, Rol.ADMIN) for g in usuario.grants)


def es_admin_torre(usuario: UsuarioAutenticado, torre: Torre) -> bool:
    """Cambiar el molde (schema de plantilla) = solo admin de la torre."""
    return any(g.torre == torre and g.rol == Rol.ADMIN for g in usuario.grants)


# --- Inspección y emparejamiento ------------------------------------------------------


@dataclass
class Inspeccion:
    columnas: list[str]
    filas_muestra: list[list[str]]


def inspeccionar(datos: bytes, nombre_archivo: str) -> Inspeccion:
    """Lee encabezados y una muestra de filas SIN procesar el archivo."""
    tabla = leer_tabla(datos, nombre_archivo)
    muestra = [[f.get(c, "") for c in tabla.columnas] for f in tabla.filas[:_FILAS_MUESTRA]]
    return Inspeccion(columnas=tabla.columnas, filas_muestra=muestra)


@dataclass
class CandidataPlantilla:
    plantilla: PlantillaReporte
    faltantes: list[str]  # columnas esperadas (requeridas + llaves) ausentes del archivo
    extra: list[str]  # columnas del archivo que la plantilla no contempla
    calza: bool


def _esperadas(plantilla: PlantillaReporte) -> set[str]:
    req = {c.nombre for c in plantilla.columnas if c.requerida}
    return req | {plantilla.columna_pais, plantilla.columna_periodo}


def emparejar(db: Session, torre: Torre, columnas_archivo: list[str]) -> list[CandidataPlantilla]:
    """Compara los encabezados contra las plantillas de la torre.

    Una plantilla "calza" si todas sus columnas esperadas (requeridas + país +
    periodo) están en el archivo. Las candidatas con calce van primero; el resto se
    ordena por menor cantidad de faltantes (mejores candidatas para mapear).
    """
    presentes = set(columnas_archivo)
    candidatas: list[CandidataPlantilla] = []
    plantillas = db.scalars(select(PlantillaReporte).where(PlantillaReporte.torre == torre))
    for p in plantillas:
        esperadas = _esperadas(p)
        nombres = {c.nombre for c in p.columnas}
        faltantes = sorted(esperadas - presentes)
        extra = sorted(presentes - nombres - {p.columna_pais, p.columna_periodo})
        candidatas.append(
            CandidataPlantilla(plantilla=p, faltantes=faltantes, extra=extra, calza=not faltantes)
        )
    candidatas.sort(key=lambda c: (not c.calza, len(c.faltantes)))
    return candidatas


# --- Generación de identificadores SQL-seguros ----------------------------------------


def _slug(texto: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")
    if not s or not s[0].isalpha():
        s = f"v_{s}" if s else "vista"
    return s[:60]


def _vista_existe(db: Session, nombre: str) -> bool:
    return db.scalar(select(VistaCatalogo.id).where(VistaCatalogo.nombre == nombre)) is not None


def _plantilla_existe(db: Session, codigo: str) -> bool:
    return (
        db.scalar(select(PlantillaReporte.id).where(PlantillaReporte.codigo == codigo)) is not None
    )


def _vista_nombre_unico(db: Session, base: str) -> str:
    candidato, n = base, 2
    while _vista_existe(db, candidato):
        candidato, n = f"{base}_{n}", n + 1
    return candidato


def _plantilla_codigo_unico(db: Session, base: str) -> str:
    candidato, n = base, 2
    while _plantilla_existe(db, candidato):
        candidato, n = f"{base}_{n}", n + 1
    return candidato


# --- Creación de plantilla + vista 1:1 ------------------------------------------------


@dataclass
class PlantillaConVista:
    plantilla: PlantillaReporte
    vista: VistaCatalogo


def _sql_vista(codigo: str, columnas: list[ColumnaSpec]) -> str:
    cols = ", ".join(c.nombre for c in columnas)
    return f"SELECT {cols} FROM {codigo}"


def _columnas_descritas(
    columnas: list[ColumnaSpec], descripciones: dict[str, str], nombre_negocio: str
) -> list[ColumnaDescrita]:
    descritas: list[ColumnaDescrita] = []
    for c in columnas:
        desc = (descripciones.get(c.nombre) or "").strip()
        if not desc:
            # Genérica si se deja vacía (pero la UI invita a llenarla).
            desc = f"Columna '{c.nombre}' de {nombre_negocio}."
        descritas.append(ColumnaDescrita(nombre=c.nombre, descripcion=desc))
    return descritas


def crear_plantilla_con_vista(
    db: Session,
    torre: Torre,
    *,
    nombre_plantilla: str,
    frecuencia: Frecuencia,
    columnas: list[ColumnaSpec],
    columna_pais: str,
    columna_periodo: str,
    vista_nombre_negocio: str,
    vista_descripcion: str = "",
    descripciones_columnas: dict[str, str] | None = None,
) -> PlantillaConVista:
    """Crea la plantilla y, automáticamente, su vista 1:1. Todo en una transacción."""
    _validar_definicion(columnas, columna_pais, columna_periodo, vista_nombre_negocio)
    descripciones_columnas = descripciones_columnas or {}

    base = _slug(vista_nombre_negocio)
    vista_nombre = _vista_nombre_unico(db, base)
    codigo = _plantilla_codigo_unico(db, f"{torre.value.lower()}_{base}")

    plantilla = PlantillaReporte(
        codigo=codigo,
        nombre=nombre_plantilla.strip(),
        torre=torre,
        descripcion=vista_descripcion.strip(),
        frecuencia=frecuencia,
        columnas_json=[c.model_dump(mode="json") for c in columnas],
        columna_pais=columna_pais,
        columna_periodo=columna_periodo,
    )
    db.add(plantilla)
    db.flush()

    vista = VistaCatalogo(
        nombre=vista_nombre,
        titulo=vista_nombre_negocio.strip(),
        descripcion=vista_descripcion.strip(),
        torre=torre,
        plantilla_id=plantilla.id,
        sql=_sql_vista(codigo, columnas),
        columnas_json=[
            c.model_dump(mode="json")
            for c in _columnas_descritas(columnas, descripciones_columnas, vista_nombre_negocio)
        ],
    )
    db.add(vista)
    db.commit()
    db.refresh(plantilla)
    db.refresh(vista)
    return PlantillaConVista(plantilla=plantilla, vista=vista)


def _validar_definicion(
    columnas: list[ColumnaSpec],
    columna_pais: str,
    columna_periodo: str,
    vista_nombre_negocio: str,
) -> None:
    if not vista_nombre_negocio.strip():
        raise DefinicionInvalida("El nombre de negocio de la vista es obligatorio.")
    if not columnas:
        raise DefinicionInvalida("La plantilla necesita al menos una columna.")
    nombres = [c.nombre for c in columnas]
    for n in nombres:
        if not _IDENT.match(n):
            raise DefinicionInvalida(
                f"Nombre de columna no válido para SQL: '{n}'. Usa minúsculas, "
                "números y guion bajo, empezando por letra."
            )
    if len(nombres) != len(set(nombres)):
        raise DefinicionInvalida("Hay nombres de columna repetidos.")
    for etiqueta, llave in (("país", columna_pais), ("periodo", columna_periodo)):
        if llave not in nombres:
            raise DefinicionInvalida(
                f"La llave de {etiqueta} ('{llave}') debe ser una de las columnas definidas."
            )


# --- Edición gobernada ----------------------------------------------------------------


def impacto_edicion(db: Session, plantilla: PlantillaReporte) -> int:
    """Cuántas cargas existentes dependen de la plantilla (aviso de impacto)."""
    return (
        db.scalar(
            select(func.count())
            .select_from(CargaArchivo)
            .where(CargaArchivo.plantilla_id == plantilla.id)
        )
        or 0
    )


def vista_de_plantilla(db: Session, plantilla: PlantillaReporte) -> VistaCatalogo | None:
    return db.scalars(
        select(VistaCatalogo).where(VistaCatalogo.plantilla_id == plantilla.id)
    ).first()


def editar_plantilla(
    db: Session,
    plantilla: PlantillaReporte,
    *,
    nombre_plantilla: str,
    frecuencia: Frecuencia,
    columnas: list[ColumnaSpec],
    columna_pais: str,
    columna_periodo: str,
) -> PlantillaReporte:
    """Edita explícitamente el molde (solo admin). Re-sincroniza la vista 1:1.

    NO se llama desde el flujo de carga: cambiar el molde es un acto aparte. Las
    descripciones de negocio de la vista se conservan para las columnas que sigan
    existiendo; las nuevas reciben una descripción genérica.
    """
    _validar_definicion(columnas, columna_pais, columna_periodo, plantilla.nombre)
    plantilla.nombre = nombre_plantilla.strip()
    plantilla.frecuencia = frecuencia
    plantilla.columnas_json = [c.model_dump(mode="json") for c in columnas]
    plantilla.columna_pais = columna_pais
    plantilla.columna_periodo = columna_periodo

    vista = vista_de_plantilla(db, plantilla)
    if vista is not None:
        previas = {c.nombre: c.descripcion for c in vista.columnas}
        vista.sql = _sql_vista(plantilla.codigo, columnas)
        vista.columnas_json = [
            ColumnaDescrita(
                nombre=c.nombre,
                descripcion=previas.get(c.nombre) or f"Columna '{c.nombre}' de {vista.titulo}.",
            ).model_dump(mode="json")
            for c in columnas
        ]
    db.commit()
    db.refresh(plantilla)
    return plantilla


def editar_vista(
    db: Session,
    vista: VistaCatalogo,
    *,
    titulo: str,
    descripcion: str,
    descripciones_columnas: dict[str, str] | None = None,
) -> VistaCatalogo:
    """Edita el nombre de negocio y las descripciones de la vista (admin/uploader)."""
    if not titulo.strip():
        raise DefinicionInvalida("El nombre de negocio de la vista es obligatorio.")
    descripciones_columnas = descripciones_columnas or {}
    vista.titulo = titulo.strip()
    vista.descripcion = descripcion.strip()
    vista.columnas_json = [
        ColumnaDescrita(
            nombre=c.nombre,
            descripcion=(descripciones_columnas.get(c.nombre) or c.descripcion or "").strip()
            or f"Columna '{c.nombre}' de {titulo.strip()}.",
        ).model_dump(mode="json")
        for c in vista.columnas
    ]
    db.commit()
    db.refresh(vista)
    return vista


# --- Mapeo de carga a plantilla -------------------------------------------------------


def aplicar_mapeo(tabla: Tabla, mapeo: dict[str, str]) -> Tabla:
    """Acomoda la tabla del archivo a los nombres de la plantilla SIN tocar el molde.

    ``mapeo`` = {columna_esperada: columna_en_el_archivo}. Renombra (copia) las
    columnas del archivo a los nombres que la plantilla espera. No altera la
    plantilla: solo transforma los datos entrantes.
    """
    if not mapeo:
        return tabla
    columnas = list(tabla.columnas)
    for esperada in mapeo:
        if esperada not in columnas:
            columnas.append(esperada)
    filas: list[dict[str, str]] = []
    for fila in tabla.filas:
        nueva = dict(fila)
        for esperada, en_archivo in mapeo.items():
            if en_archivo in fila:
                nueva[esperada] = fila[en_archivo]
        filas.append(nueva)
    return Tabla(columnas=columnas, filas=filas)
