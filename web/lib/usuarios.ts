// Usuarios mock de desarrollo (coinciden con el seed del backend, app.scripts.seed_dev).
// En dev no hay Entra ID: el selector envía X-Mock-User en cada request.
// `puedeCargar` refleja el rol (uploader/admin); con Entra ID vendrá de /me.

export type UsuarioMock = {
  email: string;
  nombre: string;
  inicial: string;
  puedeCargar: boolean;
  // Torre de la que el usuario es admin (gating de UI; el backend valida el RBAC real).
  adminTorre?: string;
};

export const USUARIOS_MOCK: UsuarioMock[] = [
  {
    email: "admin.otc@powerai.dev",
    nombre: "Admin OTC",
    inicial: "AO",
    puedeCargar: true,
    adminTorre: "OTC",
  },
  {
    email: "uploader.mx@powerai.dev",
    nombre: "Cargador MX",
    inicial: "MX",
    puedeCargar: true,
  },
  {
    email: "consulta.co@powerai.dev",
    nombre: "Analista CO",
    inicial: "CO",
    puedeCargar: false,
  },
  {
    email: "multi.torre@powerai.dev",
    nombre: "Multi-torre",
    inicial: "MT",
    puedeCargar: false,
  },
];

export const USUARIO_POR_DEFECTO = USUARIOS_MOCK[1].email; // uploader.mx

export function buscarUsuario(email: string): UsuarioMock | undefined {
  return USUARIOS_MOCK.find((u) => u.email === email);
}
