import type { ReactNode } from "react";

/**
 * Iconos de la interfaz.
 *
 * Se dibujan en línea, con trazo (`stroke`) y sin relleno, para no depender
 * de una librería de iconos ni pedir fuentes a un CDN. Todas las geometrías
 * están dentro de una caja de 24x24 y heredan el color del texto con
 * `currentColor`.
 */
export type NombreIcono =
  | "buscar"
  | "listas"
  | "perfil"
  | "menu"
  | "cerrar"
  | "check"
  | "filtros"
  | "mas"
  | "volver"
  | "info"
  | "editar"
  | "candado";

const TRAZOS: Record<NombreIcono, ReactNode> = {
  buscar: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.6-3.6" />
    </>
  ),
  listas: (
    <>
      <path d="M8 6h13M8 12h13M8 18h13" />
      <path d="M3.5 6h.01M3.5 12h.01M3.5 18h.01" />
    </>
  ),
  perfil: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 20.5a7.5 7.5 0 0 1 15 0" />
    </>
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  cerrar: <path d="m6 6 12 12M18 6 6 18" />,
  check: <path d="m5 13 4 4L19 7" />,
  filtros: (
    <>
      <path d="M4 7h9M17 7h3M4 17h3M11 17h9" />
      <circle cx="15" cy="7" r="2" />
      <circle cx="9" cy="17" r="2" />
    </>
  ),
  mas: <path d="M12 5v14M5 12h14" />,
  volver: <path d="m15 18-6-6 6-6" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </>
  ),
  editar: (
    <>
      <path d="M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17v3Z" />
      <path d="m14.5 6.5 3 3" />
    </>
  ),
  candado: (
    <>
      <rect x="4" y="10" width="16" height="10" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </>
  ),
};

export function Icono({
  nombre,
  className,
}: {
  nombre: NombreIcono;
  className?: string;
}) {
  return (
    <svg
      className={className}
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {TRAZOS[nombre]}
    </svg>
  );
}

/** Marca de la aplicación: cuadro con líneas, al estilo de una etiqueta. */
export function Marca({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="2" y="2" width="20" height="20" rx="5.5" fill="currentColor" />
      <path
        d="M7.5 9h9M7.5 12h6M7.5 15h3.5"
        stroke="white"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
    </svg>
  );
}
