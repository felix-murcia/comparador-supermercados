import { llamarApiServidor } from "@/lib/api";
import { VistaLista } from "@/components/listas/VistaLista";
import { SLUGS_CADENAS } from "@/lib/cadenas";
import { t } from "@/lib/i18n";

type Props = {
  params: { id: string };
};

type Item = {
  id: string;
  producto_id: string;
  cantidad: number;
  cadena_compra_id: string | null;
  precio_snapshot: string | null;
  producto_nombre: string | null;
  producto_marca: string | null;
  cadena_compra: string | null;
};

type Lista = {
  id: string;
  nombre: string;
  items: Item[];
};

type CosteCadena = {
  cadena: string;
  coste: string;
  porcentaje_a: number | null;
  productos_no_disponibles: string[];
};

type Resumen = {
  coste_total: string;
  por_cadena: CosteCadena[];
  porcentaje_c: number | null;
  avisos: string[];
};

async function cargarLista(id: string): Promise<Lista | null> {
  try {
    const respuesta = await llamarApiServidor(`/v1/listas/${id}`);
    if (!respuesta.ok) {
      return null;
    }
    return (await respuesta.json()) as Lista;
  } catch {
    return null;
  }
}

async function cargarResumen(id: string): Promise<Resumen | null> {
  try {
    // El resumen compara las cadenas elegidas: sin ellas no hay coste ni % A.
    const parametros = new URLSearchParams();
    for (const cadena of SLUGS_CADENAS) {
      parametros.append("cadenas", cadena);
    }
    const respuesta = await llamarApiServidor(
      `/v1/listas/${id}/resumen?${parametros.toString()}`,
    );
    if (!respuesta.ok) {
      return null;
    }
    return (await respuesta.json()) as Resumen;
  } catch {
    return null;
  }
}

export default async function PaginaLista({ params }: Props) {
  const [lista, resumen] = await Promise.all([
    cargarLista(params.id),
    cargarResumen(params.id),
  ]);

  if (!lista) {
    return (
      <section className="mx-auto max-w-lectura text-center">
        <h1 className="text-2xl font-medium text-texto">
          {t("lista.no_encontrada")}
        </h1>
      </section>
    );
  }

  return <VistaLista lista={lista} resumen={resumen} />;
}
