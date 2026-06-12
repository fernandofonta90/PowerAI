import type { Metadata } from "next";
import { TorreNav } from "@/components/TorreNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "PowerAI — SSC Finanzas LATAM",
  description:
    "Plataforma de inteligencia analítica del SSC Finanzas LATAM de ManpowerGroup.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>
        <div className="flex min-h-screen flex-col">
          {/* Header en dos tonos (patrón familia AI.Q). Bloque izquierdo brand-800,
              banda derecha brand-600. Hasta aprobar el uso de la marca AI.Q se usa
              "ManpowerGroup" en el bloque izquierdo (ver nota de gobernanza). */}
          <header className="flex items-stretch">
            <div className="flex items-center bg-brand-800 px-6 py-3">
              <span className="text-sm font-medium text-white">
                ManpowerGroup
              </span>
            </div>
            <div className="flex flex-1 items-center justify-between bg-brand-600 px-6 py-3">
              <div className="flex items-baseline gap-2">
                <span className="text-lg text-white">
                  <span className="font-normal">POWER</span>
                  <span className="font-semibold">AI</span>
                </span>
                <span className="text-sm italic text-brand-100">
                  SSC Finanzas LATAM
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="rounded-pill bg-brand-800 px-3 py-1 text-xs font-medium text-white">
                  OTC · MX
                </span>
                <span
                  aria-label="Usuario"
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-800"
                >
                  AO
                </span>
              </div>
            </div>
          </header>

          <div className="flex flex-1">
            <aside className="w-60 border-r border-neutral-100 bg-surface-200 p-4">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Torres
              </h2>
              <TorreNav />
            </aside>
            <main className="flex-1 p-8">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
