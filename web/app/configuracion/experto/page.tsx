"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { ExpertoConfig } from "@/components/ExpertoConfig";
import { Sparkle } from "@/components/Sparkle";
import { useUsuario } from "@/context/UsuarioContext";
import { buscarUsuario } from "@/lib/usuarios";

// Configuración del Experto por torre (solo admin de la torre). M10.
export default function ConfiguracionExpertoPage() {
  const { email } = useUsuario();
  const torre = buscarUsuario(email)?.adminTorre;

  return (
    <div className="mx-auto w-full max-w-[760px] px-6 py-12">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-[13px] text-neutral-500 hover:text-brand-800"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Volver al inicio
      </Link>
      <h1 className="mt-4 flex items-center gap-2 text-[21px] font-medium text-neutral-900">
        <Sparkle className="h-5 w-5 text-brand-600" />
        Experto {torre ?? ""}
      </h1>
      <p className="mt-1.5 text-[14px] text-neutral-500">
        Define la identidad, el formato y las fuentes del experto de tu torre.
        Los cambios solo se activan si pasan el banco de evals.
      </p>
      <div className="mt-8">
        {torre ? (
          <ExpertoConfig torre={torre} />
        ) : (
          <p className="py-8 text-center text-[13px] text-neutral-400">
            No eres administrador de ninguna torre. Esta sección es solo para
            administradores.
          </p>
        )}
      </div>
    </div>
  );
}
