// Bloque de citación al pie de cada respuesta de IA (fondo brand-50). Nunca
// omitible: archivos fuente con versión y responsable, frescura, y la nota de que
// el SQL queda en la bitácora de auditoría.

import { Database } from "lucide-react";
import { BadgeFrescura } from "@/components/BadgeFrescura";
import type { Citacion } from "@/lib/types";

export function CitationBlock({ citacion }: { citacion: Citacion }) {
  const sinFuentes = citacion.fuentes.length === 0;
  return (
    <div className="mt-3 rounded-lg bg-brand-50 px-3 py-2 text-[11px] text-neutral-700">
      <div className="flex items-center gap-1.5 font-medium text-brand-800">
        <Database className="h-3 w-3" aria-hidden />
        Fuentes
      </div>
      {sinFuentes ? (
        <p className="mt-1 text-neutral-500">
          Sin fuentes: la respuesta no se basó en datos del catálogo.
        </p>
      ) : (
        <ul className="mt-1 space-y-1">
          {citacion.fuentes.map((f, i) => (
            <li key={i} className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-medium text-neutral-900">{f.archivo}</span>
              <span className="text-neutral-500">
                v{f.version} · {f.pais} · {f.periodo} · {f.responsable}
              </span>
              <BadgeFrescura estado={f.frescura} />
            </li>
          ))}
        </ul>
      )}
      {citacion.vistas_usadas.length > 0 && (
        <p className="mt-1.5 text-neutral-500">
          Vistas: {citacion.vistas_usadas.join(", ")}
        </p>
      )}
      <p className="mt-1.5 text-neutral-400">
        El SQL ejecutado queda registrado en la bitácora de auditoría
        {citacion.sql_ejecutado_ids.length > 0
          ? ` (${citacion.sql_ejecutado_ids.length} consulta(s)).`
          : "."}
      </p>
    </div>
  );
}
