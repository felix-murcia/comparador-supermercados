/** Cadenas de supermercado soportadas por el comparador. */
export const CADENAS = [
  { slug: "dia", nombre: "DIA" },
  { slug: "carrefour", nombre: "Carrefour" },
  { slug: "mercadona", nombre: "Mercadona" },
] as const;

/** Slugs de las cadenas, en el orden en que se muestran. */
export const SLUGS_CADENAS: string[] = CADENAS.map((cadena) => cadena.slug);

/** Nombre legible de una cadena a partir de su slug. */
export function nombreCadena(slug: string): string {
  return CADENAS.find((cadena) => cadena.slug === slug)?.nombre ?? slug;
}
