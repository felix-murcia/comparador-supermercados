"use client";

import { Icono } from "@/components/ui/Icono";
import { nombreCadena } from "@/lib/cadenas";
import { t } from "@/lib/i18n";
import type { Resumen } from "@/components/listas/tipos";

const PRECIO = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});

type Props = {
  nombre: string;
  resumen: Resumen | null;
  /** Nombre de la lista editable en el sitio. */
  editando: boolean;
  onEmpezarEdicion: () => void;
  onGuardarNombre: (nombre: string) => void;
  onAnadir: () => void;
};

/**
 * Cabecera de la lista: lo primero que se ve es la respuesta a la pregunta
 * que trae a la persona hasta aquí, "¿dónde me sale más barata la compra?",
 * y la acción principal, añadir un producto, siempre a mano.
 */
export function CabeceraLista({
  nombre,
  resumen,
  editando,
  onEmpezarEdicion,
  onGuardarNombre,
  onAnadir,
}: Props) {
  const costeMejor = resumen?.por_cadena.find(
    (coste) => coste.cadena === resumen.mejor_cadena,
  )?.coste;
  const masCara = resumen
    ? [...resumen.por_cadena].sort((a, b) => Number(b.coste) - Number(a.coste))[0]
    : undefined;
  const ahorro = resumen?.ahorro_maximo ? Number(resumen.ahorro_maximo) : 0;

  return (
    <section className="rounded-tarjeta border border-borde bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        {editando ? (
          <form
            className="flex min-w-0 flex-1 items-center gap-2"
            onSubmit={(evento) => {
              evento.preventDefault();
              const valor = new FormData(evento.currentTarget).get("nombre");
              if (typeof valor === "string" && valor.trim().length > 0) {
                onGuardarNombre(valor.trim());
              }
            }}
          >
            <input
              name="nombre"
              defaultValue={nombre}
              autoFocus
              maxLength={120}
              aria-label={t("lista.nombre")}
              className="min-w-0 flex-1 rounded-lg border border-borde-fuerte px-3 py-1.5 text-lg text-texto focus:border-primario"
            />
            <button
              type="submit"
              className="rounded-lg bg-primario px-3 py-1.5 text-sm font-medium text-white transition-colors duration-150 hover:bg-primario-oscuro"
            >
              {t("lista.guardar")}
            </button>
          </form>
        ) : (
          <h1 className="flex min-w-0 items-center gap-2 text-xl font-medium text-texto">
            <span className="truncate">{nombre}</span>
            <button
              type="button"
              onClick={onEmpezarEdicion}
              aria-label={t("lista.renombrar")}
              className="shrink-0 rounded-lg p-1.5 text-gris transition-colors duration-150 hover:bg-superficie hover:text-texto"
            >
              <Icono nombre="editar" className="h-4 w-4" />
            </button>
          </h1>
        )}

        <button
          type="button"
          onClick={onAnadir}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-primario px-4 py-2 text-sm font-medium text-white transition-colors duration-150 hover:bg-primario-oscuro"
        >
          <Icono nombre="mas" className="h-4 w-4" />
          {t("lista.anadir_producto")}
        </button>
      </div>

      {resumen?.mejor_cadena && costeMejor ? (
        <div className="mt-5">
          <p className="text-xs font-medium uppercase tracking-wide text-gris">
            {t("lista.mejor_opcion")}
          </p>
          <p className="mt-1.5 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-2xl font-medium text-texto">
              {nombreCadena(resumen.mejor_cadena)}
            </span>
            <span className="text-2xl font-semibold tabular-nums text-texto">
              {PRECIO.format(Number(costeMejor))}
            </span>
          </p>
          {ahorro > 0 && masCara ? (
            <p className="mt-1 text-sm text-gris">
              {t("lista.ahorro_frente_a", {
                importe: PRECIO.format(ahorro),
                cadena: nombreCadena(masCara.cadena),
              })}
            </p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
