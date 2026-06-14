import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BadgeFrescura } from "@/components/BadgeFrescura";

describe("BadgeFrescura", () => {
  it("muestra la etiqueta de cada estado de frescura", () => {
    render(<BadgeFrescura estado="al_dia" />);
    expect(screen.getByText("Al día")).toBeInTheDocument();
  });

  it("usa texto + icono (el color no es el único portador de significado)", () => {
    const { container } = render(<BadgeFrescura estado="vencido" />);
    expect(screen.getByText("Vencido")).toBeInTheDocument();
    // El icono (svg de lucide) acompaña al texto.
    expect(container.querySelector("svg")).toBeInTheDocument();
  });
});
