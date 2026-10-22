"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { t } from "@/lib/i18n";

type Lista = {
  id: string;
  nombre: string;
};

export function ListarListas({ listas }: { listas: Lista[] }) {
  const router = useRouter();
  const [nombre, setNombre] = useState("");
  const [creando, setCreando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function crear() {
    if (nombre.trim().length === 0 || creando) {
      return;
    }
    setCreando(true);
    setError(null);

    try {
      const respuesta = await fetch("/api/listas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre: nombre.trim() }),
      });
      if (!respuesta.ok) {
        setError(t("lista.error"));
        return;
      }
      setNombre("");
      router.refresh();
    } catch {
      setError(t("lista.error"));
    } finally {
      setCreando(false);
    }
  }

  return (
    <section className="mx-auto max-w-lectura">
      <h1 className="text-2xl font-medium text-texto">{t("listas.titulo")}</h1>

      <form
        className="mt-4 flex gap-2"
        onSubmit={(evento) => {
          evento.preventDefault();
          void crear();
        }}
      >
        <label className="sr-only" htmlFor="nombre-lista">
          {t("listas.nombre")}
        </label>
        <input
          id="nombre-lista"
          type="text"
          value={nombre}
          onChange={(evento) => setNombre(evento.target.value)}
          placeholder={t("listas.nombre_placeholder")}
          className="min-w-0 flex-1 rounded-lg border border-borde-fuerte px-4 py-2 text-sm text-texto focus:border-primario"
        />
        <button
          type="submit"
          disabled={nombre.trim().length === 0 || creando}
          className="rounded-lg bg-primario px-4 py-2 text-sm font-medium text-white transition-colors duration-150 hover:bg-primario-oscuro disabled:cursor-not-allowed disabled:bg-superficie-activa disabled:text-gris"
        >
          {t("listas.crear")}
        </button>
      </form>

      {error ? (
        <p role="alert" className="mt-3 text-sm text-error">
          {error}
        </p>
      ) : null}

      {listas.length === 0 ? (
        <p className="mt-6 text-sm text-gris">{t("listas.vacias")}</p>
      ) : (
        <ul className="mt-6 space-y-2">
          {listas.map((lista) => (
            <li key={lista.id}>
              <Link
                href={`/listas/${lista.id}`}
                className="block rounded-tarjeta border border-borde px-4 py-3 text-sm text-texto transition-colors duration-150 hover:bg-superficie"
              >
                {lista.nombre}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
