import { LOCALE_POR_DEFECTO, TRADUCCIONES } from "@/locales";

/**
 * Cadenas de la interfaz. La clave usa puntos para la jerarquía
 * (`menu.buscar`) y los valores admiten marcadores `{nombre}`.
 *
 * La función es pura y no depende del contexto, así que sirve igual en
 * Server Components y en Client Components.
 */
export function t(
  clave: string,
  valores?: Record<string, string | number>,
): string {
  const diccionario = TRADUCCIONES[LOCALE_POR_DEFECTO] as unknown as Record<
    string,
    unknown
  >;
  const valor = clave
    .split(".")
    .reduce<unknown>(
      (actual, parte) =>
        actual && typeof actual === "object" && parte in actual
          ? (actual as Record<string, unknown>)[parte]
          : undefined,
      diccionario,
    );

  const texto = typeof valor === "string" ? valor : clave;
  if (!valores) {
    return texto;
  }
  return Object.entries(valores).reduce(
    (resultado, [nombre, replacement]) =>
      resultado.replaceAll(`{${nombre}}`, String(replacement)),
    texto,
  );
}
