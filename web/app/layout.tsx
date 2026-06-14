import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Header } from "@/components/Header";
import { UsuarioProvider } from "@/context/UsuarioContext";
import "./globals.css";

// Inter vía next/font: se descarga y auto-hospeda en build-time (sin CDN en runtime).
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: "PowerAI — SSC Finanzas LATAM",
  description:
    "Plataforma de inteligencia analítica del SSC Finanzas LATAM de ManpowerGroup.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={inter.variable}>
      <body className="font-sans">
        <UsuarioProvider>
          <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex flex-1 flex-col">{children}</main>
          </div>
        </UsuarioProvider>
      </body>
    </html>
  );
}
