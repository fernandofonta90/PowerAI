"use client";

import { Bell, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { BadgeFrescura } from "@/components/BadgeFrescura";
import { Sparkle } from "@/components/Sparkle";
import { useUsuario } from "@/context/UsuarioContext";
import { api } from "@/lib/api";
import type { Frescura } from "@/lib/types";
import { buscarUsuario } from "@/lib/usuarios";

// Grid de 3 tarjetas del home (existe desde Fase 1 aunque dos estén vacías).
export function ContextGrid() {
  const { email } = useUsuario();
  const [fuentes, setFuentes] = useState<Frescura[]>([]);
  const puedeCargar = buscarUsuario(email)?.puedeCargar ?? false;

  useEffect(() => {
    let activo = true;
    api
      .get<Frescura[]>("/catalogo/frescura?torre=OTC")
      .then((f) => activo && setFuentes(f))
      .catch(() => activo && setFuentes([]));
    return () => {
      activo = false;
    };
  }, [email]);

  return (
    <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
      <Tarjeta
        titulo="Fuentes de mi torre"
        accion={
          puedeCargar ? (
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-pill border border-neutral-200 px-2 py-1 text-[11px] text-brand-800"
            >
              <Upload className="h-3 w-3" aria-hidden />
              Cargar
            </button>
          ) : null
        }
      >
        {fuentes.length === 0 ? (
          <Vacio texto="Aún no hay fuentes cargadas." />
        ) : (
          <ul className="space-y-2">
            {fuentes.map((f, i) => (
              <li key={i} className="flex items-center justify-between gap-2 text-[12px]">
                <span className="truncate text-neutral-700">
                  {f.plantilla_nombre} · {f.pais}
                </span>
                <BadgeFrescura estado={f.estado} />
              </li>
            ))}
          </ul>
        )}
      </Tarjeta>

      <Tarjeta
        titulo="Mis dashboards"
        etiqueta={<Sparkle className="h-3.5 w-3.5 text-brand-600" title="Generado por IA" />}
      >
        <Vacio texto="Disponible próximamente." />
      </Tarjeta>

      <Tarjeta titulo="Alertas recientes" etiqueta={<Bell className="h-3.5 w-3.5 text-neutral-400" />}>
        <Vacio texto="Disponible próximamente." />
      </Tarjeta>
    </div>
  );
}

function Tarjeta({
  titulo,
  accion,
  etiqueta,
  children,
}: {
  titulo: string;
  accion?: React.ReactNode;
  etiqueta?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-neutral-100 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-[13px] font-medium text-neutral-700">
          {titulo}
          {etiqueta}
        </h3>
        {accion}
      </div>
      {children}
    </div>
  );
}

function Vacio({ texto }: { texto: string }) {
  return <p className="text-[12px] text-neutral-400">{texto}</p>;
}
