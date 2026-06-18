"use client";

import { useEffect, useRef } from "react";
import { Sparkle } from "@/components/Sparkle";
import { saludo } from "@/lib/format";

// Banner ancho del home: degradado violeta AI.Q + animación sutil de partículas
// (efecto constelación) dentro del propio banner. Presentacional: no toca lógica
// de chat. Respeta prefers-reduced-motion y se pausa si la pestaña no está visible.

type Particula = { x: number; y: number; vx: number; vy: number };

const N_PARTICULAS = 38;
const DIST_CONEXION = 110; // px: umbral para dibujar línea entre dos partículas
const COLOR_PARTICULA = "201, 197, 236"; // brand-200 (#C9C5EC)

export function ChatBanner({ nombre }: { nombre: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let ancho = 0;
    let alto = 0;
    let dpr = 1;
    const particulas: Particula[] = [];

    // (Re)dimensiona el canvas al tamaño real del banner, nítido en pantallas HiDPI.
    function redimensionar() {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      ancho = rect.width;
      alto = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(ancho * dpr);
      canvas.height = Math.round(alto * dpr);
      ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function sembrar() {
      particulas.length = 0;
      for (let i = 0; i < N_PARTICULAS; i++) {
        particulas.push({
          x: Math.random() * ancho,
          y: Math.random() * alto,
          // Velocidad muy baja: movimiento premium, no distractor.
          vx: (Math.random() - 0.5) * 0.22,
          vy: (Math.random() - 0.5) * 0.22,
        });
      }
    }

    function dibujar() {
      if (!ctx) return;
      ctx.clearRect(0, 0, ancho, alto);

      // Líneas de constelación entre partículas cercanas (más tenues con la distancia).
      for (let i = 0; i < particulas.length; i++) {
        for (let j = i + 1; j < particulas.length; j++) {
          const a = particulas[i];
          const b = particulas[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.hypot(dx, dy);
          if (dist < DIST_CONEXION) {
            const op = (1 - dist / DIST_CONEXION) * 0.18;
            ctx.strokeStyle = `rgba(${COLOR_PARTICULA}, ${op})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      // Partículas.
      for (const p of particulas) {
        ctx.fillStyle = `rgba(${COLOR_PARTICULA}, 0.55)`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    function avanzar() {
      for (const p of particulas) {
        p.x += p.vx;
        p.y += p.vy;
        // Rebote suave en los bordes para mantenerlas siempre dentro del banner.
        if (p.x <= 0 || p.x >= ancho) p.vx *= -1;
        if (p.y <= 0 || p.y >= alto) p.vy *= -1;
        p.x = Math.max(0, Math.min(ancho, p.x));
        p.y = Math.max(0, Math.min(alto, p.y));
      }
    }

    let raf = 0;
    function bucle() {
      avanzar();
      dibujar();
      raf = window.requestAnimationFrame(bucle);
    }

    function parar() {
      if (raf) {
        window.cancelAnimationFrame(raf);
        raf = 0;
      }
    }

    function arrancar() {
      if (reduce || raf || document.hidden) return;
      raf = window.requestAnimationFrame(bucle);
    }

    function onVisibilidad() {
      if (document.hidden) parar();
      else arrancar();
    }

    redimensionar();
    sembrar();
    dibujar(); // primer cuadro estático (también es el único si reduce-motion)
    if (!reduce) arrancar();

    const ro = new ResizeObserver(() => {
      redimensionar();
      sembrar();
      dibujar();
    });
    ro.observe(canvas);
    document.addEventListener("visibilitychange", onVisibilidad);

    return () => {
      parar();
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVisibilidad);
    };
  }, []);

  return (
    <div
      className="relative w-full overflow-hidden rounded-3xl"
      style={{
        height: 150,
        backgroundImage: "linear-gradient(135deg, #1a1340 0%, #453A96 100%)",
      }}
    >
      <canvas
        ref={canvasRef}
        aria-hidden
        className="pointer-events-none absolute inset-0 h-full w-full"
      />
      <div className="relative flex h-full flex-col items-center justify-center px-6 text-center">
        <h1 className="flex items-center gap-2 text-[22px] font-medium text-white">
          <Sparkle className="h-5 w-5 text-brand-200" />
          {saludo()}
          {nombre ? `, ${nombre}` : ""}
        </h1>
        <p className="mt-1.5 text-[14px] text-brand-200">
          Pregunta sobre la información de tu torre
        </p>
      </div>
    </div>
  );
}
