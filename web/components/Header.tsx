"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { MockUserSelector } from "@/components/MockUserSelector";
import { useUsuario } from "@/context/UsuarioContext";
import { api } from "@/lib/api";
import type { Me } from "@/lib/types";
import { buscarUsuario } from "@/lib/usuarios";

// Header en dos tonos (patrón familia AI.Q). Bloque izquierdo brand-800; banda
// derecha brand-600 con POWERAI, badge de torre/países y avatar. Por gobernanza
// de marca, el bloque izquierdo usa "ManpowerGroup" hasta aprobar el uso de AI.Q.
export function Header() {
  const { email } = useUsuario();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    let activo = true;
    api
      .get<Me>("/me")
      .then((m) => activo && setMe(m))
      .catch(() => activo && setMe(null));
    return () => {
      activo = false;
    };
  }, [email]);

  const usuario = buscarUsuario(email);
  const badge = me?.torres
    .map((t) => `${t.torre} · ${t.paises.join("/")}`)
    .join("  ");

  return (
    <header className="flex items-stretch">
      <div className="flex items-center bg-brand-800 px-6 py-3">
        <span className="text-sm font-medium text-white">ManpowerGroup</span>
      </div>
      <div className="flex flex-1 items-center justify-between bg-brand-600 px-6 py-3">
        <div className="flex items-baseline gap-3">
          <Link href="/" className="text-lg text-white">
            <span className="font-normal">POWER</span>
            <span className="font-semibold">AI</span>
          </Link>
          <span className="text-sm italic text-brand-100">SSC Finanzas LATAM</span>
        </div>
        <div className="flex items-center gap-3">
          {badge && (
            <span className="rounded-pill bg-brand-800 px-3 py-1 text-xs font-medium text-white">
              {badge}
            </span>
          )}
          <MockUserSelector />
          <span
            aria-label={usuario?.nombre ?? email}
            title={usuario?.nombre ?? email}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-800"
          >
            {usuario?.inicial ?? "?"}
          </span>
        </div>
      </div>
    </header>
  );
}
