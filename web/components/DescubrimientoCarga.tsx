"use client";

import { CheckCircle2, FileSpreadsheet, Upload } from "lucide-react";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import type {
  ColumnaSpec,
  CrearPlantillaInput,
  Inspeccion,
  PlantillaCandidata,
  PlantillaCreada,
  TipoColumna,
} from "@/lib/types";

const TIPOS: TipoColumna[] = ["texto", "entero", "decimal", "fecha"];

// Flujo de carga por descubrimiento (M11): subir → inspeccionar → si calza,
// guardar; si no, crear plantilla nueva (con su vista 1:1) o mapear a una candidata.
export function DescubrimientoCarga({ torre }: { torre: string }) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [pais, setPais] = useState("");
  const [periodo, setPeriodo] = useState("");
  const [insp, setInsp] = useState<Inspeccion | null>(null);
  const [modo, setModo] = useState<"crear" | "mapear" | null>(null);
  const [candidata, setCandidata] = useState<PlantillaCandidata | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [avisos, setAvisos] = useState<string[]>([]);

  function reset() {
    setInsp(null);
    setModo(null);
    setCandidata(null);
    setError(null);
    setOk(null);
    setAvisos([]);
  }

  async function inspeccionar() {
    if (!archivo) return;
    setOcupado(true);
    reset();
    try {
      const form = new FormData();
      form.append("torre", torre);
      form.append("archivo", archivo);
      setInsp(await api.postForm<Inspeccion>("/cargas/inspeccionar", form));
    } catch (e: unknown) {
      setError(
        e instanceof ApiError
          ? `No se pudo inspeccionar (${e.status}).`
          : "Error al inspeccionar.",
      );
    } finally {
      setOcupado(false);
    }
  }

  async function guardarCarga(
    plantillaCodigo: string,
    mapeo?: Record<string, string>,
  ) {
    if (!archivo) return;
    setOcupado(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("plantilla_codigo", plantillaCodigo);
      form.append("pais", pais.trim().toUpperCase());
      form.append("periodo", periodo.trim());
      form.append("archivo", archivo);
      if (mapeo) form.append("mapeo", JSON.stringify(mapeo));
      await api.postForm("/cargas", form);
      setOk(
        `Carga aceptada y en proceso contra la plantilla «${plantillaCodigo}».`,
      );
      setModo(null);
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 422) {
        setError(
          "La carga fue rechazada: revisa que las columnas y el país/periodo coincidan.",
        );
      } else {
        setError(
          e instanceof ApiError
            ? `No se pudo guardar (${e.status}).`
            : "Error al guardar.",
        );
      }
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Campo etiqueta="País (ISO 2)">
          <input
            value={pais}
            onChange={(e) => setPais(e.target.value)}
            placeholder="MX"
            maxLength={2}
            className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-[14px] uppercase focus:outline-none focus:ring-1 focus:ring-brand-600"
          />
        </Campo>
        <Campo etiqueta="Periodo">
          <input
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            placeholder="2026-05"
            className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-[14px] focus:outline-none focus:ring-1 focus:ring-brand-600"
          />
        </Campo>
        <Campo etiqueta="Archivo (.csv / .xlsx)">
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={(e) => {
              setArchivo(e.target.files?.[0] ?? null);
              reset();
            }}
            className="w-full text-[12.5px] text-neutral-600 file:mr-2 file:rounded-pill file:border-0 file:bg-brand-100 file:px-3 file:py-1 file:text-[12px] file:text-brand-800"
          />
        </Campo>
      </div>

      <button
        type="button"
        onClick={inspeccionar}
        disabled={ocupado || !archivo}
        className="inline-flex items-center gap-1.5 rounded-pill bg-brand-600 px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-40"
      >
        <Upload className="h-4 w-4" aria-hidden />
        {ocupado && !insp ? "Inspeccionando…" : "Inspeccionar archivo"}
      </button>

      {error && <p className="text-[13px] text-danger-700">{error}</p>}
      {ok && (
        <p className="flex items-center gap-1.5 text-[13px] text-success-700">
          <CheckCircle2 className="h-4 w-4" aria-hidden />
          {ok}
        </p>
      )}
      {avisos.length > 0 && (
        <ul className="rounded-lg border border-warning-600/30 bg-warning-600/5 p-3 text-[12.5px] text-warning-700">
          {avisos.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      )}

      {insp && (
        <>
          <Vista insp={insp} />
          {insp.calce ? (
            <div className="rounded-xl border border-success-600/30 bg-success-600/5 p-4">
              <p className="text-[13.5px] text-neutral-700">
                El archivo <strong>calza</strong> con la plantilla «
                {insp.calce.nombre}».
              </p>
              <button
                type="button"
                onClick={() => insp.calce && guardarCarga(insp.calce.codigo)}
                disabled={ocupado || !pais || !periodo}
                className="mt-2 rounded-pill bg-brand-600 px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-40"
              >
                Guardar carga
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-[13.5px] text-neutral-700">
                Ninguna plantilla calza tal cual. Crea una nueva o mapea a una
                existente.
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setModo("crear");
                    setCandidata(null);
                  }}
                  className="rounded-pill border border-brand-200 px-4 py-2 text-[13px] font-medium text-brand-800"
                >
                  Crear plantilla nueva
                </button>
                {insp.candidatas
                  .filter((c) => c.extra.length > 0 || c.faltantes.length > 0)
                  .slice(0, 3)
                  .map((c) => (
                    <button
                      key={c.codigo}
                      type="button"
                      onClick={() => {
                        setModo("mapear");
                        setCandidata(c);
                      }}
                      className="rounded-pill border border-neutral-200 px-4 py-2 text-[13px] text-neutral-700"
                    >
                      Mapear a «{c.nombre}»
                    </button>
                  ))}
              </div>
            </div>
          )}
        </>
      )}

      {modo === "crear" && insp && (
        <CrearPlantilla
          torre={torre}
          columnas={insp.columnas}
          tiposSugeridos={insp.tipos_sugeridos}
          ocupado={ocupado}
          onCrear={async (input) => {
            setOcupado(true);
            setError(null);
            try {
              const creada = await api.post<PlantillaCreada>(
                "/plantillas",
                input,
              );
              setAvisos(creada.avisos ?? []);
              await guardarCarga(creada.plantilla.codigo);
              setModo(null);
            } catch (e: unknown) {
              setError(
                e instanceof ApiError
                  ? `No se pudo crear (${e.status}).`
                  : "Error al crear.",
              );
              setOcupado(false);
            }
          }}
        />
      )}

      {modo === "mapear" && candidata && insp && (
        <Mapear
          candidata={candidata}
          columnasArchivo={insp.columnas}
          ocupado={ocupado || !pais || !periodo}
          onMapear={(mapeo) => guardarCarga(candidata.codigo, mapeo)}
        />
      )}
    </div>
  );
}

function Vista({ insp }: { insp: Inspeccion }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-neutral-100">
      <table className="w-full text-left text-[12.5px]">
        <thead className="bg-surface-100 text-neutral-500">
          <tr>
            {insp.columnas.map((c) => (
              <th key={c} className="whitespace-nowrap px-3 py-1.5 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {insp.filas_muestra.map((fila, i) => (
            <tr key={i} className="border-t border-neutral-100">
              {fila.map((v, j) => (
                <td
                  key={j}
                  className="whitespace-nowrap px-3 py-1.5 text-neutral-700"
                >
                  {v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CrearPlantilla({
  torre,
  columnas,
  tiposSugeridos,
  ocupado,
  onCrear,
}: {
  torre: string;
  columnas: string[];
  tiposSugeridos: Record<string, TipoColumna>;
  ocupado: boolean;
  onCrear: (input: CrearPlantillaInput) => void;
}) {
  // Pre-selecciona el tipo inferido por el backend (el usuario solo ajusta lo que esté mal).
  const [tipos, setTipos] = useState<Record<string, TipoColumna>>(
    Object.fromEntries(columnas.map((c) => [c, tiposSugeridos[c] ?? "texto"])),
  );
  const [descs, setDescs] = useState<Record<string, string>>({});
  const [vistaNombre, setVistaNombre] = useState("");
  const [vistaDesc, setVistaDesc] = useState("");
  // País opcional: por defecto "" = sin columna (se usa el país declarado al
  // cargar). NO autoseleccionar la primera columna (eso tomaba "Business Unit").
  const [colPais, setColPais] = useState("");
  // Periodo opcional: por defecto la columna llamada "periodo" si existe; si no,
  // "" = sin columna (se usa el periodo declarado al cargar).
  const [colPeriodo, setColPeriodo] = useState(
    columnas.find((c) => /periodo|period/i.test(c)) ?? "",
  );

  function enviar() {
    const cols: ColumnaSpec[] = columnas.map((c) => ({
      nombre: c,
      tipo: tipos[c] ?? "texto",
      requerida: true,
      descripcion: descs[c] ?? "",
    }));
    onCrear({
      torre,
      nombre: vistaNombre,
      frecuencia: "mensual",
      columnas: cols,
      columna_pais: colPais || null,
      columna_periodo: colPeriodo || null,
      vista_nombre_negocio: vistaNombre,
      vista_descripcion: vistaDesc,
      descripciones_columnas: descs,
    });
  }

  return (
    <div className="space-y-4 rounded-xl border border-brand-100 bg-brand-50/50 p-4">
      <h3 className="flex items-center gap-1.5 text-[14px] font-medium text-neutral-900">
        <FileSpreadsheet className="h-4 w-4 text-brand-600" aria-hidden />
        Definir plantilla nueva
      </h3>
      <Campo etiqueta="Nombre de negocio de la vista (obligatorio)">
        <input
          value={vistaNombre}
          onChange={(e) => setVistaNombre(e.target.value)}
          placeholder="Ej. Cartera abierta"
          className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-[14px] focus:outline-none focus:ring-1 focus:ring-brand-600"
        />
      </Campo>
      <Campo etiqueta="Descripción de la vista (recomendada)">
        <input
          value={vistaDesc}
          onChange={(e) => setVistaDesc(e.target.value)}
          placeholder="Qué contiene y para qué sirve"
          className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-[14px] focus:outline-none focus:ring-1 focus:ring-brand-600"
        />
      </Campo>

      <div className="space-y-2">
        <p className="text-[13px] font-medium text-neutral-800">Columnas</p>
        {columnas.map((c) => (
          <div
            key={c}
            className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_120px_2fr]"
          >
            <span className="self-center text-[13px] text-neutral-700">
              {c}
            </span>
            <select
              aria-label={`Tipo de ${c}`}
              value={tipos[c]}
              onChange={(e) =>
                setTipos({ ...tipos, [c]: e.target.value as TipoColumna })
              }
              className="rounded-lg border border-neutral-200 px-2 py-1.5 text-[13px]"
            >
              {TIPOS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <input
              value={descs[c] ?? ""}
              onChange={(e) => setDescs({ ...descs, [c]: e.target.value })}
              placeholder="ej. saldo pendiente de cobro por factura"
              className="rounded-lg border border-neutral-200 px-2 py-1.5 text-[13px]"
            />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Campo etiqueta="Columna de país (opcional)">
          <select
            value={colPais}
            onChange={(e) => setColPais(e.target.value)}
            className="w-full rounded-lg border border-neutral-200 px-2 py-1.5 text-[13px]"
          >
            <option value="">— sin columna (uso el país declarado) —</option>
            {columnas.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </Campo>
        <Campo etiqueta="Columna de periodo (opcional)">
          <select
            value={colPeriodo}
            onChange={(e) => setColPeriodo(e.target.value)}
            className="w-full rounded-lg border border-neutral-200 px-2 py-1.5 text-[13px]"
          >
            <option value="">— sin columna (uso el periodo declarado) —</option>
            {columnas.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </Campo>
      </div>

      <button
        type="button"
        onClick={enviar}
        disabled={ocupado || !vistaNombre}
        className="rounded-pill bg-brand-600 px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-40"
      >
        Crear plantilla y guardar carga
      </button>
    </div>
  );
}

function Mapear({
  candidata,
  columnasArchivo,
  ocupado,
  onMapear,
}: {
  candidata: PlantillaCandidata;
  columnasArchivo: string[];
  ocupado: boolean;
  onMapear: (mapeo: Record<string, string>) => void;
}) {
  const [mapeo, setMapeo] = useState<Record<string, string>>(
    Object.fromEntries(
      candidata.columnas_esperadas.map((c) => [
        c,
        columnasArchivo.includes(c) ? c : "",
      ]),
    ),
  );

  return (
    <div className="space-y-3 rounded-xl border border-neutral-200 p-4">
      <h3 className="text-[14px] font-medium text-neutral-900">
        Mapear columnas a «{candidata.nombre}»
      </h3>
      <p className="text-[12.5px] text-neutral-500">
        Acomoda este archivo a la plantilla. Esto no cambia el molde de la
        plantilla.
      </p>
      {candidata.columnas_esperadas.map((esperada) => (
        <div
          key={esperada}
          className="grid grid-cols-[1fr_1fr] items-center gap-2"
        >
          <span className="text-[13px] text-neutral-700">{esperada}</span>
          <select
            aria-label={`Mapeo de ${esperada}`}
            value={mapeo[esperada] ?? ""}
            onChange={(e) => setMapeo({ ...mapeo, [esperada]: e.target.value })}
            className="rounded-lg border border-neutral-200 px-2 py-1.5 text-[13px]"
          >
            <option value="">— sin mapear —</option>
            {columnasArchivo.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      ))}
      <button
        type="button"
        onClick={() =>
          onMapear(
            Object.fromEntries(Object.entries(mapeo).filter(([, v]) => v)),
          )
        }
        disabled={ocupado}
        className="rounded-pill bg-brand-600 px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-40"
      >
        Guardar carga con este mapeo
      </button>
    </div>
  );
}

function Campo({
  etiqueta,
  children,
}: {
  etiqueta: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1 block text-[13px] font-medium text-neutral-800">
        {etiqueta}
      </label>
      {children}
    </div>
  );
}
