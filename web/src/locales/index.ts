import es from "./es.json";

/**
 * Diccionarios de traducción disponibles.
 *
 * Para añadir otro idioma basta con importar su archivo y añadirlo aquí
 * (por ejemplo `en.json`): ni `t()` ni los componentes necesitan cambios.
 */
export const TRADUCCIONES = { es } as const;

export type Locale = keyof typeof TRADUCCIONES;

export const LOCALE_POR_DEFECTO: Locale = "es";
