"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { t } from "@/lib/i18n";
import { aSlug } from "@/lib/slug";

type Props = {
  posicion: number;
  nombre: string;
  marca: string | null;
  formato: string | null;
  cadena: string;
  precio_eur: string;
  precio_por_litro_kg: string | null;
  url_producto: string | null;
};

const PRECIO = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});

const UNIDAD = new Intl.NumberFormat("es-ES", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Card de producto: logo de la cadena, ranking, precio y enlace a la ficha. */
export function CardProducto({
  posicion,
  nombre,
  marca,
  formato,
  cadena,
  precio_eur,
  precio_por_litro_kg,
  url_producto,
}: Props) {
  const [aviso, setAviso] = useState(false);
  const descripcion = [marca, formato].filter(Boolean).join(" · ");
  const logo = (
    <Image
      src={`/logos/${cadena}.svg`}
      alt={`${nombre} en ${cadena}`}
      width={40}
      height={40}
      className="h-10 w-10 shrink-0 rounded-pill"
    />
  );

  return (
    <article className="rounded-tarjeta border border-borde p-4">
      <div className="flex items-start gap-3">
        <span className="w-6 shrink-0 text-sm text-gris">#{posicion}</span>

        {url_producto ? (
          <a
            href={url_producto}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded-pill hover:opacity-80"
          >
            {logo}
          </a>
        ) : (
          logo
        )}

        <div className="min-w-0 flex-1">
          <h3 className="truncate font-medium text-texto">
            <Link
              href={`/producto/${aSlug(nombre)}`}
              className="hover:underline"
            >
              {nombre}
            </Link>
          </h3>
          <p className="truncate text-sm text-gris">
            {[descripcion, cadena].filter(Boolean).join(" · ")}
          </p>
        </div>

        <div className="shrink-0 text-right">
          <p className="font-medium text-texto">
            {PRECIO.format(Number(precio_eur))}
          </p>
          {precio_por_litro_kg ? (
            <p className="text-sm text-gris">
              {UNIDAD.format(Number(precio_por_litro_kg))} €/kg-L
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-end gap-3">
        {aviso ? (
          <p role="status" className="text-xs text-gris">
            {t("lista.proximamente")}
          </p>
        ) : null}
        <button
          type="button"
          onClick={() => setAviso(true)}
          className="rounded-pill border border-borde px-4 py-1.5 text-sm text-texto hover:bg-primario-suave"
        >
          {t("lista.anadir")}
        </button>
      </div>
    </article>
  );
}
