// Tabla de datos del design system: filas alternas, encabezado neutral, montos a
// la derecha con tabular-nums. Los decimales-string se muestran SIN convertir a
// float (no se pierden centavos).

import type { DatosTabulares } from "@/lib/types";
import { esNumerica, mostrarCelda } from "@/lib/format";

export function DataTable({ datos }: { datos: DatosTabulares }) {
  if (datos.filas.length === 0) {
    return (
      <p className="mt-2 text-[12px] text-neutral-500">
        No hay datos para tu alcance.
      </p>
    );
  }
  return (
    <div className="mt-3 overflow-x-auto rounded-lg border border-neutral-100">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr className="bg-surface-100">
            {datos.columnas.map((c) => (
              <th
                key={c}
                scope="col"
                className="px-3 py-2 text-left text-[12px] font-medium text-neutral-500"
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {datos.filas.map((fila, i) => (
            <tr key={i} className={i % 2 === 1 ? "bg-surface-100/60" : "bg-white"}>
              {fila.map((celda, j) => (
                <td
                  key={j}
                  className={`px-3 py-1.5 text-neutral-700 ${
                    esNumerica(celda) ? "text-right tabular-nums" : "text-left"
                  }`}
                >
                  {mostrarCelda(celda)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
