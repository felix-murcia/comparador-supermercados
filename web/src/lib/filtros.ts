/**
 * Filtros y orden de la vista de resultados.
 *
 * Se aplican en el cliente sobre los resultados ya cargados: cambiar un
 * filtro no relanza la búsqueda, solo reordena y filtra lo que hay en
 * memoria. El estado vive además en la URL.
 */

export type Orden = "precio_unitario" | "precio_kg_l" | "relevancia";

export type Filtros = {
  orden: Orden;
  precioMin: number | null;
  precioMax: number | null;
  marca: string;
  categoria: string;
  soloConStock: boolean;
};

export const FILTROS_INICIALES: Filtros = {
  orden: "precio_unitario",
  precioMin: null,
  precioMax: null,
  marca: "",
  categoria: "",
  soloConStock: false,
};

export type ResultadoComparacion = {
  posicion: number;
  producto_cadena_id: string;
  nombre: string;
  marca: string | null;
  categoria: string | null;
  formato: string | null;
  cadena: string;
  precio_eur: string;
  precio_por_litro_kg: string | null;
  disponible: boolean | null;
  url_producto: string | null;
};

function coincide(resultado: ResultadoComparacion, filtros: Filtros): boolean {
  const precio = Number(resultado.precio_eur);
  if (filtros.precioMin !== null && precio < filtros.precioMin) {
    return false;
  }
  if (filtros.precioMax !== null && precio > filtros.precioMax) {
    return false;
  }
  if (
    filtros.marca &&
    (resultado.marca ?? "").toLowerCase() !== filtros.marca.toLowerCase()
  ) {
    return false;
  }
  if (filtros.categoria && resultado.categoria !== filtros.categoria) {
    return false;
  }
  if (filtros.soloConStock && resultado.disponible !== true) {
    return false;
  }
  return true;
}

function compararPorNombre(
  izquierda: ResultadoComparacion,
  derecha: ResultadoComparacion,
): number {
  return izquierda.nombre.localeCompare(derecha.nombre, "es");
}

function ordenar(
  resultados: ResultadoComparacion[],
  orden: Orden,
): ResultadoComparacion[] {
  if (orden === "precio_unitario") {
    return [...resultados].sort(
      (izquierda, derecha) =>
        Number(izquierda.precio_eur) - Number(derecha.precio_eur) ||
        compararPorNombre(izquierda, derecha),
    );
  }
  if (orden === "precio_kg_l") {
    return [...resultados].sort((izquierda, derecha) => {
      if (izquierda.precio_por_litro_kg === null) {
        return 1;
      }
      if (derecha.precio_por_litro_kg === null) {
        return -1;
      }
      return (
        Number(izquierda.precio_por_litro_kg) -
          Number(derecha.precio_por_litro_kg) || compararPorNombre(izquierda, derecha)
      );
    });
  }
  // En "relevancia" se respeta el orden que devolvió el servidor.
  return [...resultados];
}

/** Filtra, ordena y renumera el ranking. */
export function aplicarFiltros(
  resultados: ResultadoComparacion[],
  filtros: Filtros,
): ResultadoComparacion[] {
  const filtrados = resultados.filter((resultado) =>
    coincide(resultado, filtros),
  );
  return ordenar(filtrados, filtros.orden).map((resultado, indice) => ({
    ...resultado,
    posicion: indice + 1,
  }));
}

/** Marcas y categorías disponibles en los resultados cargados. */
export function opcionesDisponibles(resultados: ResultadoComparacion[]): {
  marcas: string[];
  categorias: string[];
} {
  const marcas = new Set<string>();
  const categorias = new Set<string>();
  for (const resultado of resultados) {
    if (resultado.marca) {
      marcas.add(resultado.marca);
    }
    if (resultado.categoria) {
      categorias.add(resultado.categoria);
    }
  }
  return {
    marcas: [...marcas].sort((a, b) => a.localeCompare(b, "es")),
    categorias: [...categorias].sort((a, b) => a.localeCompare(b, "es")),
  };
}
