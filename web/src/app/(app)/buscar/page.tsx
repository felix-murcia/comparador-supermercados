import { VistaBusqueda } from "@/components/buscador/VistaBusqueda";
import { llamarApiServidor } from "@/lib/api";
import { FILTROS_INICIALES } from "@/lib/filtros";
import type { Filtros, Orden, ResultadoComparacion } from "@/lib/filtros";

type Props = {
  searchParams: {
    q?: string;
    cadenas?: string;
    job?: string;
    cache?: string;
    orden?: string;
    precio_min?: string;
    precio_max?: string;
    marca?: string;
    categoria?: string;
    solo_con_stock?: string;
  };
};

function filtrosDesdeParams(params: Props["searchParams"]): Filtros {
  const numero = (valor?: string): number | null => {
    if (!valor) {
      return null;
    }
    const parsed = Number(valor);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const orden: Orden =
    params.orden === "precio_kg_l" || params.orden === "relevancia"
      ? params.orden
      : FILTROS_INICIALES.orden;

  return {
    orden,
    precioMin: numero(params.precio_min),
    precioMax: numero(params.precio_max),
    marca: params.marca ?? "",
    categoria: params.categoria ?? "",
    soloConStock: params.solo_con_stock === "1",
  };
}

async function cargarResultados(
  consulta: string,
  cadenas: string[],
): Promise<ResultadoComparacion[]> {
  if (!consulta) {
    return [];
  }
  const parametros = new URLSearchParams({ q: consulta });
  for (const cadena of cadenas) {
    parametros.append("cadenas", cadena);
  }

  try {
    const respuesta = await llamarApiServidor(
      `/v1/comparar?${parametros.toString()}`,
    );
    const datos = await respuesta.json();
    return Array.isArray(datos.resultados) ? datos.resultados : [];
  } catch {
    return [];
  }
}

export default async function PaginaBuscar({ searchParams }: Props) {
  const consulta = searchParams.q ?? "";
  const cadenas = (searchParams.cadenas ?? "").split(",").filter(Boolean);
  const job = searchParams.job ?? null;
  const cacheHit = searchParams.cache === "1";

  // Los resultados se cargan en el servidor para que las cards lleguen en el HTML.
  const resultados = await cargarResultados(consulta, cadenas);

  return (
    <VistaBusqueda
      consulta={consulta}
      cadenas={cadenas}
      job={job}
      cacheHit={cacheHit}
      resultadosIniciales={resultados}
      filtrosIniciales={filtrosDesdeParams(searchParams)}
    />
  );
}
