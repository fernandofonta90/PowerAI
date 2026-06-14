"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { fijarUsuario, usuarioActual } from "@/lib/api";
import { USUARIO_POR_DEFECTO } from "@/lib/usuarios";

type Ctx = { email: string; cambiar: (email: string) => void };

const UsuarioCtx = createContext<Ctx>({
  email: USUARIO_POR_DEFECTO,
  cambiar: () => {},
});

export function UsuarioProvider({ children }: { children: React.ReactNode }) {
  const [email, setEmail] = useState(USUARIO_POR_DEFECTO);

  // En cliente, hidrata desde localStorage tras el montaje.
  useEffect(() => {
    setEmail(usuarioActual());
  }, []);

  const cambiar = (nuevo: string) => {
    fijarUsuario(nuevo);
    setEmail(nuevo);
  };

  return <UsuarioCtx.Provider value={{ email, cambiar }}>{children}</UsuarioCtx.Provider>;
}

export const useUsuario = () => useContext(UsuarioCtx);
