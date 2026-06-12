// Catálogo de torres del SSC para la navegación. Espejo de app/domain/enums.py
// en el backend; en milestones posteriores se hidratará desde /me (acceso real).

export type Torre = {
  codigo: "OTC" | "PTP" | "RTR" | "QCI" | "CARE" | "HTR";
  nombre: string;
  disponible: boolean;
};

export const TORRES: Torre[] = [
  { codigo: "OTC", nombre: "Order to Cash", disponible: true },
  { codigo: "PTP", nombre: "Procure to Pay", disponible: false },
  { codigo: "RTR", nombre: "Record to Report", disponible: false },
  { codigo: "QCI", nombre: "Quality / Control", disponible: false },
  { codigo: "CARE", nombre: "Customer Care", disponible: false },
  { codigo: "HTR", nombre: "Hire to Retire", disponible: false },
];
