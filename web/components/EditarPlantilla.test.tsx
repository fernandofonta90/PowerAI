import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EditarPlantilla } from "@/components/EditarPlantilla";

const get = vi.fn();
const put = vi.fn();
vi.mock("@/lib/api", () => ({
  api: {
    get: (r: string) => get(r),
    put: (r: string, b: unknown) => put(r, b),
  },
  ApiError: class extends Error {},
}));

const PLANTILLA = {
  codigo: "otc_ar_abiertas",
  nombre: "AR abiertas",
  frecuencia: "semanal",
  columna_pais: "pais",
  columna_periodo: "periodo",
  columnas: [
    { nombre: "pais", tipo: "texto", requerida: true },
    { nombre: "monto", tipo: "decimal", requerida: true },
  ],
};

describe("EditarPlantilla", () => {
  beforeEach(() => {
    get.mockReset();
    put.mockReset();
    get.mockImplementation((ruta: string) => {
      if (ruta.includes("/impacto"))
        return Promise.resolve({ cargas_afectadas: 4 });
      return Promise.resolve([PLANTILLA]);
    });
  });

  it("muestra el aviso de impacto antes de cambiar el molde", async () => {
    render(<EditarPlantilla codigo="otc_ar_abiertas" torre="OTC" />);
    expect(await screen.findByText(/afecta a/)).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("guarda el molde con PUT", async () => {
    put.mockResolvedValueOnce({});
    render(<EditarPlantilla codigo="otc_ar_abiertas" torre="OTC" />);
    await screen.findByText(/afecta a/);
    fireEvent.click(
      screen.getByRole("button", { name: "Guardar cambios del molde" }),
    );
    await waitFor(() =>
      expect(put).toHaveBeenCalledWith(
        "/plantillas/otc_ar_abiertas",
        expect.any(Object),
      ),
    );
  });
});
