"use client";

import { useEffect, useState } from "react";
import { BadgeFrescura } from "@/components/BadgeFrescura";
import { useUsuario } from "@/context/UsuarioContext";
import { api } from "@/lib/api";
import type { Frescura, Me } from "@/lib/types";

// Rail derecho de fuentes activas (240px): badges de frescura por dataset y el
// alcance del usuario ("Filtrado: MX · CO").
export function SourcesRail() {
  const { email } = useUsuario();
  const [frescura, setFrescura] = useState<Frescura[]>([]);
  const [alcance, setAlcance] = useState<string>("");

  useEffect(() => {
    let activo = true;
    api
      .get<Frescura[]>("/catalogo/frescura?torre=OTC")
      .then((f) => activo && setFrescura(f))
      .catch(() => activo && setFrescura([]));
    api
      .get<Me>("/me")
      .then((m) => {
        if (!activo) return;
        const paises = [...new Set(m.torres.flatMap((t) => t.paises))];
        setAlcance(paises.join(" · "));
      })
      .catch(() => activo && setAlcance(""));
    return () => {
      activo = false;
    };
  }, [email]);

  return (
    <aside className="hidden w-60 shrink-0 border-l border-neutral-100 bg-white p-4 lg:block">
      <h2 className="text-[12px] font-semibold uppercase tracking-wide text-neutral-400">
        Fuentes activas
      </h2>
      {alcance && (
        <p className="mt-1 text-[11px] text-neutral-500">Filtrado: {alcance}</p>
      )}
      <ul className="mt-3 space-y-3">
        {frescura.length === 0 && (
          <li className="text-[12px] text-neutral-500">Sin datasets disponibles.</li>
        )}
        {frescura.map((f, i) => (
          <li key={i} className="text-[12px]">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-neutral-700">{f.plantilla_nombre}</span>
              <BadgeFrescura estado={f.estado} />
            </div>
            <span className="text-[11px] text-neutral-400">{f.pais}</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
