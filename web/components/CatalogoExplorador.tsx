"use client";

import { ChevronDown, ChevronRight, Lock, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useUsuario } from "@/context/UsuarioContext";
import { api } from "@/lib/api";
import type { TorreCatalogo } from "@/lib/types";

// Explorador del catálogo de preguntas (M9).
// Muestra TODAS las torres para que el piloto se vea completo, con categorías
// colapsables y buscador. Las preguntas 'activa' (ejecutables) son clicables y
// envían al chat; las 'proximamente' se muestran en gris con badge, NO clicables.
// "Una pregunta clicable es una promesa": solo `ejecutable` es un botón.
export function CatalogoExplorador({ onElegir }: { onElegir: (pregunta: string) => void }) {
  const { email } = useUsuario();
  const [torres, setTorres] = useState<TorreCatalogo[]>([]);
  const [filtro, setFiltro] = useState("");
  const [cerradas, setCerradas] = useState<Set<string>>(new Set());

  useEffect(() => {
    let activo = true;
    api
      .get<TorreCatalogo[]>("/catalogo/preguntas")
      .then((t) => activo && setTorres(t))
      .catch(() => activo && setTorres([]));
    return () => {
      activo = false;
    };
  }, [email]);

  // Filtra por texto de pregunta; descarta categorías y torres sin coincidencias.
  const visibles = useMemo(() => {
    const q = filtro.trim().toLowerCase();
    if (!q) return torres;
    return torres
      .map((t) => ({
        ...t,
        categorias: t.categorias
          .map((c) => ({
            ...c,
            preguntas: c.preguntas.filter((p) => p.texto.toLowerCase().includes(q)),
          }))
          .filter((c) => c.preguntas.length > 0),
      }))
      .filter((t) => t.categorias.length > 0);
  }, [torres, filtro]);

  function alternar(clave: string) {
    setCerradas((prev) => {
      const sig = new Set(prev);
      if (sig.has(clave)) sig.delete(clave);
      else sig.add(clave);
      return sig;
    });
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-4 py-2.5">
        <Search className="h-4 w-4 shrink-0 text-neutral-400" aria-hidden />
        <input
          type="text"
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          placeholder="Buscar una pregunta…"
          aria-label="Buscar una pregunta"
          className="min-w-0 flex-1 bg-transparent text-[14px] text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
        />
      </div>

      {visibles.length === 0 ? (
        <p className="py-8 text-center text-[13px] text-neutral-400">
          No hay preguntas que coincidan con “{filtro}”.
        </p>
      ) : (
        visibles.map((torre) => (
          <section key={torre.torre}>
            <div className="mb-3 flex items-center gap-2">
              <h2 className="text-[15px] font-medium text-neutral-900">{torre.nombre}</h2>
              {torre.estado_torre !== "activa" && <BadgeProximamente />}
            </div>
            <div className="space-y-2">
              {torre.categorias.map((cat) => {
                const clave = `${torre.torre}/${cat.nombre}`;
                const abierta = !cerradas.has(clave);
                const activas = cat.preguntas.filter((p) => p.ejecutable).length;
                return (
                  <div
                    key={clave}
                    className="overflow-hidden rounded-xl border border-neutral-100 bg-white"
                  >
                    <button
                      type="button"
                      onClick={() => alternar(clave)}
                      aria-expanded={abierta}
                      className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left hover:bg-surface-100"
                    >
                      <span className="flex items-center gap-2">
                        {abierta ? (
                          <ChevronDown className="h-4 w-4 text-neutral-400" aria-hidden />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-neutral-400" aria-hidden />
                        )}
                        <span className="text-[13.5px] font-medium text-neutral-700">
                          {cat.nombre}
                        </span>
                      </span>
                      <span className="text-[11.5px] text-neutral-400">
                        {activas > 0
                          ? `${activas} de ${cat.preguntas.length} disponibles`
                          : `${cat.preguntas.length} próximamente`}
                      </span>
                    </button>
                    {abierta && (
                      <ul className="space-y-1.5 px-3 pb-3">
                        {cat.preguntas.map((p) =>
                          p.ejecutable ? (
                            <li key={p.id}>
                              <button
                                type="button"
                                onClick={() => onElegir(p.texto)}
                                className="w-full rounded-lg border border-brand-100 bg-brand-50 px-3.5 py-2.5 text-left text-[13.5px] text-brand-800 transition-colors hover:bg-brand-100"
                              >
                                {p.texto}
                              </button>
                            </li>
                          ) : (
                            <li key={p.id}>
                              <div
                                aria-disabled
                                title="Próximamente: esta torre aún no tiene datos disponibles."
                                className="flex w-full cursor-not-allowed items-center justify-between gap-2 rounded-lg border border-neutral-100 bg-surface-100 px-3.5 py-2.5 text-left text-[13.5px] text-neutral-400"
                              >
                                <span>{p.texto}</span>
                                <BadgeProximamente />
                              </div>
                            </li>
                          ),
                        )}
                      </ul>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        ))
      )}
    </div>
  );
}

function BadgeProximamente() {
  return (
    <span className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-pill bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-500">
      <Lock className="h-3 w-3 shrink-0" aria-hidden />
      Próximamente
    </span>
  );
}
