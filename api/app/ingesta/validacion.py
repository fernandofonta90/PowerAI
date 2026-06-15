"""Validación de una tabla cargada contra el esquema de su plantilla.

Devuelve una lista de mensajes de error claros (vacía = válida). Cubre: columnas
faltantes, tipos inválidos y verificación de país/periodo declarados contra el
contenido del archivo (decisión vinculante del arquitecto).
"""

from app.domain.columnas import ColumnaSpec
from app.domain.enums import TipoColumna
from app.ingesta.coercion import ValorInvalido, coercer
from app.ingesta.fechas import detectar_formato_fecha, parsear_fecha
from app.ingesta.lector import Tabla

# Máximo de errores de tipo a reportar por columna (evita avalanchas).
_MAX_ERRORES_TIPO = 3


def _validar_columna(col: ColumnaSpec, tabla: Tabla, errores: list[str]) -> None:
    """Valida los valores de una columna por su tipo (fechas: formato por columna)."""
    crudos = [fila.get(col.etiqueta, "") for fila in tabla.filas]
    formato = detectar_formato_fecha(crudos) if col.tipo is TipoColumna.FECHA else None
    if col.tipo is TipoColumna.FECHA and formato is None and any(v.strip() for v in crudos):
        errores.append(
            f"Columna '{col.etiqueta}': no se pudo determinar el formato de fecha "
            "(¿ambiguo o mezclado?). Revísalo o declárala como texto."
        )
        return
    problemas = 0
    for i, valor in enumerate(crudos, start=1):
        if valor == "":
            if col.requerida:
                errores.append(f"Columna '{col.etiqueta}', fila {i}: valor requerido vacío.")
                problemas += 1
        else:
            try:
                if col.tipo is TipoColumna.FECHA:
                    parsear_fecha(valor, formato or "")
                else:
                    coercer(valor, col.tipo)
            except ValorInvalido as exc:
                errores.append(f"Columna '{col.etiqueta}', fila {i}: {exc}.")
                problemas += 1
        if problemas >= _MAX_ERRORES_TIPO:
            break


def validar(
    tabla: Tabla,
    columnas: list[ColumnaSpec],
    columna_pais: str | None,
    columna_periodo: str | None,
    pais_declarado: str,
    periodo_declarado: str,
) -> list[str]:
    """Valida ``tabla`` contra la plantilla. Lista de errores (vacía si es válida).

    ``columna_pais`` y ``columna_periodo`` son opcionales: si son None, ese dato no
    viene en una columna (se declaró al cargar y aplica a todo el archivo), así que
    no se exige ni se verifica su contenido.
    """
    errores: list[str] = []
    presentes = set(tabla.columnas)

    # El archivo trae los encabezados originales (etiquetas): se valida por etiqueta.
    # 1. Columnas requeridas presentes.
    faltantes = [c.etiqueta for c in columnas if c.requerida and c.etiqueta not in presentes]
    for nombre in faltantes:
        errores.append(f"Falta la columna requerida: '{nombre}'.")

    # 2. Columnas de país/periodo presentes SOLO si la plantilla las define (opcionales).
    estructurales = [("país", columna_pais), ("periodo", columna_periodo)]
    for etiqueta, nombre_col in estructurales:
        if nombre_col and nombre_col not in presentes:
            errores.append(f"Falta la columna de {etiqueta}: '{nombre_col}'.")

    # Si faltan columnas estructurales no seguimos con validación de contenido.
    if errores:
        return errores

    # 3. Tipos de cada columna declarada presente (por etiqueta = encabezado real).
    for col in columnas:
        if col.etiqueta in presentes:
            _validar_columna(col, tabla, errores)

    # 4. Verificación de país declarado vs contenido (solo si hay columna de país).
    if columna_pais:
        paises = {f.get(columna_pais, "").strip() for f in tabla.filas}
        paises.discard("")
        distintos_pais = paises - {pais_declarado}
        if distintos_pais:
            errores.append(
                f"El país declarado ('{pais_declarado}') no coincide con el contenido: "
                f"se encontró {sorted(distintos_pais)}."
            )

    # 5. Verificación de periodo declarado vs contenido (solo si hay columna de periodo).
    if columna_periodo:
        periodos = {f.get(columna_periodo, "").strip() for f in tabla.filas}
        periodos.discard("")
        distintos_periodo = periodos - {periodo_declarado}
        if distintos_periodo:
            errores.append(
                f"El periodo declarado ('{periodo_declarado}') no coincide con el "
                f"contenido: se encontró {sorted(distintos_periodo)}."
            )

    return errores
