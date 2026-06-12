export default function HomePage() {
  return (
    <section className="max-w-2xl">
      <h1 className="text-2xl font-bold text-slate-800">
        Bienvenido a PowerAI
      </h1>
      <p className="mt-3 text-slate-600">
        Plataforma de inteligencia analítica del SSC Finanzas LATAM. Carga los
        reportes de tu torre, pregunta en lenguaje natural y conoce siempre qué
        fuentes sustentan cada respuesta.
      </p>

      <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-slate-700">
          Fase 1 — MVP OTC
        </h2>
        <ul className="mt-2 list-inside list-disc text-sm text-slate-600">
          <li>Carga de reportes con plantillas (Aging OTC)</li>
          <li>Chat analítico con panel de fuentes</li>
          <li>Control de acceso por torre × país</li>
          <li>Bitácora de auditoría completa</li>
        </ul>
        <p className="mt-3 text-xs text-slate-400">
          M1 — Fundación: monorepo, entorno dev y autenticación mock operativos.
        </p>
      </div>
    </section>
  );
}
