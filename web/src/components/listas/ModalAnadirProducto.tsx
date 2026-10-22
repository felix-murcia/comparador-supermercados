"use client";

import { useEffect, useRef, useState } from "react";

import { Icono } from "@/components/ui/Icono";
import { t } from "@/lib/i18n";

const PRECIO = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});

export type Candidato = {
  producto_id: string;
  nombre: string;
  cadena: string;
  cadena_id: string | null;
  precio_eur: string;
};

type Props = {
  abierto: boolean;
  onCerrar: () => void;
  onAnadir: (candidato: Candidato) => void;
};

/**
 * Diálogo para buscar un producto y añadirlo a la lista.
 *
 * Busca contra la API de comparación, que devuelve el precio de cada
 * cadena, así que la persona ve lo que va a pagar antes de añadirlo.
 */
export function ModalAnadirProducto({ abierto, onCerrar, onAnadir }: Props) {
  const [consulta, setConsulta] = useState("");
  const [candidatos, setCandidatos] = useState<Candidato[]>([]);
  const [buscando, setBuscando] = useState(false);
  const botonCerrar = useRef<HTMLButtonElement | null>(null);
  const dialogo = useRef<HTMLDivElement | null>(null);

  // El diálogo se cierra con Escape y devuelve el foco al botón que lo
  // abrió, para no perder el hilo con el teclado.
  useEffect(() => {
    if (!abierto) {
      return;
    }
    function alPulsarTecla(evento: KeyboardEvent) {
      if (evento.key === "Escape") {
        onCerrar();
      }
    }
    document.addEventListener("keydown", alPulsarTecla);
    dialogo.current?.focus();
    return () => document.removeEventListener("keydown", alPulsarTecla);
  }, [abierto, onCerrar]);

  if (!abierto) {
    return null;
  }

  async function buscar() {
    if (consulta.trim().length === 0) {
      return;
    }
    setBuscando(true);
    const parametros = new URLSearchParams({ q: consulta.trim() });
    const respuesta = await fetch(`/api/comparar?${parametros.toString()}`);
    const datos = await respuesta.json().catch(() => ({}));
    setCandidatos(Array.isArray(datos.resultados) ? datos.resultados : []);
    setBuscando(false);
  }

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={t("lista.anadir_producto")}
      onClick={(evento) => {
        // Clic en el fondo cierra el diálogo; clic dentro no.
        if (evento.target === evento.currentTarget) {
          onCerrar();
        }
      }}
    >
      <div
        ref={dialogo}
        tabIndex={-1}
        className="w-full max-w-lg rounded-tarjeta bg-white p-5"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium text-texto">
            {t("lista.anadir_producto")}
          </h2>
          <button
            type="button"
            ref={botonCerrar}
            onClick={onCerrar}
            aria-label={t("lista.cerrar")}
            className="rounded-lg p-1.5 text-gris transition-colors duration-150 hover:bg-superficie hover:text-texto"
          >
            <Icono nombre="cerrar" className="h-4 w-4" />
          </button>
        </div>

        <form
          className="mt-3 flex gap-2"
          onSubmit={(evento) => {
            evento.preventDefault();
            void buscar();
          }}
        >
          <label className="sr-only" htmlFor="q-lista">
            {t("buscar.campo")}
          </label>
          <input
            id="q-lista"
            type="search"
            value={consulta}
            onChange={(evento) => setConsulta(evento.target.value)}
            placeholder={t("buscar.placeholder")}
            className="min-w-0 flex-1 rounded-lg border border-borde-fuerte px-3 py-2 text-sm text-texto focus:border-primario"
          />
          <button
            type="submit"
            className="rounded-lg bg-primario px-4 py-2 text-sm text-white transition-colors duration-150 hover:bg-primario-oscuro"
          >
            {t("buscar.boton")}
          </button>
        </form>

        {buscando ? (
          <p className="mt-3 text-sm text-gris">{t("lista.buscando")}</p>
        ) : null}

        {candidatos.length > 0 ? (
          <ul className="mt-4 max-h-72 space-y-1 overflow-y-auto">
            {candidatos.map((candidato) => (
              <li key={`${candidato.producto_id}-${candidato.cadena}`}>
                <button
                  type="button"
                  onClick={() => onAnadir(candidato)}
                  className="flex w-full items-center gap-3 rounded-lg border border-borde px-3 py-2 text-left text-sm transition-colors duration-150 hover:bg-superficie"
                >
                  <span className="min-w-0 flex-1 truncate text-texto">
                    {candidato.nombre}
                  </span>
                  <span className="shrink-0 text-gris">{candidato.cadena}</span>
                  <span className="shrink-0 text-texto">
                    {PRECIO.format(Number(candidato.precio_eur))}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}
