"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DataTable } from "@/components/chat/DataTable";
import type { Celda, VisualRenderizado } from "@/lib/types";
import { mostrarCelda } from "@/lib/format";

const BRAND = "#5B51C8";

function indice(columnas: string[], nombre: string | null): number {
  return nombre ? columnas.indexOf(nombre) : -1;
}

// Datos para charts: {x, y(numérico para la geometría), raw(string exacto para tooltip)}.
function datosChart(v: VisualRenderizado): { x: string; y: number; raw: string }[] {
  const ix = indice(v.columnas, v.eje_x);
  const iy = indice(v.columnas, v.eje_y);
  if (ix < 0 || iy < 0) return [];
  return v.filas.map((fila) => ({
    x: mostrarCelda(fila[ix]),
    y: Number(fila[iy]),
    raw: mostrarCelda(fila[iy]),
  }));
}

function valorKpi(v: VisualRenderizado): Celda {
  const i = indice(v.columnas, v.columna_valor);
  if (v.filas.length === 0 || i < 0) return "—";
  return v.filas[0][i];
}

export function VisualRenderer({ visual }: { visual: VisualRenderizado }) {
  if (visual.error) {
    return (
      <Card titulo={visual.titulo}>
        <p className="text-[12px] text-danger-700">No se pudo cargar: {visual.error}</p>
      </Card>
    );
  }

  if (visual.tipo === "kpi") {
    return (
      <Card titulo={visual.titulo}>
        {/* Monto exacto (string) sin convertir a float. */}
        <p className="text-3xl font-semibold tabular-nums text-neutral-900">
          {mostrarCelda(valorKpi(visual))}
        </p>
      </Card>
    );
  }

  if (visual.tipo === "tabla") {
    return (
      <Card titulo={visual.titulo}>
        <DataTable datos={{ columnas: visual.columnas, filas: visual.filas }} />
      </Card>
    );
  }

  const datos = datosChart(visual);
  return (
    <Card titulo={visual.titulo}>
      <ResponsiveContainer width="100%" height={240}>
        {visual.tipo === "lineas" ? (
          <LineChart data={datos} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#E2E4EE" vertical={false} />
            <XAxis dataKey="x" tick={{ fontSize: 11, fill: "#6B6B80" }} />
            <YAxis tick={{ fontSize: 11, fill: "#6B6B80" }} />
            <Tooltip formatter={(_v, _n, p) => (p?.payload?.raw ?? "") as string} />
            <Line type="monotone" dataKey="y" stroke={BRAND} strokeWidth={2} dot={false} />
          </LineChart>
        ) : (
          <BarChart data={datos} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#E2E4EE" vertical={false} />
            <XAxis dataKey="x" tick={{ fontSize: 11, fill: "#6B6B80" }} />
            <YAxis tick={{ fontSize: 11, fill: "#6B6B80" }} />
            <Tooltip formatter={(_v, _n, p) => (p?.payload?.raw ?? "") as string} />
            <Bar dataKey="y" fill={BRAND} radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </Card>
  );
}

function Card({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-neutral-100 bg-white p-4">
      <h3 className="mb-3 text-[13px] font-medium text-neutral-700">{titulo}</h3>
      {children}
    </div>
  );
}
