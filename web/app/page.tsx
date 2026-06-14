"use client";

import { Send } from "lucide-react";
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

// Home (spec canónica del design system): hero de pregunta + chips + grid de 3.
export default function HomePage() {
  const router = useRouter();
  const { email } = useUsuario();
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const nombre = buscarUsuario(email)?.nombre ?? "";

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
    <div className="mx-auto w-full max-w-4xl px-6 py-12">
      {/* 1. Hero de pregunta (centrado) */}
      <section className="flex flex-col items-center text-center">
        <h1 className="flex items-center gap-2 text-[17px] font-medium text-neutral-900">
          <Sparkle className="h-5 w-5 text-brand-600" />
          {saludo()}{nombre ? `, ${nombre}` : ""}
        </h1>
        <p className="mt-1 text-[12.5px] text-neutral-500">
          Pregunta sobre la información de tu torre
        </p>

        <div className="mt-5 w-full max-w-[480px]">
          <div className="flex items-center gap-2 rounded-xl border border-brand-200 bg-white px-3 py-2.5 shadow-hero">
            <Sparkle className="h-4 w-4 shrink-0 text-brand-600" />
            <input
              type="text"
              value={texto}
              disabled={ocupado}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && iniciar(texto)}
              placeholder="Pregúntame lo que quieras"
              aria-label="Escribe tu pregunta"
              className="min-w-0 flex-1 bg-transparent text-[14px] text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => iniciar(texto)}
              disabled={ocupado || texto.trim() === ""}
              aria-label="Enviar pregunta"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-pill bg-brand-600 text-white disabled:opacity-40"
            >
              <Send className="h-4 w-4" aria-hidden />
            </button>
          </div>
          <SugeridasChips onElegir={iniciar} />
        </div>
      </section>

      {/* 2. Grid de contexto (3 tarjetas) */}
      <ContextGrid />
    </div>
  );
}
