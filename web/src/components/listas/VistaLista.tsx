"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { nombreCadena } from "@/lib/cadenas";
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

type CosteCadena = {
  cadena: string;
  coste: string;
  porcentaje_a: number | null;
  productos_no_disponibles: string[];
};

type Resumen = {
  coste_total: string;
  por_cadena: CosteCadena[];
  porcentaje_c: number | null;
  avisos: string[];
};

type Props = {
  lista: { id: string; nombre: string; items: Item[] };
  resumen: Resumen | null;
};

type Candidato = {
  producto_id: string;
  nombre: string;
  cadena: string;
  cadena_id: string | null;
  precio_eur: string;
};

const PRECIO = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});

const PORCENTAJE = new Intl.NumberFormat("es-ES", {
  style: "percent",
  maximumFractionDigits: 1,
});

export function VistaLista({ lista, resumen }: Props) {
  const router = useRouter();
  const [items, setItems] = useState<Item[]>(lista.items);
  const [borrando, setBorrando] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const botonAbrir = useRef<HTMLButtonElement | null>(null);
  const dialogo = useRef<HTMLDivElement | null>(null);

  // El diálogo se cierra con Escape y devuelve el foco al botón que lo
  // abrió, para no perder el hilo con el teclado.
  useEffect(() => {
    if (!modal) {
      return;
    }
    function alPulsarTecla(evento: KeyboardEvent) {
      if (evento.key === "Escape") {
        setModal(false);
        botonAbrir.current?.focus();
      }
    }
    document.addEventListener("keydown", alPulsarTecla);
    dialogo.current?.focus();
    return () => document.removeEventListener("keydown", alPulsarTecla);
  }, [modal]);
  const [consulta, setConsulta] = useState("");
  const [candidatos, setCandidatos] = useState<Candidato[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  async function cambiarCantidad(item: Item, cantidad: number) {
    if (cantidad < 1 || cantidad === item.cantidad) {
      return;
    }
    const respuesta = await fetch(`/api/listas/${lista.id}/items/${item.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cantidad }),
    });
    if (!respuesta.ok) {
      setAviso(t("lista.error"));
      return;
    }
    setItems((actuales) =>
      actuales.map((otro) =>
        otro.id === item.id ? { ...otro, cantidad } : otro,
      ),
    );
    router.refresh();
  }

  async function eliminarItem(item: Item) {
    const respuesta = await fetch(`/api/listas/${lista.id}/items/${item.id}`, {
      method: "DELETE",
    });
    if (!respuesta.ok) {
      setAviso(t("lista.error"));
    }
    setBorrando(null);
    setItems((actuales) => actuales.filter((otro) => otro.id !== item.id));
    router.refresh();
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

  async function anadir(candidato: Candidato) {
    const respuesta = await fetch(`/api/listas/${lista.id}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        producto_id: candidato.producto_id,
        cantidad: 1,
        ...(candidato.cadena_id ? { cadena_compra_id: candidato.cadena_id } : {}),
      }),
    });
    if (!respuesta.ok) {
      setAviso(t("lista.error"));
      return;
    }
    setModal(false);
    setConsulta("");
    setCandidatos([]);
    router.refresh();
  }

  return (
    <section className="mx-auto max-w-contenido">
      <h1 className="text-2xl font-medium text-texto">{lista.nombre}</h1>

      {resumen ? (
        <div className="mt-4 flex flex-wrap items-baseline gap-6">
          <p className="text-3xl font-medium text-texto">
            {PRECIO.format(Number(resumen.coste_total))}
          </p>
          <p className="text-sm text-gris">
            {t("lista.coste_total")}{" "}
            {resumen.porcentaje_c !== null ? (
              <span title={t("lista.tooltip_porcentaje_c")}>
                {t("lista.porcentaje_c")}{" "}
                {PORCENTAJE.format(resumen.porcentaje_c)}
                <span aria-hidden="true"> ⓘ</span>
              </span>
            ) : (
              t("lista.sin_dato")
            )}
          </p>
        </div>
      ) : null}

      {resumen && resumen.por_cadena.length > 0 ? (
        <table className="mt-4 w-full text-sm">
          <caption className="sr-only">{t("lista.porcentaje_a_titulo")}</caption>
          <thead>
            <tr className="border-b border-borde text-left text-gris">
              <th scope="col" className="py-2 font-normal">
                {t("lista.cadena")}
              </th>
              <th scope="col" className="py-2 font-normal">
                {t("lista.coste")}
              </th>
              <th scope="col" className="py-2 font-normal">
                {t("lista.porcentaje_a")}
              </th>
            </tr>
          </thead>
          <tbody>
            {resumen.por_cadena.map((coste) => (
              <tr key={coste.cadena} className="border-b border-borde">
                <th scope="row" className="py-2 text-left font-normal">
                  {nombreCadena(coste.cadena)}
                </th>
                <td className="py-2">{PRECIO.format(Number(coste.coste))}</td>
                <td className="py-2">
                  {coste.porcentaje_a !== null
                    ? PORCENTAJE.format(coste.porcentaje_a)
                    : t("lista.sin_dato")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}

      {resumen && resumen.avisos.length > 0 ? (
        <ul className="mt-4 space-y-1">
          {resumen.avisos.map((texto) => (
            <li key={texto} className="text-sm text-gris">
              {texto}
            </li>
          ))}
        </ul>
      ) : null}

      {aviso ? (
        <p role="alert" className="mt-3 text-sm text-error">
          {aviso}
        </p>
      ) : null}

      <ul className="mt-6 space-y-3">
        {items.map((item) => (
          <li
            key={item.id}
            className="flex flex-wrap items-center gap-3 rounded-tarjeta border border-borde p-4"
          >
            <Image
              src={`/logos/${item.cadena_compra ?? "dia"}.svg`}
              alt={item.cadena_compra ?? t("lista.sin_cadena")}
              width={32}
              height={32}
              className="h-8 w-8 shrink-0 rounded-pill"
            />
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-texto">
                {item.producto_nombre ?? item.producto_id}
              </p>
              <p className="truncate text-sm text-gris">
                {[item.producto_marca, item.cadena_compra]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>

            <label className="flex items-center gap-1 text-sm text-gris">
              {t("lista.cantidad")}
              <input
                type="number"
                min="1"
                max="999"
                defaultValue={item.cantidad}
                aria-label={`${t("lista.cantidad")} ${item.producto_nombre ?? ""}`}
                onBlur={(evento) =>
                  void cambiarCantidad(item, Number(evento.target.value))
                }
                className="w-16 rounded-lg border border-borde-fuerte px-2 py-1 text-sm text-texto focus:border-primario"
              />
            </label>

            <span className="w-24 text-right text-sm text-texto">
              {item.precio_snapshot
                ? PRECIO.format(Number(item.precio_snapshot))
                : t("lista.sin_precio")}
            </span>

            {borrando === item.id ? (
              <span className="flex items-center gap-2 text-sm">
                <button
                  type="button"
                  onClick={() => void eliminarItem(item)}
                  className="rounded-lg bg-error px-3 py-1 text-white"
                >
                  {t("lista.confirmar")}
                </button>
                <button
                  type="button"
                  onClick={() => setBorrando(null)}
                  className="rounded-lg border border-borde px-3 py-1 text-texto"
                >
                  {t("lista.cancelar")}
                </button>
              </span>
            ) : (
              <button
                type="button"
                onClick={() => setBorrando(item.id)}
                className="rounded-lg border border-borde px-3 py-1 text-sm text-texto transition-colors duration-150 hover:bg-superficie"
              >
                {t("lista.eliminar")}
              </button>
            )}
          </li>
        ))}
      </ul>

      <div className="mt-6">
        <button
          type="button"
          ref={botonAbrir}
          onClick={() => setModal(true)}
          className="rounded-lg bg-primario px-5 py-2.5 text-sm font-medium text-white transition-colors duration-150 hover:bg-primario-oscuro"
        >
          {t("lista.anadir_producto")}
        </button>
      </div>

      {modal ? (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-label={t("lista.anadir_producto")}
          onClick={(evento) => {
            // Clic en el fondo cierra el diálogo; clic dentro no.
            if (evento.target === evento.currentTarget) {
              setModal(false);
              botonAbrir.current?.focus();
            }
          }}
        >
          <div
            ref={dialogo}
            tabIndex={-1}
            className="w-full max-w-lg rounded-tarjeta bg-white p-5"
          >
            <h2 className="text-lg font-medium text-texto">
              {t("lista.anadir_producto")}
            </h2>
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
                className="min-w-0 flex-1 rounded-lg border border-borde-fuerte px-4 py-2 text-sm text-texto focus:border-primario"
              />
              <button
                type="submit"
                className="rounded-lg bg-primario px-4 py-2 text-sm text-white"
              >
                {t("buscar.boton")}
              </button>
            </form>

            <ul className="mt-4 max-h-72 space-y-2 overflow-y-auto">
              {candidatos.map((candidato) => (
                <li key={`${candidato.producto_id}-${candidato.cadena}`}>
                  <button
                    type="button"
                    onClick={() => void anadir(candidato)}
                    className="flex w-full items-center gap-3 rounded-lg border border-borde px-3 py-2 text-left text-sm transition-colors duration-150 hover:bg-superficie"
                  >
                    <span className="min-w-0 flex-1 truncate text-texto">
                      {candidato.nombre}
                    </span>
                    <span className="text-gris">{candidato.cadena}</span>
                    <span className="text-texto">
                      {PRECIO.format(Number(candidato.precio_eur))}
                    </span>
                  </button>
                </li>
              ))}
            </ul>

            {buscando ? (
              <p className="mt-3 text-sm text-gris">{t("lista.buscando")}</p>
            ) : null}

            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={() => {
                  setModal(false);
                  botonAbrir.current?.focus();
                }}
                className="rounded-lg border border-borde px-4 py-2 text-sm text-texto transition-colors duration-150 hover:bg-superficie"
              >
                {t("lista.cerrar")}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
