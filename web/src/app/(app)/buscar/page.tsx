import { VistaBusqueda } from "@/components/buscador/VistaBusqueda";
import { llamarApiServidor } from "@/lib/api";

type Props = {
  searchParams: {
    q?: string;
    cadenas?: string;
    job?: string;
    cache?: string;
  };
};

type Resultado = {
  posicion: number;
  producto_cadena_id: string;
  nombre: string;
  marca: string | null;
  formato: string | null;
  cadena: string;
  precio_eur: string;
  precio_por_litro_kg: string | null;
  url_producto: string | null;
};

async function cargarResultados(
  consulta: string,
  cadenas: string[],
): Promise<Resultado[]> {
  if (!consulta) {
    return [];
  }
  const parametros = new URLSearchParams({ q: consulta });
  for (const cadena of cadenas) {
    parametros.append("cadenas", cadena);
  }

  try {
    const respuesta = await llamarApiServidor(`/v1/comparar?${parametros.toString()}`);
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

  // Los resultados se cargan en el servidor para que las cards arrive en el HTML.
  const resultados = await cargarResultados(consulta, cadenas);

  return (
    <VistaBusqueda
      consulta={consulta}
      cadenas={cadenas}
      job={job}
      cacheHit={cacheHit}
      resultadosIniciales={resultados}
    />
  );
}
