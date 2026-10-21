"use client";

import { nombreCadena } from "@/lib/cadenas";
import { t } from "@/lib/i18n";

/**
 * Indicador de carga mientras la búsqueda se procesa.
 *
 * Antes era una barra de progreso, pero el porcentaje solo avanza al
 * terminar cada cadena: con una sola cadena saltaba de 0 a 100 de golpe y
 * no medía nada. Un spinner indeterminado es más honesto, y el texto
 * indica en qué supermercados se está buscando.
 */
export function IndicadorBusqueda({ cadenas }: { cadenas: string[] }) {
  const nombres = cadenas.map(nombreCadena);
  const resumen =
    nombres.length > 0
      ? t("buscar.buscando_en", { cadenas: nombres.join(", ") })
      : t("buscar.buscando");

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col items-center gap-4 text-center"
    >
      {/* El anillo gira salvo que la persona prefiera menos movimiento: la
          regla global de `globals.css` lo neutraliza en ese caso y sigue
          leyéndose como indicador de carga gracias al borde y al texto. */}
      <span
        aria-hidden="true"
        className="h-8 w-8 animate-spin rounded-pill border-[3px] border-primario-suave border-t-primario"
      />
      <p className="text-sm text-gris">{resumen}</p>
    </div>
  );
}
