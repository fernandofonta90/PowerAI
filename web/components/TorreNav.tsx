import { TORRES } from "@/lib/torres";

// Navegación lateral por torre. En M1 solo OTC está disponible; el resto se
// muestra atenuado como "próximamente" para comunicar el roadmap.
// Ítem activo: brand-800 con borde izquierdo brand-200 (patrón sidebar del
// design system v2).
export function TorreNav() {
  return (
    <nav aria-label="Torres del SSC" className="flex flex-col gap-1">
      {TORRES.map((torre) => (
        <div
          key={torre.codigo}
          className={`rounded-md px-3 py-2 text-sm ${
            torre.disponible
              ? "border-l-2 border-brand-200 bg-brand-800 text-white"
              : "text-neutral-400"
          }`}
        >
          <span className="font-semibold">{torre.codigo}</span>
          <span className="ml-2">{torre.nombre}</span>
          {!torre.disponible && (
            <span className="ml-2 text-xs italic">próximamente</span>
          )}
        </div>
      ))}
    </nav>
  );
}
