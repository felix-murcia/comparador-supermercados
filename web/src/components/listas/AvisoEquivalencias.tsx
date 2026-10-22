"use client";

import { Icono } from "@/components/ui/Icono";
import { nombreCadena } from "@/lib/cadenas";
import { t } from "@/lib/i18n";
import type { ProductoResumen } from "@/components/listas/tipos";

type Props = {
  productos: ProductoResumen[];
};

/**
 * Aviso de las equivalencias usadas en la comparación.
 *
 * Va plegado: es un matiz importante (no se compara el mismo artículo en
 * todas las cadenas), pero no es lo primero que la persona quiere leer.
 */
export function AvisoEquivalencias({ productos }: Props) {
  const conEquivalentes = productos.filter(
    (producto) => Object.keys(producto.equivalentes).length > 0,
  );

  if (conEquivalentes.length === 0) {
    return null;
  }

  return (
    <details className="group rounded-tarjeta border border-borde bg-white">
      <summary className="flex cursor-pointer items-center gap-2 px-4 py-3 text-sm text-gris transition-colors duration-150 hover:text-texto">
        <Icono nombre="info" className="h-4 w-4 shrink-0" />
        <span className="min-w-0 flex-1">
          {conEquivalentes.length === 1
            ? t("lista.equivalencias_titulo_1")
            : t("lista.equivalencias_titulo_n", {
                numero: conEquivalentes.length,
              })}
        </span>
        <span
          aria-hidden="true"
          className="shrink-0 text-xs transition-transform duration-150 group-open:rotate-180"
        >
          ▾
        </span>
      </summary>

      <div className="border-t border-borde px-4 py-3">
        <p className="text-sm text-gris">{t("lista.equivalencias_explica")}</p>
        <ul className="mt-2 space-y-2">
          {conEquivalentes.map((producto) => (
            <li key={producto.producto_id}>
              <p className="truncate text-sm text-texto">{producto.nombre}</p>
              <ul className="mt-0.5 space-y-0.5">
                {Object.entries(producto.equivalentes).map(([cadena, equivalente]) => (
                  <li key={cadena} className="text-sm text-gris">
                    <span className="text-texto">{nombreCadena(cadena)}</span>
                    {" → "}
                    {equivalente.nombre}
                    {equivalente.marca ? ` (${equivalente.marca})` : ""}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}
