// Burbuja de chat. Usuario: a la derecha en brand-100. Asistente: a la izquierda
// sin burbuja, con avatar sparkle, más tabla de datos y bloque de citación.

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

export function MessageBubble({ item }: { item: ItemMensaje }) {
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
      </div>
    </div>
  );
}
