"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { t } from "@/lib/i18n";

const ENLACES = [
  { href: "/buscar", clave: "menu.buscar" },
  { href: "/listas", clave: "menu.listas" },
  { href: "/perfil", clave: "menu.perfil" },
];

/**
 * Cromo de la aplicación: cabecera, menú lateral colapsable y área de
 * contenido. En móvil el menú se superpone; en escritorio está siempre
 * visible.
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

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-borde bg-white px-4">
        <button
          type="button"
          onClick={() => setAbierto((valor) => !valor)}
          aria-expanded={abierto}
          aria-controls="menu-lateral"
          aria-label={abierto ? t("menu.cerrar") : t("menu.abrir")}
          className="rounded-pill p-2 text-gris hover:bg-primario-suave hover:text-texto md:hidden"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>

        <Link href="/" className="text-base font-medium text-texto">
          {t("app.nombre")}
        </Link>

        {usuario ? (
          <span className="ml-auto text-sm text-gris">{usuario}</span>
        ) : null}
      </header>

      <div className="flex">
        <nav
          id="menu-lateral"
          aria-label={t("menu.titulo")}
          className={`fixed inset-y-0 left-0 z-30 w-64 border-r border-borde bg-white p-4 pt-16 transition-transform md:sticky md:top-14 md:z-0 md:h-[calc(100vh-3.5rem)] md:translate-x-0 md:pt-4 ${
            abierto ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <ul className="space-y-1">
            {ENLACES.map((enlace) => {
              const activo =
                pathname === enlace.href || pathname.startsWith(`${enlace.href}/`);
              return (
                <li key={enlace.href}>
                  <Link
                    href={enlace.href}
                    aria-current={activo ? "page" : undefined}
                    className={`block rounded-pill px-3 py-2 text-sm ${
                      activo
                        ? "bg-primario-suave text-primario-oscuro"
                        : "text-gris hover:bg-primario-suave hover:text-texto"
                    }`}
                  >
                    {t(enlace.clave)}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {abierto ? (
          <div
            className="fixed inset-0 z-20 bg-black/30 md:hidden"
            onClick={() => setAbierto(false)}
            aria-hidden="true"
          />
        ) : null}

        <main className="min-w-0 flex-1 px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
