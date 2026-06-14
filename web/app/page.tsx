"use client";

import { ArrowRight, ArrowUp, Settings2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ContextGrid } from "@/components/ContextGrid";
import { SugeridasChips } from "@/components/SugeridasChips";
import { Sparkle } from "@/components/Sparkle";
import { useUsuario } from "@/context/UsuarioContext";
import { api } from "@/lib/api";
import { saludo } from "@/lib/format";
import type { Conversacion } from "@/lib/types";
import { buscarUsuario } from "@/lib/usuarios";

// Home (spec canónica del design system): hero de pregunta protagonista + grid.
export default function HomePage() {
  const router = useRouter();
  const { email } = useUsuario();
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const usuarioMock = buscarUsuario(email);
  const nombre = usuarioMock?.nombre ?? "";
  const adminTorre = usuarioMock?.adminTorre;

  async function iniciar(pregunta: string) {
    const p = pregunta.trim();
    if (!p || ocupado) return;
    setOcupado(true);
    try {
      const conv = await api.post<Conversacion>("/conversaciones", {
        titulo: p.slice(0, 60),
      });
      router.push(`/chat/${conv.id}?q=${encodeURIComponent(p)}`);
    } catch {
      setOcupado(false);
    }
  }

  return (
    <div className="w-full px-6 py-16">
      {/* 1. Hero de pregunta (centrado, ~560px) */}
      <section className="mx-auto flex w-full max-w-[560px] flex-col items-center text-center">
        <h1 className="flex items-center gap-2 text-[21px] font-medium text-neutral-900">
          <Sparkle className="h-5 w-5 text-brand-600" />
          {saludo()}
          {nombre ? `, ${nombre}` : ""}
        </h1>
        <p className="mt-1.5 text-[14px] text-neutral-500">
          Pregunta sobre la información de tu torre
        </p>

        <div className="mt-7 w-full">
          <div className="flex items-center gap-2 rounded-2xl border border-brand-200 bg-white px-4 py-3 shadow-hero">
            <Sparkle className="h-5 w-5 shrink-0 text-brand-600" />
            <input
              type="text"
              value={texto}
              disabled={ocupado}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && iniciar(texto)}
              placeholder="Pregúntame lo que quieras"
              aria-label="Escribe tu pregunta"
              className="min-w-0 flex-1 bg-transparent text-[15px] text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => iniciar(texto)}
              disabled={ocupado || texto.trim() === ""}
              aria-label="Enviar pregunta"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-600 text-white transition-opacity disabled:opacity-40"
            >
              <ArrowUp className="h-[18px] w-[18px]" aria-hidden />
            </button>
          </div>
          <SugeridasChips onElegir={iniciar} />
          <div className="mt-3 flex flex-wrap items-center justify-center gap-x-5 gap-y-2">
            <Link
              href="/preguntas"
              className="inline-flex items-center gap-1 text-[13px] text-brand-800 hover:underline"
            >
              Explorar todas las preguntas
              <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </Link>
            {adminTorre && (
              <Link
                href="/configuracion/experto"
                className="inline-flex items-center gap-1 text-[13px] text-neutral-500 hover:text-brand-800"
              >
                <Settings2 className="h-3.5 w-3.5" aria-hidden />
                Configurar experto {adminTorre}
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* 2. Grid de contexto (~760px) */}
      <div className="mx-auto mt-12 w-full max-w-[760px]">
        <ContextGrid />
      </div>
    </div>
  );
}
