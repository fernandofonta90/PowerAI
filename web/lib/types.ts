// Tipos del contrato de la API de PowerAI (M2–M4).

export type EstadoFrescura = "al_dia" | "advertencia" | "vencido" | "sin_datos";

export type TorreAccesible = { torre: string; paises: string[] };
export type Me = { email: string; nombre: string; torres: TorreAccesible[] };

export type Frescura = {
  plantilla_codigo: string;
  plantilla_nombre: string;
  pais: string;
  ultima_actualizacion: string | null;
  estado: EstadoFrescura;
};

export type Plantilla = {
  codigo: string;
  nombre: string;
  torre: string;
  frecuencia: string;
};

export type Conversacion = { id: string; titulo: string; creado_en: string };

export type Fuente = {
  archivo: string;
  version: number;
  fecha_carga: string;
  responsable: string;
  frescura: EstadoFrescura;
  plantilla: string;
  pais: string;
  periodo: string;
};

export type Citacion = {
  fuentes: Fuente[];
  sql_ejecutado_ids: string[];
  vistas_usadas: string[];
};

// Los montos DECIMAL llegan como string para preservar la exactitud al centavo.
export type Celda = string | number | boolean | null;
export type DatosTabulares = { columnas: string[]; filas: Celda[][] };

export type Mensaje = {
  id: string;
  rol: string;
  contenido: string;
  citacion: Citacion | null;
  creado_en: string;
};

export type ConversacionDetalle = Conversacion & { mensajes: Mensaje[] };

export type RespuestaChat = {
  mensaje_id: string;
  texto: string;
  datos_tabulares: DatosTabulares | null;
  citacion: Citacion;
  uso?: { entrada: number; salida: number };
};

// --- Dashboards (M8) ---

export type DashboardMeta = {
  id: string;
  nombre: string;
  torre: string;
  creado_en: string;
};

export type VisualRenderizado = {
  tipo: "kpi" | "tabla" | "barras" | "lineas" | "distribucion";
  titulo: string;
  columna_valor: string | null;
  eje_x: string | null;
  eje_y: string | null;
  formato: "entero" | "decimal" | "texto";
  columnas: string[];
  filas: Celda[][];
  error: string | null;
};

export type DashboardRenderizado = {
  id: string;
  nombre: string;
  torre: string;
  filtros: Record<string, unknown>;
  titulo: string;
  visuales: VisualRenderizado[];
};

export type GenerarDashboardResponse = {
  spec: Record<string, unknown> | null;
  mensaje: string;
};
