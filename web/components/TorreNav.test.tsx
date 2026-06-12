import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TorreNav } from "@/components/TorreNav";
import { TORRES } from "@/lib/torres";

describe("TorreNav", () => {
  it("renderiza las seis torres del SSC", () => {
    render(<TorreNav />);
    for (const torre of TORRES) {
      expect(screen.getByText(torre.codigo)).toBeInTheDocument();
    }
  });

  it("marca como próximamente las torres no disponibles", () => {
    render(<TorreNav />);
    const proximamente = screen.getAllByText("próximamente");
    const noDisponibles = TORRES.filter((t) => !t.disponible);
    expect(proximamente).toHaveLength(noDisponibles.length);
  });

  it("OTC está disponible en M1", () => {
    const otc = TORRES.find((t) => t.codigo === "OTC");
    expect(otc?.disponible).toBe(true);
  });
});
