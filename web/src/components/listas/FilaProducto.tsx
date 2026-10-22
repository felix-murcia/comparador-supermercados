"use client";

import Image from "next/image";
import { useState } from "react";

import { nombreCadena } from "@/lib/cadenas";
import { t } from "@/lib/i18n";
import type { Item, ProductoResumen } from "@/components/listas/tipos";

const PRECIO = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});

type Props = {
  item: Item;
  producto: ProductoResumen | undefined;
  onCantidad: (item: Item, cantidad: number) => void;
  onEliminar: (item: Item) => void;
  borrando: boolean;
  onConfirmarBorrado: (item: Item) => void;
  onCancelarBorrado: () => void;
};

/**
 * Fila de un producto de la lista.
 *
 * Compacta por defecto: nombre, cadena y precio, que es lo que se mira de
 * un vistazo. El desglose de precios por cadena está a un clic, para quien
 * quiera ver dónde sale más barato cada cosa.
 */
export function FilaProducto({
  item,
  producto,
  onCantidad,
  onEliminar,
  borrando,
  onConfirmarBorrado,
  onCancelarBorrado,
}: Props) {
  const [desplegado, setDesplegado] = useState(false);
  const precioBruto =
    item.precio_snapshot ?? producto?.precios[item.cadena_compra ?? ""];
  const precio = precioBruto === undefined ? undefined : Number(precioBruto);
  const conVariosPrecios =
    producto !== undefined && Object.keys(producto.precios).length > 1;

  return (
    <li className="rounded-tarjeta border border-borde bg-white px-4 py-3">
      <div className="flex items-center gap-3">
        <Image
          src={`/logos/${item.cadena_compra ?? "dia"}.svg`}
          alt={item.cadena_compra ?? t("lista.sin_cadena")}
          width={28}
          height={28}
          className="h-7 w-7 shrink-0 rounded-pill"
        />

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-texto">
            {item.producto_nombre ?? item.producto_id}
          </p>
          <p className="truncate text-xs text-gris">
            {[item.producto_marca, item.cadena_compra].filter(Boolean).join(" · ")}
          </p>
        </div>

        {/* En móvil el precio baja a la línea siguiente: si no, el nombre
            del producto queda cortado. */}
        <span className="shrink-0 text-sm font-medium tabular-nums text-texto sm:hidden">
          {precio === undefined ? t("lista.sin_precio") : PRECIO.format(precio)}
        </span>
      </div>

      {/* `sm:contents` deja que los controles formen parte de la fila
          superior en pantallas anchas. */}
      <div className="mt-2 flex items-center justify-end gap-3 sm:mt-0 sm:contents">
        <span className="hidden shrink-0 text-sm font-medium tabular-nums text-texto sm:inline">
          {precio === undefined ? t("lista.sin_precio") : PRECIO.format(precio)}
        </span>

        <label className="flex shrink-0 items-center gap-1 text-xs text-gris">
          <span className="sr-only">{t("lista.cantidad")}</span>
          <input
            type="number"
            min="1"
            max="999"
            defaultValue={item.cantidad}
            aria-label={`${t("lista.cantidad")} ${item.producto_nombre ?? ""}`}
            onBlur={(evento) =>
              onCantidad(item, Number(evento.target.value))
            }
            className="w-14 rounded-lg border border-borde px-2 py-1 text-sm text-texto focus:border-primario"
          />
        </label>

        {borrando ? (
          <span className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => onConfirmarBorrado(item)}
              className="rounded-lg bg-error px-3 py-1 text-xs text-white transition-colors duration-150 hover:opacity-90"
            >
              {t("lista.confirmar")}
            </button>
            <button
              type="button"
              onClick={onCancelarBorrado}
              className="rounded-lg border border-borde px-3 py-1 text-xs text-texto transition-colors duration-150 hover:bg-superficie"
            >
              {t("lista.cancelar")}
            </button>
          </span>
        ) : (
          <button
            type="button"
            onClick={() => onEliminar(item)}
            className="shrink-0 rounded-lg px-2 py-1 text-xs text-gris transition-colors duration-150 hover:bg-superficie hover:text-error"
          >
            {t("lista.eliminar")}
          </button>
        )}
      </div>

      {conVariosPrecios && producto ? (
        <>
          <button
            type="button"
            onClick={() => setDesplegado((valor) => !valor)}
            aria-expanded={desplegado}
            className="mt-2 inline-flex items-center gap-1 text-xs text-gris transition-colors duration-150 hover:text-texto"
          >
            <span
              aria-hidden="true"
              className={`transition-transform duration-150 ${desplegado ? "rotate-90" : ""}`}
            >
              ▸
            </span>
            {desplegado ? t("lista.ocultar_precios") : t("lista.ver_precios")}
          </button>

          {desplegado ? (
            <ul className="mt-2 space-y-1 border-t border-borde pt-2">
              {Object.entries(producto.precios)
                .sort(([, a], [, b]) => Number(a) - Number(b))
                .map(([cadena, importe]) => {
                  const equivalente = producto.equivalentes[cadena];
                  return (
                    <li
                      key={cadena}
                      className="flex items-baseline gap-2 text-xs"
                    >
                      <span className="w-24 shrink-0 text-gris">
                        {nombreCadena(cadena)}
                      </span>
                      <span className="font-medium tabular-nums text-texto">
                        {PRECIO.format(Number(importe))}
                      </span>
                      {equivalente ? (
                        <span className="min-w-0 truncate text-gris">
                          {t("lista.es_equivalente_de", {
                            nombre: equivalente.nombre,
                          })}
                        </span>
                      ) : null}
                    </li>
                  );
                })}
              {producto.ahorro && Number(producto.ahorro) > 0 ? (
                <li className="mt-1 text-xs text-gris">
                  {t("lista.ahorro_producto", {
                    importe: PRECIO.format(Number(producto.ahorro)),
                    cadena: producto.mejor_cadena
                      ? nombreCadena(producto.mejor_cadena)
                      : "",
                  })}
                </li>
              ) : null}
            </ul>
          ) : null}
        </>
      ) : null}
    </li>
  );
}
