import type { Celda, EstadoFrescura } from "@/lib/types";

// Heurística: una celda es "numérica" (alineada a la derecha, tabular) si es un
// número o un string que parsea como número. Los montos DECIMAL llegan como string
// y se muestran TAL CUAL (sin convertir a float, para no perder centavos).
export function esNumerica(valor: Celda): boolean {
  if (typeof valor === "number") return true;
  if (typeof valor === "string" && valor.trim() !== "") {
    return !Number.isNaN(Number(valor));
  }
  return false;
}

export function mostrarCelda(valor: Celda): string {
  if (valor === null) return "—";
  return String(valor);
}

export const ETIQUETA_FRESCURA: Record<EstadoFrescura, string> = {
  al_dia: "Al día",
  advertencia: "Atención",
  vencido: "Vencido",
  sin_datos: "Sin datos",
};

export function saludo(): string {
  const h = new Date().getHours();
  if (h < 12) return "Buenos días";
  if (h < 19) return "Buenas tardes";
  return "Buenas noches";
}
