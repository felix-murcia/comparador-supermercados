"use client";

import type { InputHTMLAttributes } from "react";

import { Icono } from "@/components/ui/Icono";
import { t } from "@/lib/i18n";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "className"> & {
  /** Clases del contenedor; permite ajustar el ancho desde quien lo usa. */
  className?: string;
};

/**
 * Campo de búsqueda con icono de lupa.
 *
 * El icono va dentro del campo, no como elemento aparte, para que el
 * conjunto se lea como un solo control. El fondo es neutro (`superficie`)
 * en vez de un borde fuerte: menos ruido visual en la página.
 */
export function CampoBusqueda({ className, id = "q", ...props }: Props) {
  return (
    <div className={`relative ${className ?? ""}`}>
      <label className="sr-only" htmlFor={id}>
        {t("buscar.campo")}
      </label>
      <Icono
        nombre="buscar"
        className="pointer-events-none absolute left-3.5 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-gris"
      />
      <input
        {...props}
        id={id}
        type="search"
        autoComplete="off"
        className="w-full rounded-xl border border-borde bg-superficie py-2.5 pl-11 pr-4 text-sm text-texto transition-colors duration-150 placeholder:text-gris hover:border-borde-fuerte focus:border-primario focus:bg-white focus:outline-none"
      />
    </div>
  );
}
