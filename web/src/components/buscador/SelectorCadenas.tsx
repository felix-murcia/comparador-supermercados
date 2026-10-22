"use client";

import Image from "next/image";

import { Icono } from "@/components/ui/Icono";
import { CADENAS } from "@/lib/cadenas";
import { t } from "@/lib/i18n";

/**
 * Selector de supermercados: chips con el logo de cada cadena.
 *
 * Antes eran casillas de verificación dentro de una etiqueta. Ahora cada
 * cadena es un botón con `aria-pressed`, al estilo de los filtros de
 * Vercel: el estado seleccionado se ve en el propio chip (fondo azul
 * suave y marca de verificación) en lugar de depender de una casilla.
 */
export function SelectorCadenas({
  seleccionadas,
  onChange,
}: {
  seleccionadas: string[];
  onChange: (cadenas: string[]) => void;
}) {
  function alternar(slug: string) {
    onChange(
      seleccionadas.includes(slug)
        ? seleccionadas.filter((cadena) => cadena !== slug)
        : [...seleccionadas, slug],
    );
  }

  return (
    <div className="mt-6" role="group" aria-label={t("buscar.cadenas")}>
      <p className="text-sm text-gris">{t("buscar.cadenas")}</p>
      <div className="mt-2.5 flex flex-wrap gap-2">
        {CADENAS.map((cadena) => {
          const activa = seleccionadas.includes(cadena.slug);
          return (
            <button
              key={cadena.slug}
              type="button"
              aria-pressed={activa}
              onClick={() => alternar(cadena.slug)}
              className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors duration-150 ${
                activa
                  ? "border-primario bg-primario-suave text-primario-oscuro"
                  : "border-borde bg-white text-texto hover:border-borde-fuerte hover:bg-superficie"
              }`}
            >
              <Image
                src={`/logos/${cadena.slug}.svg`}
                alt=""
                width={20}
                height={20}
                className="h-5 w-5 shrink-0"
              />
              <span>{cadena.nombre}</span>
              {activa ? (
                <Icono nombre="check" className="h-4 w-4 shrink-0" />
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}
