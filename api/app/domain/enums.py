"""Enumeraciones del dominio: torres de servicio, países LATAM y roles.

El RBAC de PowerAI es bidimensional (torre × país) y se diseña desde el día 1
(ver ADR-0001 y sección 7 de la arquitectura). Estos enums son la fuente única
de verdad para las dimensiones de autorización.
"""

from enum import StrEnum


class Torre(StrEnum):
    """Torres de servicio del SSC Finanzas LATAM."""

    OTC = "OTC"  # Order to Cash
    PTP = "PTP"  # Procure to Pay
    RTR = "RTR"  # Record to Report
    QCI = "QCI"  # Quality / Control Interno
    CARE = "CARE"  # Customer Care
    HTR = "HTR"  # Hire to Retire


class Pais(StrEnum):
    """Países LATAM atendidos por el SSC (ISO 3166-1 alpha-2).

    Conjunto provisional de 15 países; se ajusta con el alta real de cada país.
    """

    AR = "AR"  # Argentina
    BO = "BO"  # Bolivia
    BR = "BR"  # Brasil
    CL = "CL"  # Chile
    CO = "CO"  # Colombia
    CR = "CR"  # Costa Rica
    EC = "EC"  # Ecuador
    GT = "GT"  # Guatemala
    HN = "HN"  # Honduras
    MX = "MX"  # México
    NI = "NI"  # Nicaragua
    PA = "PA"  # Panamá
    PE = "PE"  # Perú
    PY = "PY"  # Paraguay
    UY = "UY"  # Uruguay


class Rol(StrEnum):
    """Roles por asignación torre × país.

    - UPLOADER: carga reportes de la torre.
    - CONSULTA: consulta datos y usa el chat analítico (solo lectura).
    - ADMIN: administra la torre (gestión de plantillas, catálogo, permisos).
    """

    UPLOADER = "uploader"
    CONSULTA = "consulta"
    ADMIN = "admin"


# Comodín de país: un grant con país "*" aplica a todos los países de la torre.
PAIS_TODOS = "*"


class Frecuencia(StrEnum):
    """Frecuencia esperada de carga de una plantilla (insumo de la frescura)."""

    DIARIA = "diaria"
    SEMANAL = "semanal"
    QUINCENAL = "quincenal"
    MENSUAL = "mensual"


# Días de holgura por frecuencia, usados para calcular el estado de frescura.
DIAS_POR_FRECUENCIA: dict[Frecuencia, int] = {
    Frecuencia.DIARIA: 1,
    Frecuencia.SEMANAL: 7,
    Frecuencia.QUINCENAL: 15,
    Frecuencia.MENSUAL: 30,
}


class TipoColumna(StrEnum):
    """Tipos soportados para las columnas de una plantilla."""

    TEXTO = "texto"
    ENTERO = "entero"
    DECIMAL = "decimal"
    FECHA = "fecha"


class EstadoCarga(StrEnum):
    """Ciclo de vida de una carga de archivo."""

    RECIBIDA = "recibida"
    PROCESANDO = "procesando"
    DISPONIBLE = "disponible"
    FALLIDA = "fallida"


class EstadoExperto(StrEnum):
    """Ciclo de vida de una configuración del Experto de una torre (M10).

    - BORRADOR: configuración editable que aún no pasó la validación por evals.
    - ACTIVO: configuración vigente que el agente usa (pasó el umbral de evals).
    - ARCHIVADO: configuración que fue activa y quedó reemplazada (rollback posible).
    """

    BORRADOR = "borrador"
    ACTIVO = "activo"
    ARCHIVADO = "archivado"


class EstadoFrescura(StrEnum):
    """Estado de frescura de un dataset (badge verde/ámbar/rojo del design system)."""

    AL_DIA = "al_dia"
    ADVERTENCIA = "advertencia"
    VENCIDO = "vencido"
    SIN_DATOS = "sin_datos"
