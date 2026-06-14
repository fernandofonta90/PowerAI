"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { CatalogoExplorador } from "@/components/CatalogoExplorador";
import { api } from "@/lib/api";
import type { Conversacion } from "@/lib/types";

// "Explorar preguntas": catálogo navegable de todas las torres (M9).
export default function PreguntasPage() {
  const router = useRouter();
  const [ocupado, setOcupado] = useState(false);

  async function iniciar(pregunta: string) {
    const p = pregunta.trim();
    if (!p || ocupado) return;
    setOcupado(true);
    try {
      const conv = await api.post<Conversacion>("/conversaciones", { titulo: p.slice(0, 60) });
      router.push(`/chat/${conv.id}?q=${encodeURIComponent(p)}`);
    } catch {
      setOcupado(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-[760px] px-6 py-12">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-[13px] text-neutral-500 hover:text-brand-800"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Volver al inicio
      </Link>
      <h1 className="mt-4 text-[21px] font-medium text-neutral-900">Explorar preguntas</h1>
      <p className="mt-1.5 text-[14px] text-neutral-500">
        Todas las preguntas del SSC por torre. Las disponibles se pueden enviar al chat; el resto
        llegarán cuando su torre tenga datos cargados.
      </p>
      <div className="mt-8">
        <CatalogoExplorador onElegir={iniciar} />
      </div>
    </div>
  );
}
