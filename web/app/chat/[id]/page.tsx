"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { MessageBubble, type ItemMensaje } from "@/components/chat/MessageBubble";
import { SourcesRail } from "@/components/chat/SourcesRail";
import { Sparkle } from "@/components/Sparkle";
import { useUsuario } from "@/context/UsuarioContext";
import { ApiError, api } from "@/lib/api";
import type {
  ConversacionDetalle,
  DashboardMeta,
  GenerarDashboardResponse,
  RespuestaChat,
} from "@/lib/types";

export default function ChatPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const router = useRouter();
  const { email } = useUsuario();
  const [items, setItems] = useState<ItemMensaje[]>([]);
  const [ocupado, setOcupado] = useState(false);
  const [generando, setGenerando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoEnviado = useRef(false);

  async function generarDashboard(pregunta: string) {
    setError(null);
    setGenerando(true);
    try {
      const r = await api.post<GenerarDashboardResponse>("/dashboards/generar", {
        peticion: pregunta,
      });
      if (!r.spec) {
        setError(r.mensaje); // honesto: no se puede generar con las vistas disponibles
        return;
      }
      const d = await api.post<DashboardMeta>("/dashboards", {
        nombre: pregunta.slice(0, 60),
        torre: "OTC",
        spec: r.spec,
      });
      router.push(`/dashboards/${d.id}`);
    } catch {
      setError("No se pudo generar el dashboard.");
    } finally {
      setGenerando(false);
    }
  }

  async function enviar(pregunta: string) {
    setError(null);
    setItems((prev) => [...prev, { rol: "user", contenido: pregunta }]);
    setOcupado(true);
    try {
      const r = await api.post<RespuestaChat>(`/conversaciones/${id}/mensajes`, {
        pregunta,
      });
      setItems((prev) => [
        ...prev,
        { rol: "assistant", contenido: r.texto, datos: r.datos_tabulares, citacion: r.citacion },
      ]);
    } catch (e) {
      const msg = e instanceof ApiError && e.status === 404 ? "Conversación no encontrada." : "Ocurrió un error al consultar.";
      setError(msg);
    } finally {
      setOcupado(false);
    }
  }

  // Carga el historial y, si el home pasó ?q=, envía esa primera pregunta.
  useEffect(() => {
    let activo = true;
    api
      .get<ConversacionDetalle>(`/conversaciones/${id}`)
      .then((c) => {
        if (!activo) return;
        setItems(
          c.mensajes.map((m) => ({
            rol: m.rol,
            contenido: m.contenido,
            citacion: m.citacion,
          })),
        );
        const q = new URLSearchParams(window.location.search).get("q");
        if (q && !autoEnviado.current && c.mensajes.length === 0) {
          autoEnviado.current = true;
          window.history.replaceState(null, "", `/chat/${id}`);
          void enviar(q);
        }
      })
      .catch(() => activo && setError("Conversación no encontrada."));
    return () => {
      activo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, email]);

  return (
    <div className="flex flex-1 overflow-hidden">
      <ChatSidebar activoId={id} />
      <section className="flex flex-1 flex-col">
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="mx-auto flex max-w-3xl flex-col gap-6">
            {error && <p className="text-[13px] text-danger-700">{error}</p>}
            {items.map((it, i) => (
              <MessageBubble
                key={i}
                item={it}
                generando={generando}
                onGenerarDashboard={
                  it.rol === "assistant" && it.datos && items[i - 1]?.rol === "user"
                    ? () => generarDashboard(items[i - 1].contenido)
                    : undefined
                }
              />
            ))}
            {ocupado && (
              <div className="flex items-center gap-3 text-neutral-500" aria-live="polite">
                <Sparkle className="h-5 w-5 animate-pulse text-brand-600" />
                <span className="text-[13px]">Analizando las vistas disponibles…</span>
              </div>
            )}
          </div>
        </div>
        <div className="border-t border-neutral-100 bg-surface-100 px-6 py-4">
          <div className="mx-auto max-w-3xl">
            <ChatInput onEnviar={enviar} ocupado={ocupado} />
          </div>
        </div>
      </section>
      <SourcesRail />
    </div>
  );
}
