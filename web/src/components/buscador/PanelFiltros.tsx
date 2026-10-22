"use client";

import { Icono } from "@/components/ui/Icono";
import { t } from "@/lib/i18n";
import type { Filtros, Orden } from "@/lib/filtros";

type Props = {
  filtros: Filtros;
  marcas: string[];
  categorias: string[];
  onChange: (filtros: Filtros) => void;
  onLimpiar: () => void;
};

const CLASE_CAMPO =
  "mt-1.5 w-full rounded-lg border border-borde bg-white px-3 py-2 text-sm text-texto transition-colors duration-150 hover:border-borde-fuerte focus:border-primario";

/** Etiqueta de un control del panel. */
function Etiqueta({ htmlFor, children }: { htmlFor: string; children: string }) {
  return (
    <label className="block text-xs text-gris" htmlFor={htmlFor}>
      {children}
    </label>
  );
}

/**
 * Panel de orden y filtros; se aplican en el cliente sobre lo ya cargado.
 *
 * Los controles viven en una card con rejilla responsive: cuatro columnas
 * en pantallas anchas, dos en medianas y una en móvil. La sombra es mínima
 * (`shadow-sm`), solo para separar la card del fondo.
 */
export function PanelFiltros({
  filtros,
  marcas,
  categorias,
  onChange,
  onLimpiar,
}: Props) {
  return (
    <section className="mt-6 rounded-tarjeta border border-borde bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-center gap-2">
        <Icono nombre="filtros" className="h-4 w-4 text-gris" />
        <h2 className="text-sm font-medium text-texto">{t("filtros.titulo")}</h2>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div>
          <Etiqueta htmlFor="orden">{t("filtros.orden")}</Etiqueta>
          <select
            id="orden"
            className={CLASE_CAMPO}
            value={filtros.orden}
            onChange={(evento) =>
              onChange({ ...filtros, orden: evento.target.value as Orden })
            }
          >
            <option value="precio_unitario">
              {t("filtros.orden_precio_unitario")}
            </option>
            <option value="precio_kg_l">{t("filtros.orden_precio_kg_l")}</option>
            <option value="relevancia">{t("filtros.orden_relevancia")}</option>
          </select>
        </div>

        <div>
          <Etiqueta htmlFor="precio_min">{t("filtros.precio_min")}</Etiqueta>
          <input
            id="precio_min"
            type="number"
            inputMode="decimal"
            min="0"
            step="0.01"
            className={CLASE_CAMPO}
            value={filtros.precioMin ?? ""}
            onChange={(evento) =>
              onChange({
                ...filtros,
                precioMin: evento.target.value === "" ? null : Number(evento.target.value),
              })
            }
          />
        </div>

        <div>
          <Etiqueta htmlFor="precio_max">{t("filtros.precio_max")}</Etiqueta>
          <input
            id="precio_max"
            type="number"
            inputMode="decimal"
            min="0"
            step="0.01"
            className={CLASE_CAMPO}
            value={filtros.precioMax ?? ""}
            onChange={(evento) =>
              onChange({
                ...filtros,
                precioMax: evento.target.value === "" ? null : Number(evento.target.value),
              })
            }
          />
        </div>

        <div>
          <Etiqueta htmlFor="marca">{t("filtros.marca")}</Etiqueta>
          <select
            id="marca"
            className={CLASE_CAMPO}
            value={filtros.marca}
            onChange={(evento) => onChange({ ...filtros, marca: evento.target.value })}
          >
            <option value="">{t("filtros.todas")}</option>
            {marcas.map((marca) => (
              <option key={marca} value={marca}>
                {marca}
              </option>
            ))}
          </select>
        </div>

        <div>
          <Etiqueta htmlFor="categoria">{t("filtros.categoria")}</Etiqueta>
          <select
            id="categoria"
            className={CLASE_CAMPO}
            value={filtros.categoria}
            onChange={(evento) =>
              onChange({ ...filtros, categoria: evento.target.value })
            }
          >
            <option value="">{t("filtros.todas")}</option>
            {categorias.map((categoria) => (
              <option key={categoria} value={categoria}>
                {categoria}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-borde pt-4">
        <label className="flex items-center gap-2 text-sm text-texto">
          <input
            type="checkbox"
            className="h-4 w-4 accent-primario"
            checked={filtros.soloConStock}
            onChange={(evento) =>
              onChange({ ...filtros, soloConStock: evento.target.checked })
            }
          />
          {t("filtros.solo_con_stock")}
        </label>

        <button
          type="button"
          onClick={onLimpiar}
          className="rounded-lg border border-borde px-3 py-1.5 text-sm text-gris transition-colors duration-150 hover:border-borde-fuerte hover:bg-superficie hover:text-texto"
        >
          {t("filtros.limpiar")}
        </button>
      </div>
    </section>
  );
}
