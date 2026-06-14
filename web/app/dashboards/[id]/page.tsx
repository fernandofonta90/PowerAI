"use client";

import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { VisualRenderer } from "@/components/dashboard/VisualRenderer";
import { Sparkle } from "@/components/Sparkle";
import { useUsuario } from "@/context/UsuarioContext";
import { api } from "@/lib/api";
import type { DashboardRenderizado } from "@/lib/types";

export default function DashboardPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const router = useRouter();
  const { email } = useUsuario();
  const [dash, setDash] = useState<DashboardRenderizado | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    api
      .get<DashboardRenderizado>(`/dashboards/${id}`)
      .then((d) => activo && setDash(d))
      .catch(() => activo && setError("Dashboard no encontrado."));
    return () => {
      activo = false;
    };
  }, [id, email]);

  async function eliminar() {
    await api.del(`/dashboards/${id}`);
    router.push("/");
  }

  if (error) return <p className="p-8 text-[13px] text-danger-700">{error}</p>;
  if (!dash) return <p className="p-8 text-[13px] text-neutral-500">Cargando…</p>;

  const filtros = Object.entries(dash.filtros)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join(" · ");

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-8">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-medium text-neutral-900">
            <Sparkle className="h-5 w-5 text-brand-600" title="Generado por IA" />
            {dash.nombre}
          </h1>
          <p className="mt-1 text-[12.5px] text-neutral-500">
            {dash.torre}
            {filtros ? ` · ${filtros}` : ""} · datos actualizados al abrir
          </p>
        </div>
        <button
          type="button"
          onClick={eliminar}
          aria-label="Eliminar dashboard"
          className="inline-flex items-center gap-1 rounded-pill border border-neutral-200 px-3 py-1.5 text-[12px] text-danger-700"
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden />
          Eliminar
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {dash.visuales.map((v, i) => (
          <div key={i} className={v.tipo === "tabla" ? "md:col-span-2" : ""}>
            <VisualRenderer visual={v} />
          </div>
        ))}
      </div>
    </div>
  );
}
