"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { DescubrimientoCarga } from "@/components/DescubrimientoCarga";
import { useUsuario } from "@/context/UsuarioContext";
import { api } from "@/lib/api";
import type { Me } from "@/lib/types";
import { buscarUsuario } from "@/lib/usuarios";

// Carga por descubrimiento (M11): solo admin/uploader. Si el usuario tiene varias
// torres, elige sobre cuál carga.
export default function CargarPage() {
  const { email } = useUsuario();
  const [me, setMe] = useState<Me | null>(null);
  const [torre, setTorre] = useState<string>("");
  const puedeCargar = buscarUsuario(email)?.puedeCargar ?? false;

  useEffect(() => {
    let activo = true;
    api
      .get<Me>("/me")
      .then((m) => {
        if (!activo) return;
        setMe(m);
        setTorre(m.torres[0]?.torre ?? "");
      })
      .catch(() => activo && setMe(null));
    return () => {
      activo = false;
    };
  }, [email]);

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
        Cargar datos
      </h1>
      <p className="mt-1.5 text-[14px] text-neutral-500">
        Sube un archivo: si su estructura es nueva, la primera carga define la
        plantilla y su vista; si ya existe, se previsualiza o se mapea.
      </p>

      <div className="mt-8">
        {!puedeCargar ? (
          <p className="py-8 text-center text-[13px] text-neutral-400">
            Esta sección es solo para roles de carga (uploader o admin).
          </p>
        ) : !me || !torre ? (
          <p className="py-8 text-center text-[13px] text-neutral-400">
            Cargando…
          </p>
        ) : (
          <>
            {me.torres.length > 1 && (
              <div className="mb-5">
                <label className="mb-1 block text-[13px] font-medium text-neutral-800">
                  Torre
                </label>
                <select
                  value={torre}
                  onChange={(e) => setTorre(e.target.value)}
                  className="rounded-lg border border-neutral-200 px-3 py-2 text-[14px]"
                >
                  {me.torres.map((t) => (
                    <option key={t.torre} value={t.torre}>
                      {t.torre}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <DescubrimientoCarga key={torre} torre={torre} />
          </>
        )}
      </div>
    </div>
  );
}
