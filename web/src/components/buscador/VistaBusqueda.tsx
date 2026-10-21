"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { IndicadorBusqueda } from "@/components/buscador/IndicadorBusqueda";
import { PanelFiltros } from "@/components/buscador/PanelFiltros";
import { SelectorCadenas } from "@/components/buscador/SelectorCadenas";
import { CardProducto } from "@/components/producto/CardProducto";
import { t } from "@/lib/i18n";
import {
  aplicarFiltros,
  opcionesDisponibles,
  FILTROS_INICIALES,
} from "@/lib/filtros";
import type { Filtros, ResultadoComparacion } from "@/lib/filtros";

type Props = {
  consulta: string;
  cadenas: string[];
  job: string | null;
  cacheHit: boolean;
  resultadosIniciales?: ResultadoComparacion[];
  filtrosIniciales?: Filtros;
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
  resultadosIniciales = [],
  filtrosIniciales = FILTROS_INICIALES,
}: Props) {
  const router = useRouter();
  const [consulta, setConsulta] = useState(consultaInicial);
  const [cadenas, setCadenas] = useState<string[]>(cadenasIniciales);
  const [estado, setEstado] = useState<Estado>(
    cacheHit ? "resultados" : "progreso",
  );
  const [resultados, setResultados] =
    useState<ResultadoComparacion[]>(resultadosIniciales);
  const [filtros, setFiltros] = useState<Filtros>(filtrosIniciales);
  const [error, setError] = useState<string | null>(null);

  const puedeBuscar = consulta.trim().length > 0 && cadenas.length > 0;
  const visibles = useMemo(
    () => aplicarFiltros(resultados, filtros),
    [resultados, filtros],
  );
  const opciones = useMemo(
    () => opcionesDisponibles(resultados),
    [resultados],
  );

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
      // Los resultados ya vienen del servidor en el HTML inicial.
      return;
    }
    if (!job) {
      setEstado("fallida");
      return;
    }

    let cancelado = false;

    // Cada consulta se agenda con setTimeout (y no setInterval) para poder
    // alargar la espera cuando el servidor responde 429.
    let espera = INTERVALO_MS;
    let temporizador: ReturnType<typeof setTimeout> | undefined;

    const consultar = async () => {
      try {
        const respuesta = await fetch(`/api/busquedas/${job}`);
        if (cancelado) {
          return;
        }
        // Un 429 no es un fallo del job: se ha alcanzado el límite. Se
        // espera lo que indica el servidor y se reintenta, en vez de seguir
        // golpeando la API cada 1,5 s.
        if (respuesta.status === 429) {
          espera = Math.max(
            INTERVALO_MS,
            Number(respuesta.headers.get("retry-after") ?? 0) * 1000,
          );
          return;
        }
        if (!respuesta.ok) {
          setEstado("fallida");
          return;
        }
        const datos = await respuesta.json();
        if (cancelado) {
          return;
        }
        if (datos.estado === "completada") {
          setEstado("resultados");
          void cargarResultados();
          return;
        }
        if (datos.estado === "fallida") {
          setEstado("fallida");
          return;
        }
      } catch {
        // El siguiente tick reintenta la consulta.
      }
      espera = INTERVALO_MS;
    };

    const agendar = () => {
      temporizador = setTimeout(() => {
        void consultar().finally(agendar);
      }, espera);
    };

    void consultar().finally(agendar);

    return () => {
      cancelado = true;
      if (temporizador !== undefined) {
        clearTimeout(temporizador);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job, cacheHit]);

  function parametrosUrl(nuevos: Filtros): string {
    const parametros = new URLSearchParams({ q: consultaInicial });
    if (cadenasIniciales.length > 0) {
      parametros.set("cadenas", cadenasIniciales.join(","));
    }
    if (job) {
      parametros.set("job", job);
    }
    if (cacheHit) {
      parametros.set("cache", "1");
    }
    if (nuevos.orden !== FILTROS_INICIALES.orden) {
      parametros.set("orden", nuevos.orden);
    }
    if (nuevos.precioMin !== null) {
      parametros.set("precio_min", String(nuevos.precioMin));
    }
    if (nuevos.precioMax !== null) {
      parametros.set("precio_max", String(nuevos.precioMax));
    }
    if (nuevos.marca) {
      parametros.set("marca", nuevos.marca);
    }
    if (nuevos.categoria) {
      parametros.set("categoria", nuevos.categoria);
    }
    if (nuevos.soloConStock) {
      parametros.set("solo_con_stock", "1");
    }
    return parametros.toString();
  }

  function cambiarFiltros(nuevos: Filtros) {
    setFiltros(nuevos);
    router.replace(`/buscar?${parametrosUrl(nuevos)}`, { scroll: false });
  }

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
          <IndicadorBusqueda cadenas={cadenasIniciales} />
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
            className="min-w-0 flex-1 rounded-pill border border-borde-fuerte px-4 py-2.5 text-sm text-texto placeholder:text-gris focus:border-primario"
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

      <PanelFiltros
        filtros={filtros}
        marcas={opciones.marcas}
        categorias={opciones.categorias}
        onChange={cambiarFiltros}
        onLimpiar={() => cambiarFiltros(FILTROS_INICIALES)}
      />

      <p className="mt-3 text-sm text-gris">
        {t("filtros.contador", {
          visibles: visibles.length,
          total: resultados.length,
        })}
      </p>

      {error ? (
        <p role="alert" className="mt-4 text-sm text-error">
          {error}
        </p>
      ) : null}

      {visibles.length === 0 ? (
        <p className="mt-10 text-center text-sm text-gris">
          {t("buscar.sin_resultados")}
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {visibles.map((resultado) => (
            <li key={`${resultado.producto_cadena_id}-${resultado.cadena}`}>
              <CardProducto {...resultado} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
