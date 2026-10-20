"use client";

import Image from "next/image";

import { CADENAS } from "@/lib/cadenas";
import { t } from "@/lib/i18n";

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
    <fieldset className="mt-6">
      <legend className="text-sm text-gris">{t("buscar.cadenas")}</legend>
      <div className="mt-3 flex flex-wrap gap-2">
        {CADENAS.map((cadena) => {
          const activa = seleccionadas.includes(cadena.slug);
          return (
            <label
              key={cadena.slug}
              className={`flex cursor-pointer items-center gap-2 rounded-pill border px-3 py-2 text-sm ${
                activa
                  ? "border-primario bg-primario-suave text-primario-oscuro"
                  : "border-borde bg-white text-texto hover:bg-primario-suave"
              }`}
            >
              <input
                type="checkbox"
                className="h-4 w-4 accent-primario"
                checked={activa}
                onChange={() => alternar(cadena.slug)}
              />
              <Image
                src={`/logos/${cadena.slug}.svg`}
                alt={cadena.nombre}
                width={24}
                height={24}
                className="h-6 w-6"
              />
              <span>{cadena.nombre}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
