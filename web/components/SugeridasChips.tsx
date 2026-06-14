"use client";

import { useEffect, useState } from "react";
import { useUsuario } from "@/context/UsuarioContext";
import { api } from "@/lib/api";

// Chips de preguntas sugeridas (pill brand-50/brand-200, texto brand-800).
// Alimentados desde el banco de preguntas doradas (endpoint por torre). Clic = enviar.
export function SugeridasChips({
  torre = "OTC",
  onElegir,
}: {
  torre?: string;
  onElegir: (pregunta: string) => void;
}) {
  const { email } = useUsuario();
  const [chips, setChips] = useState<string[]>([]);

  useEffect(() => {
    let activo = true;
    api
      .get<string[]>(`/torres/${torre}/preguntas-sugeridas`)
      .then((p) => activo && setChips(p))
      .catch(() => activo && setChips([]));
    return () => {
      activo = false;
    };
  }, [email, torre]);

  if (chips.length === 0) return null;

  return (
    <div className="mt-4 flex flex-col gap-2 text-left">
      {chips.map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => onElegir(p)}
          className="w-full rounded-lg border border-brand-100 bg-brand-50 px-3.5 py-2.5 text-left text-[13.5px] text-brand-800 transition-colors hover:bg-brand-100"
        >
          {p}
        </button>
      ))}
    </div>
  );
}
