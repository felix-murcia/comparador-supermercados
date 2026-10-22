"use client";

import { nombreCadena } from "@/lib/cadenas";
import { t } from "@/lib/i18n";
import type { CosteCadena } from "@/components/listas/tipos";

const PRECIO = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});

type Props = {
  por_cadena: CosteCadena[];
};

/**
 * Comparativa entre cadenas, ordenada de más barata a más cara.
 *
 * Una tabla obligaba a comparar números de memoria; con la barra, la
 * diferencia se ve. La barra es proporcional al coste, así que lo que más
 * cara sale se ve a simple vista.
 */
export function ComparativaCadenas({ por_cadena }: Props) {
  if (por_cadena.length === 0) {
    return null;
  }

  const ordenadas = [...por_cadena].sort(
    (a, b) => Number(a.coste) - Number(b.coste) || a.cadena.localeCompare(b.cadena),
  );
  const maximo = Math.max(...ordenadas.map((coste) => Number(coste.coste)), 0);

  return (
    <section aria-labelledby="titulo-comparativa">
      <h2
        id="titulo-comparativa"
        className="text-sm font-medium text-texto"
      >
        {t("lista.comparativa")}
      </h2>

      <ul className="mt-3 space-y-2">
        {ordenadas.map((coste, indice) => {
          const importe = Number(coste.coste);
          const porcentaje = maximo > 0 ? (importe / maximo) * 100 : 0;
          const mejor = indice === 0 && importe > 0;
          return (
            <li key={coste.cadena} className="flex items-center gap-3">
              <span
                aria-hidden="true"
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs font-medium ${
                  mejor
                    ? "bg-primario-suave text-primario-oscuro"
                    : "bg-superficie-activa text-gris"
                }`}
              >
                {indice + 1}
              </span>
              <span
                className={`w-24 shrink-0 truncate text-sm ${
                  mejor ? "font-medium text-texto" : "text-gris"
                }`}
              >
                {nombreCadena(coste.cadena)}
              </span>
              <span className="h-2 min-w-0 flex-1 overflow-hidden rounded-pill bg-superficie-activa">
                <span
                  className={`block h-full rounded-pill ${
                    mejor ? "bg-primario" : "bg-barra"
                  }`}
                  style={{ width: `${porcentaje}%` }}
                />
              </span>
              <span
                className={`w-20 shrink-0 text-right text-sm tabular-nums ${
                  mejor ? "font-medium text-texto" : "text-gris"
                }`}
              >
                {PRECIO.format(importe)}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
