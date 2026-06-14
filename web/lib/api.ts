// Cliente HTTP de la API de PowerAI. Inyecta el usuario mock (X-Mock-User) leído
// de localStorage en cada request (en dev no hay Entra ID).

import { USUARIO_POR_DEFECTO } from "@/lib/usuarios";

const BASE = process.env.POWERAI_API_URL ?? "http://localhost:8000";
const CLAVE_USUARIO = "powerai_mock_user";

export function usuarioActual(): string {
  if (typeof window === "undefined") return USUARIO_POR_DEFECTO;
  return window.localStorage.getItem(CLAVE_USUARIO) ?? USUARIO_POR_DEFECTO;
}

export function fijarUsuario(email: string): void {
  window.localStorage.setItem(CLAVE_USUARIO, email);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(ruta: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${ruta}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Mock-User": usuarioActual(),
      ...(init?.headers ?? {}),
    },
  });
  if (!resp.ok) {
    throw new ApiError(resp.status, `${resp.status} ${resp.statusText}`);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  get: <T>(ruta: string) => request<T>(ruta),
  post: <T>(ruta: string, cuerpo?: unknown) =>
    request<T>(ruta, { method: "POST", body: JSON.stringify(cuerpo ?? {}) }),
};
