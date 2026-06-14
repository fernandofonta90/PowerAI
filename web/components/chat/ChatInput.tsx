"use client";

import { Send } from "lucide-react";
import { useState } from "react";
import { Sparkle } from "@/components/Sparkle";

// Input flotante de chat (radio 14px) con sparkle a la izquierda y botón circular
// de envío en brand-600. Enter envía; Shift+Enter no aplica (input de una línea).
export function ChatInput({
  onEnviar,
  ocupado,
  placeholder = "Pregúntame lo que quieras",
}: {
  onEnviar: (texto: string) => void;
  ocupado: boolean;
  placeholder?: string;
}) {
  const [texto, setTexto] = useState("");

  const enviar = () => {
    const t = texto.trim();
    if (!t || ocupado) return;
    setTexto("");
    onEnviar(t);
  };

  return (
    <div className="flex items-center gap-2 rounded-[14px] border border-neutral-200 bg-white px-3 py-2 shadow-hero">
      <Sparkle className="h-4 w-4 shrink-0 text-brand-600" />
      <input
        type="text"
        value={texto}
        disabled={ocupado}
        onChange={(e) => setTexto(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && enviar()}
        placeholder={placeholder}
        aria-label="Escribe tu pregunta"
        className="min-w-0 flex-1 bg-transparent text-[14px] text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
      />
      <button
        type="button"
        onClick={enviar}
        disabled={ocupado || texto.trim() === ""}
        aria-label="Enviar pregunta"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-pill bg-brand-600 text-white disabled:opacity-40"
      >
        <Send className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}
