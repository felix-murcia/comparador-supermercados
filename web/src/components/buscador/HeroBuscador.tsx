"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { CampoBusqueda } from "@/components/buscador/CampoBusqueda";
import { SelectorCadenas } from "@/components/buscador/SelectorCadenas";
import { t } from "@/lib/i18n";

/**
 * Buscador de la portada: consulta, cadenas a comparar y botón de
 * búsqueda. El botón se habilita cuando hay consulta y al menos una cadena.
 */
export function HeroBuscador() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [cadenas, setCadenas] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lanzando, setLanzando] = useState(false);

  const consulta = query.trim();
  const puedeBuscar = consulta.length > 0 && cadenas.length > 0 && !lanzando;

  async function buscar() {
    if (!puedeBuscar) {
      return;
    }
    setLanzando(true);
    setError(null);

    try {
      const respuesta = await fetch("/api/busquedas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: consulta, cadenas }),
      });
      const datos = await respuesta.json().catch(() => ({}));

      if (!respuesta.ok) {
        setError(t("buscar.error"));
        return;
      }

      const parametros = new URLSearchParams({ q: consulta });
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
    } catch {
      setError(t("buscar.error"));
    } finally {
      setLanzando(false);
    }
  }

  return (
    <section className="mx-auto flex max-w-lectura flex-col items-center pt-12">
      <h1 className="text-center text-3xl font-medium text-texto">
        {t("inicio.titulo")}
      </h1>
      <p className="mt-3 text-center text-gris">{t("inicio.subtitulo")}</p>

      <form
        className="mt-8 w-full"
        onSubmit={(evento) => {
          evento.preventDefault();
          void buscar();
        }}
      >
        <CampoBusqueda
          id="q"
          name="q"
          value={query}
          onChange={(evento) => setQuery(evento.target.value)}
          placeholder={t("buscar.placeholder")}
        />

        <SelectorCadenas seleccionadas={cadenas} onChange={setCadenas} />

        <button
          type="submit"
          disabled={!puedeBuscar}
          className="mt-6 w-full rounded-lg bg-primario px-5 py-2.5 text-sm font-medium text-white transition-colors duration-150 hover:bg-primario-oscuro disabled:cursor-not-allowed disabled:bg-superficie-activa disabled:text-gris"
        >
          {lanzando ? t("buscar.buscando") : t("buscar.comparar")}
        </button>
      </form>

      {error ? (
        <p role="alert" className="mt-4 text-sm text-error">
          {error}
        </p>
      ) : null}
    </section>
  );
}
