import { llamarApiServidor } from "@/lib/api";
import { VistaLista } from "@/components/listas/VistaLista";
import type { Lista, Resumen } from "@/components/listas/tipos";
import { SLUGS_CADENAS } from "@/lib/cadenas";
import { t } from "@/lib/i18n";

type Props = {
  params: { id: string };
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
