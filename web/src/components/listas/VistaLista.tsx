"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { AvisoEquivalencias } from "@/components/listas/AvisoEquivalencias";
import { CabeceraLista } from "@/components/listas/CabeceraLista";
import { ComparativaCadenas } from "@/components/listas/ComparativaCadenas";
import { FilaProducto } from "@/components/listas/FilaProducto";
import { ModalAnadirProducto } from "@/components/listas/ModalAnadirProducto";
import type { Candidato } from "@/components/listas/ModalAnadirProducto";
import type { Item, Lista, Resumen } from "@/components/listas/tipos";
import { t } from "@/lib/i18n";

type Props = {
  lista: Lista;
  resumen: Resumen | null;
};

/**
 * Vista de la lista de la compra.
 *
 * El orden es el de las preguntas de quien la abre: primero dónde sale más
 * barata, después cuánto costaría en cada cadena, y al final los
 * productos, uno por línea y sin ocupar media pantalla cada uno.
 */
export function VistaLista({ lista, resumen }: Props) {
  const router = useRouter();
  const [items, setItems] = useState<Item[]>(lista.items);
  const [borrando, setBorrando] = useState<string | null>(null);
  const [modal, setModal] = useState(false);
  const [editando, setEditando] = useState(false);
  const botonAbrir = useRef<HTMLButtonElement | null>(null);

  // Los items vienen del servidor, pero se guardan en estado para poder
  // actualizarlos al vuelo (borrar, cambiar la cantidad). Al añadir un
  // producto, `router.refresh()` trae la lista nueva por prop, pero el
  // estado local no se reinicia solo: el coste (que llega por prop) se
  // actualizaba y el producto no aparecía en la lista.
  useEffect(() => {
    setItems(lista.items);
  }, [lista.items]);

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
    setBorrando(null);
    if (respuesta.ok) {
      setItems((actuales) => actuales.filter((otro) => otro.id !== item.id));
    }
    router.refresh();
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
      return;
    }
    setModal(false);
    router.refresh();
  }

  async function renombrar(nombre: string) {
    setEditando(false);
    const respuesta = await fetch(`/api/listas/${lista.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre }),
    });
    if (respuesta.ok) {
      router.refresh();
    }
  }

  const resumenPorProducto = new Map(
    (resumen?.productos ?? []).map((producto) => [
      producto.producto_id,
      producto,
    ]),
  );

  return (
    <section className="mx-auto max-w-contenido">
      <CabeceraLista
        nombre={lista.nombre}
        resumen={resumen}
        editando={editando}
        onEmpezarEdicion={() => setEditando(true)}
        onGuardarNombre={(nombre) => void renombrar(nombre)}
        onAnadir={() => {
          setModal(true);
          botonAbrir.current?.focus();
        }}
      />

      {resumen ? (
        <div className="mt-8 space-y-8">
          <ComparativaCadenas por_cadena={resumen.por_cadena} />
          <AvisoEquivalencias productos={resumen.productos} />
        </div>
      ) : null}

      <div className="mt-8">
        <h2 className="text-sm font-medium text-texto">
          {t("lista.productos", { numero: items.length })}
        </h2>
        {items.length === 0 ? (
          <p className="mt-3 text-sm text-gris">{t("lista.sin_productos")}</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {items.map((item) => (
              <FilaProducto
                key={item.id}
                item={item}
                producto={resumenPorProducto.get(item.producto_id)}
                onCantidad={(item, cantidad) => void cambiarCantidad(item, cantidad)}
                onEliminar={(item) => setBorrando(item.id)}
                borrando={borrando === item.id}
                onConfirmarBorrado={(item) => void eliminarItem(item)}
                onCancelarBorrado={() => setBorrando(null)}
              />
            ))}
          </ul>
        )}
      </div>

      <ModalAnadirProducto
        abierto={modal}
        onCerrar={() => setModal(false)}
        onAnadir={(candidato) => void anadir(candidato)}
      />
    </section>
  );
}
