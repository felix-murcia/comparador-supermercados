import es from "@/locales/es.json";

/**
 * Cadenas de la interfaz. La clave usa puntos para la jerarquía
 * (`menu.buscar`) y el objeto de traducciones se puede ampliar con
 * `en.json` sin tocar los componentes.
 */
export function t(clave: string): string {
  const valor = clave
    .split(".")
    .reduce<unknown>(
      (actual, parte) =>
        actual && typeof actual === "object" && parte in actual
          ? (actual as Record<string, unknown>)[parte]
          : undefined,
      es as unknown,
    );

  return typeof valor === "string" ? valor : clave;
}
