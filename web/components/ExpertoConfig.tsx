"use client";

import { CheckCircle2, Lock, ShieldCheck, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Sparkle } from "@/components/Sparkle";
import { useUsuario } from "@/context/UsuarioContext";
import { ApiError, api } from "@/lib/api";
import type {
  ActivacionExperto,
  ConfigExpertoInput,
  ExpertoScreen,
  VistaExperto,
} from "@/lib/types";

// Configuración del Experto de una torre (solo admin). Edita identidad/tono,
// formato y fuentes permitidas; las reglas estructurales se muestran como
// garantías fijas. "Guardar y validar" corre los evals y solo activa si pasan.
export function ExpertoConfig({ torre }: { torre: string }) {
  const { email } = useUsuario();
  const [pantalla, setPantalla] = useState<ExpertoScreen | null>(null);
  const [nombre, setNombre] = useState("");
  const [identidad, setIdentidad] = useState("");
  const [formato, setFormato] = useState("");
  const [fuentes, setFuentes] = useState<Set<string>>(new Set());
  const [ocupado, setOcupado] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [activacion, setActivacion] = useState<ActivacionExperto | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    api
      .get<ExpertoScreen>(`/torres/${torre}/experto`)
      .then((p) => {
        if (!activo) return;
        setPantalla(p);
        const base = p.borrador ?? p.activo;
        setNombre(base?.nombre ?? `Experto ${torre}`);
        setIdentidad(base?.identidad ?? "");
        setFormato(base?.instrucciones_formato ?? "");
        setFuentes(new Set(base?.fuentes ?? []));
        setError(null);
      })
      .catch((e: unknown) => {
        if (!activo) return;
        setError(
          e instanceof ApiError && e.status === 403
            ? "Necesitas rol de administrador de esta torre para configurar su experto."
            : "No se pudo cargar la configuración del experto.",
        );
      });
    return () => {
      activo = false;
    };
  }, [email, torre]);

  function alternarFuente(nombreVista: string) {
    setFuentes((prev) => {
      const sig = new Set(prev);
      if (sig.has(nombreVista)) sig.delete(nombreVista);
      else sig.add(nombreVista);
      return sig;
    });
  }

  function cuerpo(): ConfigExpertoInput {
    return {
      nombre,
      identidad,
      instrucciones_formato: formato,
      fuentes: [...fuentes],
    };
  }

  async function guardar() {
    setOcupado(true);
    setMensaje(null);
    setActivacion(null);
    setError(null);
    try {
      await api.put(`/torres/${torre}/experto/borrador`, cuerpo());
      setMensaje(
        "Borrador guardado. Aún no está activo: valida con evals para activarlo.",
      );
    } catch (e: unknown) {
      setError(
        e instanceof ApiError
          ? `No se pudo guardar (${e.status}).`
          : "No se pudo guardar.",
      );
    } finally {
      setOcupado(false);
    }
  }

  async function validarYActivar() {
    setOcupado(true);
    setMensaje(null);
    setActivacion(null);
    setError(null);
    try {
      const r = await api.post<ActivacionExperto>(
        `/torres/${torre}/experto/activar`,
        cuerpo(),
      );
      setActivacion(r);
    } catch (e: unknown) {
      setError(
        e instanceof ApiError
          ? `No se pudo validar (${e.status}).`
          : "No se pudo validar.",
      );
    } finally {
      setOcupado(false);
    }
  }

  if (error && !pantalla) {
    return (
      <p className="py-8 text-center text-[13px] text-danger-700">{error}</p>
    );
  }
  if (!pantalla) {
    return (
      <p className="py-8 text-center text-[13px] text-neutral-400">Cargando…</p>
    );
  }

  return (
    <div className="space-y-6">
      {pantalla.activo && (
        <p className="text-[12.5px] text-neutral-500">
          Versión activa: v{pantalla.activo.version} · «{pantalla.activo.nombre}
          »
        </p>
      )}

      <Campo etiqueta="Nombre del experto">
        <input
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-[14px] text-neutral-900 focus:outline-none focus:ring-1 focus:ring-brand-600"
        />
      </Campo>

      <Campo
        etiqueta="Identidad y tono"
        ayuda="Cómo se presenta y comunica el experto. No incluye reglas de seguridad."
      >
        <textarea
          value={identidad}
          onChange={(e) => setIdentidad(e.target.value)}
          rows={4}
          className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-[14px] leading-relaxed text-neutral-900 focus:outline-none focus:ring-1 focus:ring-brand-600"
        />
      </Campo>

      <Campo
        etiqueta="Instrucciones de formato"
        ayuda="Cómo estructurar las respuestas (columnas, agregados, tramos…)."
      >
        <textarea
          value={formato}
          onChange={(e) => setFormato(e.target.value)}
          rows={5}
          className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-[14px] leading-relaxed text-neutral-900 focus:outline-none focus:ring-1 focus:ring-brand-600"
        />
      </Campo>

      <Campo
        etiqueta="Fuentes permitidas"
        ayuda="Vistas del catálogo de la torre que el experto puede consultar."
      >
        <div className="space-y-1.5">
          {pantalla.vistas_torre.map((v: VistaExperto) => (
            <label
              key={v.nombre}
              className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-neutral-100 px-3 py-2 hover:bg-surface-100"
            >
              <input
                type="checkbox"
                checked={fuentes.has(v.nombre)}
                onChange={() => alternarFuente(v.nombre)}
                className="mt-0.5 h-4 w-4 accent-brand-600"
              />
              <span className="min-w-0">
                <span className="block text-[13.5px] font-medium text-neutral-800">
                  {v.titulo}
                </span>
                <span className="block truncate text-[12px] text-neutral-500">
                  {v.descripcion}
                </span>
              </span>
            </label>
          ))}
        </div>
      </Campo>

      {/* Garantías estructurales: fijas, no editables (transparencia). */}
      <div className="rounded-xl border border-neutral-100 bg-brand-50 p-4">
        <h3 className="flex items-center gap-1.5 text-[13px] font-medium text-brand-800">
          <ShieldCheck className="h-4 w-4" aria-hidden />
          Garantías fijas del sistema (no configurables)
        </h3>
        <ul className="mt-2.5 space-y-1.5">
          {pantalla.garantias_estructurales.map((g: string) => (
            <li
              key={g}
              className="flex items-start gap-2 text-[12.5px] text-neutral-600"
            >
              <Lock
                className="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-400"
                aria-hidden
              />
              {g}
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={guardar}
          disabled={ocupado}
          className="rounded-pill border border-neutral-200 px-4 py-2 text-[13px] font-medium text-neutral-700 transition-colors hover:bg-surface-100 disabled:opacity-40"
        >
          Guardar borrador
        </button>
        <button
          type="button"
          onClick={validarYActivar}
          disabled={ocupado}
          className="inline-flex items-center gap-1.5 rounded-pill bg-brand-600 px-4 py-2 text-[13px] font-semibold text-white transition-opacity disabled:opacity-40"
        >
          <Sparkle className="h-4 w-4" aria-hidden />
          {ocupado ? "Validando con evals…" : "Guardar y validar con evals"}
        </button>
      </div>

      {mensaje && <p className="text-[13px] text-neutral-600">{mensaje}</p>}
      {error && <p className="text-[13px] text-danger-700">{error}</p>}
      {activacion && <ResultadoActivacion activacion={activacion} />}
    </div>
  );
}

function ResultadoActivacion({
  activacion,
}: {
  activacion: ActivacionExperto;
}) {
  const { activado, motivo, reporte } = activacion;
  const Icono = activado ? CheckCircle2 : XCircle;
  const clase = activado
    ? "border-success-600/30 bg-success-600/5 text-success-700"
    : "border-danger-600/30 bg-danger-600/5 text-danger-700";
  return (
    <div className={`rounded-xl border p-4 ${clase}`}>
      <p className="flex items-center gap-2 text-[13.5px] font-medium">
        <Icono className="h-4 w-4 shrink-0" aria-hidden />
        {motivo}
      </p>
      {reporte && (
        <div className="mt-2 text-[12.5px] text-neutral-600">
          Evals: {reporte.aprobadas}/{reporte.total} aprobadas (
          {(reporte.tasa * 100).toFixed(1)}%).
          {reporte.fallos.length > 0 && (
            <ul className="mt-1.5 space-y-1">
              {reporte.fallos.slice(0, 5).map((f, i) => (
                <li key={i} className="text-neutral-500">
                  ✗ [{f.id}] «{f.fraseo}»: {f.motivo}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function Campo({
  etiqueta,
  ayuda,
  children,
}: {
  etiqueta: string;
  ayuda?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-[13px] font-medium text-neutral-800">
        {etiqueta}
      </label>
      {ayuda && (
        <p className="mb-1.5 mt-0.5 text-[12px] text-neutral-500">{ayuda}</p>
      )}
      {!ayuda && <div className="mb-1.5" />}
      {children}
    </div>
  );
}
