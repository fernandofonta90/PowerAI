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
          <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-brand">PowerAI</span>
              <span className="text-sm text-slate-500">SSC Finanzas LATAM</span>
            </div>
            <span className="text-sm text-slate-500">mock: admin.otc@powerai.dev</span>
          </header>
          <div className="flex flex-1">
            <aside className="w-60 border-r border-slate-200 bg-white p-4">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
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
