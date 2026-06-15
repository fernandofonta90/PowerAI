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
import unicodedata
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.schemas import UsuarioAutenticado
from app.domain.columnas import ColumnaDescrita, ColumnaSpec
from app.domain.enums import Frecuencia, Rol, TipoColumna, Torre
from app.ingesta.coercion import ValorInvalido, coercer
from app.ingesta.fechas import detectar_formato_fecha
from app.ingesta.lector import Tabla, leer_tabla
from app.models.carga import CargaArchivo
from app.models.plantilla import PlantillaReporte
from app.models.vista import VistaCatalogo

_FILAS_MUESTRA = 5
_FILAS_INFERENCIA = 50
_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")
# Nombres que sugieren un identificador (preferir texto aunque parezcan números:
# suelen tener ceros a la izquierda o prefijos).
_ID_LIKE = re.compile(r"(?:^|_)(id|number|nro|num|folio|code|codigo|clave|ref)(?:$|_)", re.I)


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


def _todos_parsean(valores: list[str], tipo: TipoColumna) -> bool:
    """True si hay al menos un valor y TODOS parsean como ``tipo``."""
    visto = False
    for v in valores:
        try:
            coercer(v, tipo)
        except ValorInvalido:
            return False
        visto = True
    return visto


def _tiene_cero_izquierda(v: str) -> bool:
    cuerpo = v.lstrip("+-")
    return len(cuerpo) > 1 and cuerpo[0] == "0"


def inferir_tipo(valores: list[str], nombre: str) -> TipoColumna:
    """Sugiere el tipo de una columna a partir de una muestra de valores.

    SUGIERE, no impone (el humano confirma). Reglas:
    - fecha si la columna tiene un formato de fecha reconocible y no ambiguo
      (ISO, DD/MM o MM/DD detectado por sus valores); una fecha ambigua va a texto;
    - si todos son numéricos: decimal si alguno trae parte decimal; si todos son
      enteros, ENTERO salvo que parezca identificador (nombre tipo id/number o con
      ceros a la izquierda) → TEXTO, porque esos "números" no se operan;
    - texto en cualquier otro caso.
    """
    vals = [v.strip() for v in valores if v and v.strip()]
    if not vals:
        return TipoColumna.TEXTO
    if detectar_formato_fecha(vals) is not None:
        return TipoColumna.FECHA
    if _todos_parsean(vals, TipoColumna.DECIMAL):
        if _todos_parsean(vals, TipoColumna.ENTERO):
            if _ID_LIKE.search(nombre) or any(_tiene_cero_izquierda(v) for v in vals):
                return TipoColumna.TEXTO
            return TipoColumna.ENTERO
        return TipoColumna.DECIMAL
    return TipoColumna.TEXTO


@dataclass
class Inspeccion:
    columnas: list[str]
    filas_muestra: list[list[str]]
    # Tipo sugerido por columna (la UI lo pre-selecciona; el usuario lo confirma).
    tipos_sugeridos: dict[str, TipoColumna]


def inspeccionar(datos: bytes, nombre_archivo: str) -> Inspeccion:
    """Lee encabezados, una muestra de filas y sugiere el tipo de cada columna."""
    tabla = leer_tabla(datos, nombre_archivo)
    muestra = [[f.get(c, "") for c in tabla.columnas] for f in tabla.filas[:_FILAS_MUESTRA]]
    n = min(len(tabla.filas), _FILAS_INFERENCIA)
    tipos = {
        c: inferir_tipo([tabla.filas[i].get(c, "") for i in range(n)], c) for c in tabla.columnas
    }
    return Inspeccion(columnas=tabla.columnas, filas_muestra=muestra, tipos_sugeridos=tipos)


@dataclass
class CandidataPlantilla:
    plantilla: PlantillaReporte
    faltantes: list[str]  # columnas esperadas (requeridas + llaves) ausentes del archivo
    extra: list[str]  # columnas del archivo que la plantilla no contempla
    calza: bool


def _esperadas(plantilla: PlantillaReporte) -> set[str]:
    # Por ETIQUETA (encabezado real): el emparejamiento compara contra los
    # encabezados del archivo, no contra los nombres técnicos (slugs).
    req = {c.etiqueta for c in plantilla.columnas if c.requerida}
    if plantilla.columna_pais:
        req.add(plantilla.columna_pais)
    if plantilla.columna_periodo:
        req.add(plantilla.columna_periodo)
    return req


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
        # Conocidas por la plantilla = etiquetas (encabezados reales) + llaves.
        conocidas = {c.etiqueta for c in p.columnas}
        conocidas |= {k for k in (p.columna_pais, p.columna_periodo) if k}
        faltantes = sorted(esperadas - presentes)
        extra = sorted(presentes - conocidas)
        candidatas.append(
            CandidataPlantilla(plantilla=p, faltantes=faltantes, extra=extra, calza=not faltantes)
        )
    candidatas.sort(key=lambda c: (not c.calza, len(c.faltantes)))
    return candidatas


# --- Generación de identificadores SQL-seguros ----------------------------------------


def _sin_acentos(texto: str) -> str:
    """Pliega acentos/diacríticos a ASCII (Número → Numero, País → Pais)."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _slug(texto: str, prefijo: str = "col") -> str:
    """Convierte un texto (encabezado) en un identificador SQL-seguro.

    Minúsculas, sin acentos, espacios/símbolos → guion bajo, empezando por letra.
    "Número Documento" → numero_documento; "Importe S/" → importe_s; "RUC" → ruc.
    """
    s = re.sub(r"[^a-z0-9]+", "_", _sin_acentos(texto).lower()).strip("_")
    if not s or not s[0].isalpha():
        s = f"{prefijo}_{s}".rstrip("_") if s else prefijo
    return s[:60]


def slugificar_columnas(columnas: list[ColumnaSpec]) -> tuple[list[ColumnaSpec], list[str]]:
    """Genera el nombre técnico (slug) de cada columna desde su encabezado.

    El encabezado original (``etiqueta``) se conserva como etiqueta de negocio. Si
    dos encabezados slugifican igual, se desambigua con sufijo numérico y se reporta
    el aviso. Devuelve (columnas con nombre=slug y etiqueta=encabezado, avisos).
    """
    usados: set[str] = set()
    resultado: list[ColumnaSpec] = []
    avisos: list[str] = []
    for col in columnas:
        encabezado = col.etiqueta or col.nombre
        base = _slug(encabezado)
        slug, n = base, 2
        while slug in usados:
            slug, n = f"{base}_{n}", n + 1
        if slug != base:
            avisos.append(
                f"El encabezado '{encabezado}' genera el mismo nombre técnico que otro; "
                f"se usó '{slug}' para desambiguar."
            )
        usados.add(slug)
        resultado.append(
            ColumnaSpec(
                nombre=slug,
                tipo=col.tipo,
                requerida=col.requerida,
                descripcion=col.descripcion,
                etiqueta=encabezado,
            )
        )
    return resultado, avisos


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
    avisos: list[str] = field(default_factory=list)


def _sql_vista(codigo: str, columnas: list[ColumnaSpec]) -> str:
    cols = ", ".join(c.nombre for c in columnas)
    return f"SELECT {cols} FROM {codigo}"


def _columnas_descritas(
    columnas: list[ColumnaSpec], descripciones: dict[str, str], nombre_negocio: str
) -> list[ColumnaDescrita]:
    descritas: list[ColumnaDescrita] = []
    for c in columnas:
        # Las descripciones llegan indexadas por el encabezado (etiqueta) que ve
        # el usuario; la vista guarda el nombre técnico (slug).
        desc = (descripciones.get(c.etiqueta) or descripciones.get(c.nombre) or "").strip()
        if not desc:
            # Genérica si se deja vacía (pero la UI invita a llenarla).
            desc = f"Columna '{c.etiqueta}' de {nombre_negocio}."
        descritas.append(ColumnaDescrita(nombre=c.nombre, descripcion=desc))
    return descritas


def crear_plantilla_con_vista(
    db: Session,
    torre: Torre,
    *,
    nombre_plantilla: str,
    frecuencia: Frecuencia,
    columnas: list[ColumnaSpec],
    columna_pais: str | None,
    columna_periodo: str | None,
    vista_nombre_negocio: str,
    vista_descripcion: str = "",
    descripciones_columnas: dict[str, str] | None = None,
) -> PlantillaConVista:
    """Crea la plantilla y, automáticamente, su vista 1:1. Todo en una transacción.

    ``columna_periodo`` es opcional: si no hay columna de periodo, el periodo se
    declara al cargar (campo del formulario) y aplica a todo el archivo.
    """
    columna_periodo = columna_periodo or None
    # Genera nombres técnicos SQL-seguros desde los encabezados; conserva el
    # encabezado como etiqueta de negocio. El país/periodo se siguen identificando
    # por su encabezado (etiqueta), que es lo que la validación lee del archivo.
    columnas, avisos = slugificar_columnas(columnas)
    _validar_definicion(columnas, columna_pais, columna_periodo, vista_nombre_negocio)
    descripciones_columnas = descripciones_columnas or {}

    base = _slug(vista_nombre_negocio, prefijo="vista")
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
    return PlantillaConVista(plantilla=plantilla, vista=vista, avisos=avisos)


def _validar_definicion(
    columnas: list[ColumnaSpec],
    columna_pais: str | None,
    columna_periodo: str | None,
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
    # Las llaves se identifican por encabezado (etiqueta) o por nombre técnico, para
    # servir tanto al flujo de creación (etiqueta) como a la edición (slug).
    identificadores = set(nombres) | {c.etiqueta for c in columnas}
    # País y periodo son OPCIONALES (pueden declararse al cargar). Si se indican,
    # deben referir a una columna definida (por nombre técnico o por encabezado).
    if columna_pais and columna_pais not in identificadores:
        raise DefinicionInvalida(
            f"La llave de país ('{columna_pais}') debe ser una de las columnas definidas."
        )
    if columna_periodo and columna_periodo not in identificadores:
        raise DefinicionInvalida(
            f"La llave de periodo ('{columna_periodo}') debe ser una de las columnas definidas."
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
    columna_pais: str | None,
    columna_periodo: str | None,
) -> PlantillaReporte:
    """Edita explícitamente el molde (solo admin). Re-sincroniza la vista 1:1.

    NO se llama desde el flujo de carga: cambiar el molde es un acto aparte. Las
    descripciones de negocio de la vista se conservan para las columnas que sigan
    existiendo; las nuevas reciben una descripción genérica.
    """
    columna_periodo = columna_periodo or None
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
    """Edita el nombre de negocio y las descripciones de la vista.

    El RBAC (solo admin) lo aplica el endpoint: editar lo establecido es tan
    sensible como el molde, porque estas descripciones guían al experto.
    """
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
