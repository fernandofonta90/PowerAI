// Badge de frescura reutilizable (panel de fuentes, home, citación).
// El color comunica estado; cada estado lleva icono (accesibilidad: el color
// nunca es el único portador de significado).

import { AlertTriangle, CheckCircle2, CircleOff, XCircle } from "lucide-react";
import type { EstadoFrescura } from "@/lib/types";
import { ETIQUETA_FRESCURA } from "@/lib/format";

const ESTILO: Record<EstadoFrescura, { clase: string; Icono: typeof CheckCircle2 }> = {
  al_dia: { clase: "bg-success-600/10 text-success-700", Icono: CheckCircle2 },
  advertencia: { clase: "bg-warning-600/10 text-warning-700", Icono: AlertTriangle },
  vencido: { clase: "bg-danger-600/10 text-danger-700", Icono: XCircle },
  sin_datos: { clase: "bg-neutral-100 text-neutral-500", Icono: CircleOff },
};

export function BadgeFrescura({ estado }: { estado: EstadoFrescura }) {
  const { clase, Icono } = ESTILO[estado];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-pill px-2 py-0.5 text-[11px] font-medium ${clase}`}
    >
      <Icono className="h-3 w-3" aria-hidden />
      {ETIQUETA_FRESCURA[estado]}
    </span>
  );
}
