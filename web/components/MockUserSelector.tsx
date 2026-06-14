"use client";

import { useUsuario } from "@/context/UsuarioContext";
import { USUARIOS_MOCK } from "@/lib/usuarios";

// Selector de usuario mock (solo dev). Cambia X-Mock-User y persiste la selección.
export function MockUserSelector() {
  const { email, cambiar } = useUsuario();
  return (
    <label className="flex items-center gap-2 text-xs text-brand-100">
      <span className="sr-only">Usuario de prueba</span>
      <span aria-hidden>dev:</span>
      <select
        aria-label="Seleccionar usuario de prueba"
        value={email}
        onChange={(e) => cambiar(e.target.value)}
        className="rounded-pill border border-brand-200/40 bg-brand-800 px-3 py-1 text-xs text-white focus:outline-none focus:ring-2 focus:ring-brand-200"
      >
        {USUARIOS_MOCK.map((u) => (
          <option key={u.email} value={u.email}>
            {u.nombre}
          </option>
        ))}
      </select>
    </label>
  );
}
