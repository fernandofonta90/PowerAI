"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EditarPlantilla } from "@/components/EditarPlantilla";
import { useUsuario } from "@/context/UsuarioContext";
import { api } from "@/lib/api";
import { buscarUsuario } from "@/lib/usuarios";

type PlantillaItem = { codigo: string; nombre: string };

// Edición explícita del molde (solo admin de la torre). Camino separado de la carga.
export default function EditarPlantillasPage() {
  const { email } = useUsuario();
  const torre = buscarUsuario(email)?.adminTorre;
  const [plantillas, setPlantillas] = useState<PlantillaItem[]>([]);
  const [sel, setSel] = useState<string>("");

  useEffect(() => {
    if (!torre) return;
    let activo = true;
    api
      .get<PlantillaItem[]>(`/plantillas?torre=${torre}`)
      .then((l) => activo && setPlantillas(l))
      .catch(() => activo && setPlantillas([]));
    return () => {
      activo = false;
    };
  }, [email, torre]);

  return (
    <div className="mx-auto w-full max-w-[760px] px-6 py-12">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-[13px] text-neutral-500 hover:text-brand-800"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Volver al inicio
      </Link>
      <h1 className="mt-4 text-[21px] font-medium text-neutral-900">
        Editar plantillas
      </h1>
      <p className="mt-1.5 text-[14px] text-neutral-500">
        Cambiar el molde es un acto explícito de administrador: afecta a las
        cargas existentes y futuras. Para acomodar un archivo puntual, usa el
        mapeo en la carga.
      </p>

      <div className="mt-8">
        {!torre ? (
          <p className="py-8 text-center text-[13px] text-neutral-400">
            Esta sección es solo para administradores de torre.
          </p>
        ) : (
          <>
            <div className="mb-5">
              <label className="mb-1 block text-[13px] font-medium text-neutral-800">
                Plantilla
              </label>
              <select
                value={sel}
                onChange={(e) => setSel(e.target.value)}
                className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-[14px]"
              >
                <option value="">— elige una plantilla —</option>
                {plantillas.map((p) => (
                  <option key={p.codigo} value={p.codigo}>
                    {p.nombre}
                  </option>
                ))}
              </select>
            </div>
            {sel && <EditarPlantilla key={sel} codigo={sel} torre={torre} />}
          </>
        )}
      </div>
    </div>
  );
}
