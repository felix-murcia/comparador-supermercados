"use client";

import { useState } from "react";

import { t } from "@/lib/i18n";

type Estado = "inactivo" | "guardando" | "guardado" | "error";

export function FormularioPerfil({
  nombreInicial,
  provinciaInicial,
  provincias,
}: {
  nombreInicial: string;
  provinciaInicial: string;
  provincias: string[];
}) {
  const [nombre, setNombre] = useState(nombreInicial);
  const [provincia, setProvincia] = useState(provinciaInicial);
  const [estado, setEstado] = useState<Estado>("inactivo");
  const [error, setError] = useState<string | null>(null);

  async function guardar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setEstado("guardando");
    setError(null);

    try {
      const respuesta = await fetch("/api/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre, provincia }),
      });
      const datos = await respuesta.json().catch(() => ({}));

      if (!respuesta.ok) {
        setError(
          typeof datos.message === "string" ? datos.message : t("perfil.error"),
        );
        setEstado("error");
        return;
      }
      setEstado("guardado");
    } catch {
      setError(t("perfil.error"));
      setEstado("error");
    }
  }

  return (
    <form className="mt-6 max-w-lectura" onSubmit={(evento) => void guardar(evento)}>
      <div>
        <label className="block text-sm text-gris" htmlFor="nombre">
          {t("perfil.nombre")}
        </label>
        <input
          id="nombre"
          name="nombre"
          type="text"
          value={nombre}
          onChange={(evento) => setNombre(evento.target.value)}
          placeholder={t("perfil.nombre_placeholder")}
          className="mt-1 w-full rounded-lg border border-borde bg-white px-3.5 py-2.5 text-sm text-texto transition-colors duration-150 hover:border-borde-fuerte focus:border-primario"
        />
      </div>

      <div className="mt-4">
        <label className="block text-sm text-gris" htmlFor="provincia">
          {t("perfil.provincia")}
        </label>
        <select
          id="provincia"
          name="provincia"
          value={provincia}
          onChange={(evento) => setProvincia(evento.target.value)}
          className="mt-1 w-full rounded-lg border border-borde bg-white px-3.5 py-2.5 text-sm text-texto transition-colors duration-150 hover:border-borde-fuerte focus:border-primario"
        >
          <option value="">{t("perfil.provincia_sin_elegir")}</option>
          {provincias.map((provincia) => (
            <option key={provincia} value={provincia}>
              {provincia}
            </option>
          ))}
        </select>
        <p className="mt-2 text-xs text-gris">{t("perfil.descripcion")}</p>
      </div>

      <button
        type="submit"
        disabled={estado === "guardando"}
        className="mt-6 rounded-lg bg-primario px-5 py-2.5 text-sm font-medium text-white transition-colors duration-150 hover:bg-primario-oscuro disabled:cursor-not-allowed disabled:bg-superficie-activa disabled:text-gris"
      >
        {estado === "guardando" ? t("perfil.guardando") : t("perfil.guardar")}
      </button>

      {estado === "guardado" ? (
        <p role="status" className="mt-3 text-sm text-gris">
          {t("perfil.guardado")}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-3 text-sm text-error">
          {error}
        </p>
      ) : null}
    </form>
  );
}
