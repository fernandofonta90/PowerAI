import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CatalogoExplorador } from "@/components/CatalogoExplorador";
import type { TorreCatalogo } from "@/lib/types";

const CATALOGO: TorreCatalogo[] = [
  {
    torre: "OTC",
    nombre: "OTC — Order to Cash",
    estado_torre: "activa",
    categorias: [
      {
        nombre: "Cartera y cobranza",
        preguntas: [
          { id: "CU-00", texto: "¿Antigüedad de la cartera?", estado: "activa", ejecutable: true },
          { id: "CU-02", texto: "¿Concilian AR y GL?", estado: "proximamente", ejecutable: false },
        ],
      },
    ],
  },
  {
    torre: "PTP",
    nombre: "PTP — Procure to Pay",
    estado_torre: "proximamente",
    categorias: [
      {
        nombre: "Pagos a proveedores",
        preguntas: [
          { id: "AP-01", texto: "¿Top 10 proveedores?", estado: "proximamente", ejecutable: false },
        ],
      },
    ],
  },
];

const get = vi.fn();
vi.mock("@/lib/api", () => ({ api: { get: (ruta: string) => get(ruta) } }));

describe("CatalogoExplorador", () => {
  beforeEach(() => {
    get.mockReset();
    get.mockResolvedValue(CATALOGO);
  });

  it("con búsqueda vacía muestra TODAS las torres y preguntas (estado por defecto)", async () => {
    render(<CatalogoExplorador onElegir={() => {}} />);
    // Las dos torres del fixture, con sus preguntas activas y proximamente.
    expect(await screen.findByText("OTC — Order to Cash")).toBeInTheDocument();
    expect(screen.getByText("PTP — Procure to Pay")).toBeInTheDocument();
    expect(screen.getByText("¿Antigüedad de la cartera?")).toBeInTheDocument();
    expect(screen.getByText("¿Concilian AR y GL?")).toBeInTheDocument();
    expect(screen.getByText("¿Top 10 proveedores?")).toBeInTheDocument();
    // Nunca el mensaje de "sin coincidencias" con el campo vacío.
    expect(screen.queryByText(/No hay preguntas que coincidan/)).not.toBeInTheDocument();
  });

  it("las categorías colapsables se ven desde el inicio con su conteo", async () => {
    render(<CatalogoExplorador onElegir={() => {}} />);
    // La categoría y su conteo aparecen sin necesidad de buscar primero.
    expect(await screen.findByText("Cartera y cobranza")).toBeInTheDocument();
    expect(screen.getByText("1 de 2 disponibles")).toBeInTheDocument();
  });

  it("con texto SIN coincidencias muestra el mensaje vacío", async () => {
    render(<CatalogoExplorador onElegir={() => {}} />);
    await screen.findByText("¿Antigüedad de la cartera?");
    fireEvent.change(screen.getByLabelText("Buscar una pregunta"), {
      target: { value: "xyz no existe" },
    });
    expect(await screen.findByText(/No hay preguntas que coincidan/)).toBeInTheDocument();
  });

  it("una pregunta activa es clicable y envía al chat", async () => {
    const onElegir = vi.fn();
    render(<CatalogoExplorador onElegir={onElegir} />);
    const boton = await screen.findByRole("button", { name: "¿Antigüedad de la cartera?" });
    fireEvent.click(boton);
    expect(onElegir).toHaveBeenCalledWith("¿Antigüedad de la cartera?");
  });

  it("una pregunta 'proximamente' NO es clicable (no es un botón) y lleva badge", async () => {
    render(<CatalogoExplorador onElegir={() => {}} />);
    // El texto se muestra...
    const proxima = await screen.findByText("¿Concilian AR y GL?");
    // ...pero NO es (ni está dentro de) un botón ejecutable.
    expect(proxima.closest("button")).toBeNull();
    expect(
      screen.queryByRole("button", { name: "¿Concilian AR y GL?" }),
    ).not.toBeInTheDocument();
    // El badge "Próximamente" aparece (color no es el único portador de significado).
    expect(screen.getAllByText("Próximamente").length).toBeGreaterThan(0);
  });

  it("el buscador filtra por texto de la pregunta", async () => {
    render(<CatalogoExplorador onElegir={() => {}} />);
    await screen.findByText("¿Antigüedad de la cartera?");
    fireEvent.change(screen.getByLabelText("Buscar una pregunta"), {
      target: { value: "top 10" },
    });
    await waitFor(() => {
      expect(screen.queryByText("¿Antigüedad de la cartera?")).not.toBeInTheDocument();
    });
    expect(screen.getByText("¿Top 10 proveedores?")).toBeInTheDocument();
  });
});
