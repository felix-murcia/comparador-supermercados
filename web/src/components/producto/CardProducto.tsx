"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { t } from "@/lib/i18n";

type Item = {
  id: string;
  producto_id: string;
  cantidad: number;
  precio_snapshot: string | null;
  producto_nombre: string | null;
  producto_marca: string | null;
  cadena_compra: string | null;
};

type Props = {
  posicion: number;
  nombre: string;
  marca: string | null;
  formato: string | null;
  cadena: string;
  cadena_id: string | null;
  producto_id: string;
  precio_eur: string;
  precio_por_litro_kg: string | null;
  url_producto: string | null;
};

type Lista = {
  id: string;
  nombre: string;
};

const PRECIO = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});

const UNIDAD = new Intl.NumberFormat("es-ES", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Card de producto: logo de la cadena, ranking, precio y alta en una lista. */
export function CardProducto({
  posicion,
  nombre,
  marca,
  formato,
  cadena,
  cadena_id,
  producto_id,
  precio_eur,
  precio_por_litro_kg,
  url_producto,
}: Props) {
  const [modal, setModal] = useState(false);
  const [listas, setListas] = useState<Lista[]>([]);
  const [estado, setEstado] = useState<"inactivo" | "cargando" | "anadido" | "error">(
    "inactivo",
  );
  const botonAbrir = useRef<HTMLButtonElement | null>(null);
  const dialogo = useRef<HTMLDivElement | null>(null);

  // El modal se cierra con Escape y devuelve el foco al botón que lo abrió
  // (si no, el foco se pierde en el fondo y la navegación con teclado se
  // corta).
  useEffect(() => {
    if (!modal) {
      return;
    }
    function alPulsarTecla(evento: KeyboardEvent) {
      if (evento.key === "Escape") {
        setModal(false);
      }
    }
    document.addEventListener("keydown", alPulsarTecla);
    dialogo.current?.focus();
    return () => document.removeEventListener("keydown", alPulsarTecla);
  }, [modal]);

  function cerrarModal() {
    setModal(false);
    botonAbrir.current?.focus();
  }

  async function abrirModal() {
    setModal(true);
    setEstado("cargando");
    try {
      const respuesta = await fetch("/api/listas");
      const datos = await respuesta.json().catch(() => []);
      setListas(Array.isArray(datos) ? datos : []);
      setEstado("inactivo");
    } catch {
      setEstado("error");
    }
  }

  async function anadir(lista: Lista) {
    setEstado("cargando");
    try {
      const respuesta = await fetch(`/api/listas/${lista.id}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          producto_id,
          cantidad: 1,
          ...(cadena_id ? { cadena_compra_id: cadena_id } : {}),
        }),
      });
      if (!respuesta.ok) {
        setEstado("error");
        return;
      }
      setEstado("anadido");
      setModal(false);
      botonAbrir.current?.focus();
    } catch {
      setEstado("error");
    }
  }

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
            className="shrink-0 rounded-pill transition-colors duration-200 hover:opacity-80"
          >
            {logo}
          </a>
        ) : (
          logo
        )}

        <div className="min-w-0 flex-1">
          <h3 className="truncate font-medium text-texto">{nombre}</h3>
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
        {estado === "anadido" ? (
          <p role="status" className="text-xs text-gris">
            {t("lista.anadida")}
          </p>
        ) : null}
        {estado === "error" ? (
          <p role="alert" className="text-xs text-error">
            {t("lista.error")}
          </p>
        ) : null}
        <button
          type="button"
          ref={botonAbrir}
          onClick={() => void abrirModal()}
          className="rounded-pill border border-borde px-4 py-1.5 text-sm text-texto transition-colors duration-200 hover:bg-primario-suave"
        >
          {t("lista.anadir")}
        </button>
      </div>

      {modal ? (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-label={t("lista.elegir")}
          onClick={(evento) => {
            // Clic en el fondo cierra el modal; clic dentro no.
            if (evento.target === evento.currentTarget) {
              cerrarModal();
            }
          }}
        >
          <div ref={dialogo} tabIndex={-1} className="w-full max-w-md rounded-tarjeta bg-white p-5">
            <h2 className="text-lg font-medium text-texto">{t("lista.elegir")}</h2>

            {listas.length === 0 ? (
              <p className="mt-3 text-sm text-gris">{t("listas.vacias")}</p>
            ) : (
              <ul className="mt-3 space-y-2">
                {listas.map((lista) => (
                  <li key={lista.id}>
                    <button
                      type="button"
                      onClick={() => void anadir(lista)}
                      className="w-full rounded-pill border border-borde px-4 py-2 text-left text-sm text-texto transition-colors duration-200 hover:bg-primario-suave"
                    >
                      {lista.nombre}
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={cerrarModal}
                className="rounded-pill border border-borde px-4 py-2 text-sm text-texto transition-colors duration-200 hover:bg-primario-suave"
              >
                {t("lista.cerrar")}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </article>
  );
}
