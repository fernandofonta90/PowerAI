"use client";

import { AlertTriangle, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { ColumnaSpec, Frecuencia, TipoColumna } from "@/lib/types";

const TIPOS: TipoColumna[] = ["texto", "entero", "decimal", "fecha"];
const FRECUENCIAS: Frecuencia[] = ["diaria", "semanal", "quincenal", "mensual"];

type PlantillaDetalle = {
  codigo: string;
  nombre: string;
  frecuencia: Frecuencia;
  columna_pais: string;
  columna_periodo: string;
  columnas: ColumnaSpec[];
};

// Edición EXPLÍCITA del molde de una plantilla (solo admin). Muestra el aviso de
// impacto: cambiar el molde afecta a las cargas existentes. Camino separado del
// flujo de carga: aquí sí se redefine la estructura, a propósito.
export function EditarPlantilla({
  codigo,
  torre,
}: {
  codigo: string;
  torre: string;
}) {
  const [p, setP] = useState<PlantillaDetalle | null>(null);
  const [impacto, setImpacto] = useState<number | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    api
      .get<PlantillaDetalle[]>(`/plantillas?torre=${torre}`)
      .then(
        (lista) =>
          activo && setP(lista.find((x) => x.codigo === codigo) ?? null),
      )
      .catch(() => activo && setError("No se pudo cargar la plantilla."));
    api
      .get<{ cargas_afectadas: number }>(`/plantillas/${codigo}/impacto`)
      .then((r) => activo && setImpacto(r.cargas_afectadas))
      .catch(() => activo && setImpacto(null));
    return () => {
      activo = false;
    };
  }, [codigo, torre]);

  if (error && !p)
    return <p className="text-[13px] text-danger-700">{error}</p>;
  if (!p) return <p className="text-[13px] text-neutral-400">Cargando…</p>;

  function actualizarCol(i: number, cambios: Partial<ColumnaSpec>) {
    if (!p) return;
    const columnas = p.columnas.map((c, j) =>
      j === i ? { ...c, ...cambios } : c,
    );
    setP({ ...p, columnas });
  }

  async function guardar() {
    if (!p) return;
    setOcupado(true);
    setError(null);
    setMsg(null);
    try {
      await api.put(`/plantillas/${p.codigo}`, {
        nombre: p.nombre,
        frecuencia: p.frecuencia,
        columnas: p.columnas,
        columna_pais: p.columna_pais,
        columna_periodo: p.columna_periodo,
      });
      setMsg("Molde actualizado. La vista 1:1 se re-sincronizó.");
    } catch (e: unknown) {
      setError(
        e instanceof ApiError
          ? `No se pudo guardar (${e.status}).`
          : "Error al guardar.",
      );
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="space-y-4">
      {impacto !== null && impacto > 0 && (
        <div className="flex items-start gap-2 rounded-xl border border-warning-600/30 bg-warning-600/5 p-3 text-[13px] text-warning-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span>
            Cambiar este molde afecta a <strong>{impacto}</strong> carga(s)
            existente(s) y a las futuras. Es un cambio explícito de la
            estructura, no un mapeo.
          </span>
        </div>
      )}

      <div>
        <label className="mb-1 block text-[13px] font-medium text-neutral-800">
          Nombre
        </label>
        <input
          value={p.nombre}
          onChange={(e) => setP({ ...p, nombre: e.target.value })}
          className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-[14px]"
        />
      </div>

      <div className="space-y-2">
        <p className="text-[13px] font-medium text-neutral-800">Columnas</p>
        {p.columnas.map((c, i) => (
          <div
            key={i}
            className="grid grid-cols-[1fr_110px_90px_32px] items-center gap-2"
          >
            <input
              aria-label={`Nombre columna ${i}`}
              value={c.nombre}
              onChange={(e) => actualizarCol(i, { nombre: e.target.value })}
              className="rounded-lg border border-neutral-200 px-2 py-1.5 text-[13px]"
            />
            <select
              aria-label={`Tipo columna ${i}`}
              value={c.tipo}
              onChange={(e) =>
                actualizarCol(i, { tipo: e.target.value as TipoColumna })
              }
              className="rounded-lg border border-neutral-200 px-2 py-1.5 text-[13px]"
            >
              {TIPOS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-1 text-[12px] text-neutral-600">
              <input
                type="checkbox"
                checked={c.requerida ?? true}
                onChange={(e) =>
                  actualizarCol(i, { requerida: e.target.checked })
                }
                className="h-3.5 w-3.5 accent-brand-600"
              />
              req.
            </label>
            <button
              type="button"
              aria-label={`Eliminar columna ${i}`}
              onClick={() =>
                setP({ ...p, columnas: p.columnas.filter((_, j) => j !== i) })
              }
              className="flex h-8 w-8 items-center justify-center rounded-lg text-neutral-400 hover:text-danger-700"
            >
              <Trash2 className="h-4 w-4" aria-hidden />
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() =>
            setP({
              ...p,
              columnas: [
                ...p.columnas,
                { nombre: "", tipo: "texto", requerida: true },
              ],
            })
          }
          className="inline-flex items-center gap-1 text-[13px] text-brand-800"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden />
          Agregar columna
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-[13px] font-medium text-neutral-800">
            Frecuencia
          </label>
          <select
            value={p.frecuencia}
            onChange={(e) =>
              setP({ ...p, frecuencia: e.target.value as Frecuencia })
            }
            className="w-full rounded-lg border border-neutral-200 px-2 py-1.5 text-[13px]"
          >
            {FRECUENCIAS.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </div>
      </div>

      <button
        type="button"
        onClick={guardar}
        disabled={ocupado}
        className="rounded-pill bg-brand-600 px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-40"
      >
        Guardar cambios del molde
      </button>
      {msg && <p className="text-[13px] text-success-700">{msg}</p>}
      {error && <p className="text-[13px] text-danger-700">{error}</p>}
    </div>
  );
}
