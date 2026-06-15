"""Validación de una tabla cargada contra el esquema de su plantilla.

Devuelve una lista de mensajes de error claros (vacía = válida). Cubre: columnas
faltantes, tipos inválidos y verificación de país/periodo declarados contra el
contenido del archivo (decisión vinculante del arquitecto).
"""

from app.domain.columnas import ColumnaSpec
from app.ingesta.coercion import ValorInvalido, coercer
from app.ingesta.lector import Tabla

# Máximo de errores de tipo a reportar por columna (evita avalanchas).
_MAX_ERRORES_TIPO = 3


def validar(
    tabla: Tabla,
    columnas: list[ColumnaSpec],
    columna_pais: str,
    columna_periodo: str | None,
    pais_declarado: str,
    periodo_declarado: str,
) -> list[str]:
    """Valida ``tabla`` contra la plantilla. Lista de errores (vacía si es válida).

    ``columna_periodo`` es opcional: si es None, el periodo no viene en una columna
    (se declaró al cargar y aplica a todo el archivo), así que no se exige ni se
    verifica su contenido.
    """
    errores: list[str] = []
    presentes = set(tabla.columnas)

    # El archivo trae los encabezados originales (etiquetas): se valida por etiqueta.
    # 1. Columnas requeridas presentes.
    faltantes = [c.etiqueta for c in columnas if c.requerida and c.etiqueta not in presentes]
    for nombre in faltantes:
        errores.append(f"Falta la columna requerida: '{nombre}'.")

    # 2. Columna de país presente (estructural). La de periodo solo si la plantilla
    #    la define (es opcional).
    estructurales = [("país", columna_pais)]
    if columna_periodo:
        estructurales.append(("periodo", columna_periodo))
    for etiqueta, nombre_col in estructurales:
        if nombre_col not in presentes:
            errores.append(f"Falta la columna de {etiqueta}: '{nombre_col}'.")

    # Si faltan columnas estructurales no seguimos con validación de contenido.
    if errores:
        return errores

    # 3. Tipos de cada columna declarada presente (por etiqueta = encabezado real).
    for col in columnas:
        if col.etiqueta not in presentes:
            continue
        problemas = 0
        for i, fila in enumerate(tabla.filas, start=1):
            valor = fila.get(col.etiqueta, "")
            if valor == "":
                if col.requerida:
                    errores.append(f"Columna '{col.etiqueta}', fila {i}: valor requerido vacío.")
                    problemas += 1
            else:
                try:
                    coercer(valor, col.tipo)
                except ValorInvalido as exc:
                    errores.append(f"Columna '{col.etiqueta}', fila {i}: {exc}.")
                    problemas += 1
            if problemas >= _MAX_ERRORES_TIPO:
                break

    # 4. Verificación de país declarado vs contenido.
    paises = {f.get(columna_pais, "").strip() for f in tabla.filas}
    paises.discard("")
    distintos_pais = paises - {pais_declarado}
    if distintos_pais:
        errores.append(
            f"El país declarado ('{pais_declarado}') no coincide con el contenido: "
            f"se encontró {sorted(distintos_pais)}."
        )

    # 5. Verificación de periodo declarado vs contenido (solo si hay columna de
    #    periodo; si no, el periodo declarado al cargar aplica a todo el archivo).
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
