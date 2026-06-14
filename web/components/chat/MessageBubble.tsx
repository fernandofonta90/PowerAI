// Burbuja de chat. Usuario: a la derecha en brand-100. Asistente: a la izquierda
// sin burbuja, con avatar sparkle, más tabla de datos y bloque de citación.

import { LayoutDashboard } from "lucide-react";
import { CitationBlock } from "@/components/chat/CitationBlock";
import { DataTable } from "@/components/chat/DataTable";
import { Sparkle } from "@/components/Sparkle";
import type { Citacion, DatosTabulares } from "@/lib/types";

export type ItemMensaje = {
  rol: string;
  contenido: string;
  citacion?: Citacion | null;
  datos?: DatosTabulares | null;
};

export function MessageBubble({
  item,
  onGenerarDashboard,
  generando,
}: {
  item: ItemMensaje;
  onGenerarDashboard?: () => void;
  generando?: boolean;
}) {
  if (item.rol === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-brand-100 px-4 py-2 text-[14px] text-neutral-900">
          {item.contenido}
        </div>
      </div>
    );
  }
  return (
    <div className="flex gap-3">
      <div className="mt-1 shrink-0 text-brand-600" aria-hidden>
        <Sparkle className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="whitespace-pre-wrap text-[14px] text-neutral-900">{item.contenido}</p>
        {item.datos && <DataTable datos={item.datos} />}
        {item.citacion && <CitationBlock citacion={item.citacion} />}
        {item.datos && onGenerarDashboard && (
          <button
            type="button"
            onClick={onGenerarDashboard}
            disabled={generando}
            className="mt-3 inline-flex items-center gap-1.5 rounded-pill border border-brand-200 bg-brand-50 px-3 py-1.5 text-[12px] text-brand-800 disabled:opacity-50"
          >
            <LayoutDashboard className="h-3.5 w-3.5" aria-hidden />
            {generando ? "Generando dashboard…" : "Generar dashboard de esto"}
          </button>
        )}
      </div>
    </div>
  );
}
