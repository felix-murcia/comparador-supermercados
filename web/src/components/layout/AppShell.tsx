"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { Icono, Marca } from "@/components/ui/Icono";
import { t } from "@/lib/i18n";
import type { NombreIcono } from "@/components/ui/Icono";

const ENLACES: { href: string; clave: string; icono: NombreIcono }[] = [
  { href: "/buscar", clave: "menu.buscar", icono: "buscar" },
  { href: "/listas", clave: "menu.listas", icono: "listas" },
  { href: "/perfil", clave: "menu.perfil", icono: "perfil" },
];

/** Clase del enlace de navegación, con o sin estado activo. */
function claseEnlace(activo: boolean) {
  return `group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors duration-150 ${
    activo
      ? "bg-superficie-activa font-medium text-texto"
      : "text-gris hover:bg-superficie hover:text-texto"
  }`;
}

/**
 * Cromo de la aplicación: barra lateral fija y área de contenido.
 *
 * En escritorio la barra lateral es permanente y estrecha (14rem); en
 * móvil se dibuja encima del contenido. La marca de la aplicación vive en
 * la propia barra lateral, como en los paneles de Linear o Vercel, así que
 * la cabecera superior solo aparece en pantallas estrechas.
 */
export function AppShell({
  children,
  usuario,
}: {
  children: ReactNode;
  usuario: string | null;
}) {
  const [abierto, setAbierto] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setAbierto(false);
  }, [pathname]);

  const navegacion = (
    <>
      <p className="px-2.5 pb-1.5 text-[11px] font-medium uppercase tracking-wide text-gris">
        {t("menu.seccion")}
      </p>
      <ul className="space-y-0.5">
        {ENLACES.map((enlace) => {
          const activo =
            pathname === enlace.href || pathname.startsWith(`${enlace.href}/`);
          return (
            <li key={enlace.href}>
              <Link
                href={enlace.href}
                aria-current={activo ? "page" : undefined}
                className={claseEnlace(activo)}
              >
                <Icono
                  nombre={enlace.icono}
                  className="h-[18px] w-[18px] shrink-0"
                />
                <span className="truncate">{t(enlace.clave)}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </>
  );

  const pie = usuario ? (
    <div className="border-t border-borde p-3">
      <p className="truncate text-sm text-texto">{usuario}</p>
    </div>
  ) : null;

  return (
    <div className="min-h-screen">
      {/* Cabecera solo en móvil: en escritorio la marca vive en la barra. */}
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-borde bg-white px-4 md:hidden">
        <button
          type="button"
          onClick={() => setAbierto((valor) => !valor)}
          aria-expanded={abierto}
          aria-controls="menu-lateral"
          aria-label={abierto ? t("menu.cerrar") : t("menu.abrir")}
          className="rounded-lg p-2 text-gris transition-colors duration-150 hover:bg-superficie hover:text-texto"
        >
          <Icono nombre="menu" />
        </button>
        <Link href="/" className="flex items-center gap-2 text-base font-medium text-texto">
          <Marca className="h-5 w-5 text-texto" />
          {t("app.nombre")}
        </Link>
      </header>

      {/* Barra lateral de escritorio. */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col border-r border-borde bg-white md:flex">
        <Link
          href="/"
          className="flex h-14 shrink-0 items-center gap-2.5 border-b border-borde px-4 text-sm font-medium text-texto"
        >
          <Marca className="h-6 w-6 shrink-0 text-texto" />
          <span className="truncate">{t("app.nombre")}</span>
        </Link>
        <nav
          id="menu-lateral-escritorio"
          aria-label={t("menu.titulo")}
          className="flex-1 overflow-y-auto p-3"
        >
          {navegacion}
        </nav>
        {pie}
      </aside>

      {/* Menú lateral de móvil, superpuesto al contenido. */}
      {abierto ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <nav
            id="menu-lateral"
            aria-label={t("menu.titulo")}
            className="flex h-full w-64 flex-col border-r border-borde bg-white shadow-sm"
          >
            <div className="flex h-14 shrink-0 items-center justify-between border-b border-borde px-4">
              <span className="text-[15px] font-medium text-texto">
                {t("app.nombre")}
              </span>
              <button
                type="button"
                onClick={() => setAbierto(false)}
                aria-label={t("menu.cerrar")}
                className="rounded-lg p-2 text-gris transition-colors duration-150 hover:bg-superficie hover:text-texto"
              >
                <Icono nombre="cerrar" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-3">{navegacion}</div>
            {pie}
          </nav>
          <div
            className="absolute inset-0 -z-10 bg-black/30"
            onClick={() => setAbierto(false)}
            aria-hidden="true"
          />
        </div>
      ) : null}

      <div className="md:pl-56">
        <main className="min-w-0 px-4 py-6 sm:px-6 md:py-8">{children}</main>
      </div>
    </div>
  );
}
