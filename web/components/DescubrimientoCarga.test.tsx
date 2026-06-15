import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DescubrimientoCarga } from "@/components/DescubrimientoCarga";
import type { Inspeccion } from "@/lib/types";

const postForm = vi.fn();
const post = vi.fn();
vi.mock("@/lib/api", () => ({
  api: {
    postForm: (ruta: string, form: FormData) => postForm(ruta, form),
    post: (ruta: string, body: unknown) => post(ruta, body),
  },
  ApiError: class extends Error {},
}));

const CALCE: Inspeccion = {
  columnas: ["pais", "periodo", "monto"],
  filas_muestra: [["MX", "2026-05", "100.00"]],
  calce: {
    codigo: "otc_ar_abiertas",
    nombre: "AR abiertas",
    columnas_esperadas: ["pais", "periodo", "monto"],
    columna_pais: "pais",
    columna_periodo: "periodo",
    faltantes: [],
    extra: [],
    calza: true,
  },
  candidatas: [],
};

const SIN_CALCE: Inspeccion = {
  columnas: ["pais", "periodo", "importe"],
  filas_muestra: [["MX", "2026-05", "100.00"]],
  calce: null,
  candidatas: [],
};

function subirArchivo() {
  const input = document.querySelector(
    'input[type="file"]',
  ) as HTMLInputElement;
  const file = new File(
    ["pais,periodo,monto\nMX,2026-05,100.00\n"],
    "datos.csv",
    {
      type: "text/csv",
    },
  );
  fireEvent.change(input, { target: { files: [file] } });
}

describe("DescubrimientoCarga", () => {
  beforeEach(() => {
    postForm.mockReset();
    post.mockReset();
  });

  it("si el archivo calza, ofrece guardar la carga", async () => {
    postForm.mockResolvedValueOnce(CALCE);
    render(<DescubrimientoCarga torre="OTC" />);
    fireEvent.change(screen.getByPlaceholderText("MX"), {
      target: { value: "MX" },
    });
    fireEvent.change(screen.getByPlaceholderText("2026-05"), {
      target: { value: "2026-05" },
    });
    subirArchivo();
    fireEvent.click(
      screen.getByRole("button", { name: /Inspeccionar archivo/ }),
    );

    expect(await screen.findByText(/calza/)).toBeInTheDocument();
    postForm.mockResolvedValueOnce({});
    fireEvent.click(screen.getByRole("button", { name: "Guardar carga" }));
    await waitFor(() =>
      expect(postForm).toHaveBeenCalledWith("/cargas", expect.any(FormData)),
    );
  });

  it("si no calza, crear plantilla nueva llama a /plantillas y luego guarda la carga", async () => {
    postForm.mockResolvedValueOnce(SIN_CALCE);
    render(<DescubrimientoCarga torre="OTC" />);
    fireEvent.change(screen.getByPlaceholderText("MX"), {
      target: { value: "MX" },
    });
    fireEvent.change(screen.getByPlaceholderText("2026-05"), {
      target: { value: "2026-05" },
    });
    subirArchivo();
    fireEvent.click(
      screen.getByRole("button", { name: /Inspeccionar archivo/ }),
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "Crear plantilla nueva" }),
    );
    // El nombre de negocio de la vista es obligatorio.
    fireEvent.change(screen.getByPlaceholderText("Ej. Cartera abierta"), {
      target: { value: "Pagos a proveedores" },
    });
    post.mockResolvedValueOnce({
      plantilla: {
        codigo: "otc_pagos_a_proveedores",
        nombre: "x",
        torre: "OTC",
      },
      vista: {
        nombre: "pagos_a_proveedores",
        titulo: "x",
        plantilla_codigo: "otc_pagos_a_proveedores",
      },
    });
    postForm.mockResolvedValueOnce({});

    fireEvent.click(
      screen.getByRole("button", { name: "Crear plantilla y guardar carga" }),
    );
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/plantillas", expect.any(Object)),
    );
    await waitFor(() =>
      expect(postForm).toHaveBeenCalledWith("/cargas", expect.any(FormData)),
    );
    // La columna 'importe' viaja en la definición (no se inventa nada).
    const enviado = post.mock.calls[0][1] as { columnas: { nombre: string }[] };
    expect(enviado.columnas.map((c) => c.nombre)).toContain("importe");
  });
});
