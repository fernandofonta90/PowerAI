import { TORRES } from "@/lib/torres";

// Navegación lateral por torre. En M1 solo OTC está disponible; el resto se
// muestra atenuado como "próximamente" para comunicar el roadmap.
export function TorreNav() {
  return (
    <nav aria-label="Torres del SSC" className="flex flex-col gap-1">
      {TORRES.map((torre) => (
        <div
          key={torre.codigo}
          className={`rounded-md px-3 py-2 text-sm ${
            torre.disponible
              ? "bg-brand text-white"
              : "text-slate-400"
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
