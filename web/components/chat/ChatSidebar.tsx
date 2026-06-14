"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useUsuario } from "@/context/UsuarioContext";
import { api } from "@/lib/api";
import type { Conversacion } from "@/lib/types";

// Sidebar de conversaciones (fondo surface-200). Ítem activo con borde izquierdo
// brand-200. "Nueva conversación" lleva al home.
export function ChatSidebar({ activoId }: { activoId?: string }) {
  const { email } = useUsuario();
  const [convs, setConvs] = useState<Conversacion[]>([]);

  useEffect(() => {
    let activo = true;
    api
      .get<Conversacion[]>("/conversaciones")
      .then((c) => activo && setConvs(c))
      .catch(() => activo && setConvs([]));
    return () => {
      activo = false;
    };
  }, [email, activoId]);

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-neutral-100 bg-surface-200">
      <div className="p-3">
        <Link
          href="/"
          className="flex items-center justify-center gap-2 rounded-pill bg-brand-600 px-3 py-2 text-sm font-medium text-white"
        >
          <Plus className="h-4 w-4" aria-hidden />
          Nueva conversación
        </Link>
      </div>
      <nav aria-label="Conversaciones" className="flex-1 overflow-y-auto px-2 pb-3">
        <h2 className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
          Historial
        </h2>
        {convs.length === 0 && (
          <p className="px-2 py-2 text-[12px] text-neutral-500">Sin conversaciones aún.</p>
        )}
        {convs.map((c) => {
          const activo = c.id === activoId;
          return (
            <Link
              key={c.id}
              href={`/chat/${c.id}`}
              aria-current={activo ? "page" : undefined}
              className={`block truncate rounded-md px-2 py-2 text-[13px] ${
                activo
                  ? "border-l-2 border-brand-200 bg-white font-medium text-brand-800"
                  : "text-neutral-700 hover:bg-white/60"
              }`}
            >
              {c.titulo || "Conversación"}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
