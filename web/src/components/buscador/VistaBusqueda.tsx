"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BarraProgreso } from "@/components/buscador/BarraProgreso";
import { SelectorCadenas } from "@/components/buscador/SelectorCadenas";
import { t } from "@/lib/i18n";

type Props = {
  consulta: string;
  cadenas: string[];
  job: string | null;
  cacheHit: boolean;
};

type Resultado = {
  posicion: number;
  producto_cadena_id: string;
  nombre: string;
  cadena: string;
  precio_eur: string;
  precio_por_litro_kg: string | null;
};

type Estado = "progreso" | "resultados" | "fallida";

const INTERVALO_MS = 1500;

/**
 * Vista de resultados: si la búsqueda vino de caché se muestran de inmediato;
 * si no, se consulta el job hasta que termina y se cargan los resultados.
 */
export function VistaBusqueda({
  consulta: consultaInicial,
  cadenas: cadenasIniciales,
  job,
  cacheHit,
}: Props) {
  const router = useRouter();
  const [consulta, setConsulta] = useState(consultaInicial);
  const [cadenas, setCadenas] = useState<string[]>(cadenasIniciales);
  const [estado, setEstado] = useState<Estado>(
    cacheHit ? "resultados" : "progreso",
  );
  const [progreso, setProgreso] = useState(0);
  const [resultados, setResultados] = useState<Resultado[]>([]);
  const [error, setError] = useState<string | null>(null);

  const puedeBuscar = consulta.trim().length > 0 && cadenas.length > 0;

  async function cargarResultados() {
    const parametros = new URLSearchParams({ q: consultaInicial });
    for (const cadena of cadenasIniciales) {
      parametros.append("cadenas", cadena);
    }
    try {
      const respuesta = await fetch(`/api/comparar?${parametros.toString()}`);
      const datos = await respuesta.json();
      setResultados(Array.isArray(datos.resultados) ? datos.resultados : []);
    } catch {
      setError(t("buscar.error_resultados"));
    }
  }

  useEffect(() => {
    if (cacheHit) {
      void cargarResultados();
      return;
    }
    if (!job) {
      setEstado("fallida");
      return;
    }

    let cancelado = false;

    const consultar = async () => {
      try {
        const respuesta = await fetch(`/api/busquedas/${job}`);
        const datos = await respuesta.json();
        if (cancelado) {
          return;
        }
        if (typeof datos.progreso === "number") {
          setProgreso(datos.progreso);
        }
        if (datos.estado === "completada") {
          setEstado("resultados");
          void cargarResultados();
        } else if (datos.estado === "fallida") {
          setEstado("fallida");
        }
      } catch {
        // El siguiente tick reintenta la consulta.
      }
    };

    void consultar();
    const intervalo = setInterval(() => {
      void consultar();
    }, INTERVALO_MS);

    return () => {
      cancelado = true;
      clearInterval(intervalo);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job, cacheHit]);

  async function relanzar() {
    if (!puedeBuscar) {
      return;
    }
    setError(null);

    try {
      const respuesta = await fetch("/api/busquedas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: consulta.trim(), cadenas }),
      });
      const datos = await respuesta.json().catch(() => ({}));
      if (!respuesta.ok) {
        setError(t("buscar.error"));
        return;
      }

      const parametros = new URLSearchParams({ q: consulta.trim() });
      if (cadenas.length > 0) {
        parametros.set("cadenas", cadenas.join(","));
      }
      if (datos.job_id) {
        parametros.set("job", datos.job_id);
      }
      if (datos.cache_hit) {
        parametros.set("cache", "1");
      }
      router.push(`/buscar?${parametros.toString()}`);
      setEstado(datos.cache_hit ? "resultados" : "progreso");
      setProgreso(0);
    } catch {
      setError(t("buscar.error"));
    }
  }

  if (estado === "fallida") {
    return (
      <section className="mx-auto max-w-lectura text-center">
        <p role="alert" className="text-sm text-error">
          {t("buscar.error_busqueda")}
        </p>
        <button
          type="button"
          onClick={() => router.push("/")}
          className="mt-6 rounded-pill border border-borde px-5 py-2.5 text-sm hover:bg-primario-suave"
        >
          {t("buscar.volver")}
        </button>
      </section>
    );
  }

  if (estado === "progreso") {
    return (
      <section className="mx-auto max-w-lectura">
        <h1 className="text-center text-2xl font-medium text-texto">
          {t("buscar.buscando_titulo")}
        </h1>
        <p className="mt-2 text-center text-sm text-gris">{consultaInicial}</p>
        <div className="mt-8">
          <BarraProgreso progreso={progreso} />
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-contenido">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => router.push("/")}
          aria-label={t("buscar.volver")}
          className="rounded-pill p-2 text-gris hover:bg-primario-suave hover:text-texto"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>

        <form
          className="flex min-w-0 flex-1 gap-2"
          onSubmit={(evento) => {
            evento.preventDefault();
            void relanzar();
          }}
        >
          <label className="sr-only" htmlFor="q">
            {t("buscar.campo")}
          </label>
          <input
            id="q"
            name="q"
            type="search"
            value={consulta}
            onChange={(evento) => setConsulta(evento.target.value)}
            placeholder={t("buscar.placeholder")}
            autoComplete="off"
            className="min-w-0 flex-1 rounded-pill border border-borde px-4 py-2.5 text-sm text-texto placeholder:text-gris focus:border-primario"
          />
          <button
            type="submit"
            disabled={!puedeBuscar}
            className="rounded-pill bg-primario px-5 py-2.5 text-sm font-medium text-white hover:bg-primario-oscuro disabled:cursor-not-allowed disabled:bg-borde disabled:text-gris"
          >
            {t("buscar.comparar")}
          </button>
        </form>
      </div>

      <SelectorCadenas seleccionadas={cadenas} onChange={setCadenas} />

      {error ? (
        <p role="alert" className="mt-4 text-sm text-error">
          {error}
        </p>
      ) : null}

      {resultados.length === 0 ? (
        <p className="mt-10 text-center text-sm text-gris">
          {t("buscar.sin_resultados")}
        </p>
      ) : (
        <ul className="mt-6 space-y-3">
          {resultados.map((resultado) => (
            <li
              key={`${resultado.producto_cadena_id}-${resultado.cadena}`}
              className="rounded-tarjeta border border-borde p-4"
            >
              <div className="flex items-baseline gap-3">
                <span className="text-sm text-gris">#{resultado.posicion}</span>
                <span className="font-medium text-texto">{resultado.nombre}</span>
                <span className="ml-auto font-medium text-texto">
                  {resultado.precio_eur} €
                </span>
              </div>
              <p className="mt-1 text-sm text-gris">
                {resultado.cadena}
                {resultado.precio_por_litro_kg
                  ? ` · ${resultado.precio_por_litro_kg} €/kg-L`
                  : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
