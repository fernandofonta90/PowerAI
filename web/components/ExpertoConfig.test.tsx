import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExpertoConfig } from "@/components/ExpertoConfig";
import type { ActivacionExperto, ExpertoScreen } from "@/lib/types";

const PANTALLA: ExpertoScreen = {
  torre: "OTC",
  activo: {
    nombre: "Experto OTC",
    identidad: "Soy el experto OTC.",
    instrucciones_formato: "Sé conciso.",
    fuentes: ["ar_abiertas"],
    estado: "activo",
    version: 1,
  },
  borrador: null,
  vistas_torre: [
    {
      nombre: "ar_abiertas",
      titulo: "Cartera abierta",
      descripcion: "Facturas por cobrar.",
    },
    {
      nombre: "revenue_recon",
      titulo: "Conciliación",
      descripcion: "Ingreso vs reconocido.",
    },
  ],
  garantias_estructurales: [
    "Seguridad a nivel de fila (torre × país). No es configurable.",
    "Text-to-SQL gobernado sobre vistas curadas. No es configurable.",
    "Honestidad ante métricas no soportadas. No es configurable.",
  ],
};

const get = vi.fn();
const post = vi.fn();
const put = vi.fn();
vi.mock("@/lib/api", () => ({
  api: {
    get: (ruta: string) => get(ruta),
    post: (ruta: string, body: unknown) => post(ruta, body),
    put: (ruta: string, body: unknown) => put(ruta, body),
  },
  ApiError: class extends Error {},
}));

describe("ExpertoConfig", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    put.mockReset();
    get.mockResolvedValue(PANTALLA);
  });

  it("muestra las garantías estructurales como fijas (transparencia)", async () => {
    render(<ExpertoConfig torre="OTC" />);
    expect(
      await screen.findByText(
        /Garantías fijas del sistema \(no configurables\)/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Seguridad a nivel de fila/)).toBeInTheDocument();
  });

  it("precarga la config activa (identidad y fuentes seleccionadas)", async () => {
    render(<ExpertoConfig torre="OTC" />);
    expect(
      await screen.findByDisplayValue("Soy el experto OTC."),
    ).toBeInTheDocument();
    const checks = screen.getAllByRole("checkbox") as HTMLInputElement[];
    const cartera = checks.find((c) =>
      c.closest("label")?.textContent?.includes("Cartera abierta"),
    );
    expect(cartera?.checked).toBe(true);
  });

  it("al validar muestra el resultado de los evals y NO activa si caen", async () => {
    const fallo: ActivacionExperto = {
      activado: false,
      motivo:
        "La configuración no se activó: los evals dieron 40.0%, por debajo del umbral.",
      version: null,
      reporte: {
        total: 5,
        aprobadas: 2,
        tasa: 0.4,
        fallos: [
          {
            id: "otc-aging-total",
            fraseo: "¿Total?",
            motivo: "datos no coinciden",
          },
        ],
      },
    };
    post.mockResolvedValue(fallo);
    render(<ExpertoConfig torre="OTC" />);
    await screen.findByDisplayValue("Soy el experto OTC.");
    fireEvent.click(
      screen.getByRole("button", { name: /Guardar y validar con evals/ }),
    );
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith(
        "/torres/OTC/experto/activar",
        expect.any(Object),
      ),
    );
    expect(await screen.findByText(/no se activó/)).toBeInTheDocument();
    expect(screen.getByText(/2\/5 aprobadas \(40.0%\)/)).toBeInTheDocument();
  });

  it("guardar borrador usa PUT y no activa", async () => {
    put.mockResolvedValue({});
    render(<ExpertoConfig torre="OTC" />);
    await screen.findByDisplayValue("Soy el experto OTC.");
    fireEvent.click(screen.getByRole("button", { name: "Guardar borrador" }));
    await waitFor(() =>
      expect(put).toHaveBeenCalledWith(
        "/torres/OTC/experto/borrador",
        expect.any(Object),
      ),
    );
    expect(await screen.findByText(/Aún no está activo/)).toBeInTheDocument();
  });
});
