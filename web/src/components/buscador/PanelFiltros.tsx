"use client";

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
  "mt-1 rounded-pill border border-borde-fuerte px-3 py-1.5 text-sm text-texto focus:border-primario";

/** Panel de orden y filtros; se aplican en el cliente sobre lo ya cargado. */
export function PanelFiltros({
  filtros,
  marcas,
  categorias,
  onChange,
  onLimpiar,
}: Props) {
  return (
    <section className="mt-6 rounded-tarjeta border border-borde p-4">
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs text-gris" htmlFor="orden">
            {t("filtros.orden")}
          </label>
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
          <label className="block text-xs text-gris" htmlFor="precio_min">
            {t("filtros.precio_min")}
          </label>
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
          <label className="block text-xs text-gris" htmlFor="precio_max">
            {t("filtros.precio_max")}
          </label>
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
          <label className="block text-xs text-gris" htmlFor="marca">
            {t("filtros.marca")}
          </label>
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
          <label className="block text-xs text-gris" htmlFor="categoria">
            {t("filtros.categoria")}
          </label>
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

        <label className="flex items-center gap-2 pb-2 text-sm text-texto">
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
          className="mb-1 rounded-pill border border-borde px-4 py-1.5 text-sm text-texto transition-colors duration-200 hover:bg-primario-suave"
        >
          {t("filtros.limpiar")}
        </button>
      </div>
    </section>
  );
}
