import { GraficaMetricas } from "@/components/admin/GraficaMetricas";
import { llamarApiServidor } from "@/lib/api";
import { t } from "@/lib/i18n";

type Metricas = {
  total: number;
  verificado: number;
  sospechoso: number;
  rechazado: number;
  por_dia: { dia: string; verificado: number; sospechoso: number; rechazado: number }[];
  motivos: { motivo: string; total: number }[];
};

async function cargarMetricas(): Promise<Metricas | null> {
  try {
    const respuesta = await llamarApiServidor("/v1/admin/metricas");
    if (!respuesta.ok) {
      return null;
    }
    return (await respuesta.json()) as Metricas;
  } catch {
    return null;
  }
}

export default async function PaginaMetricas() {
  const metricas = await cargarMetricas();

  if (!metricas) {
    return (
      <section className="mx-auto max-w-lectura text-center">
        <h1 className="text-2xl font-medium text-texto">
          {t("admin.sin_acceso")}
        </h1>
        <p className="mt-2 text-sm text-gris">{t("admin.sin_acceso_detalle")}</p>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-contenido">
      <h1 className="text-2xl font-medium text-texto">{t("admin.titulo")}</h1>

      <div className="mt-4 flex flex-wrap gap-6 text-sm text-gris">
        <p>
          {t("admin.total")}: {metricas.total}
        </p>
        <p>
          {t("admin.verificados")}: {metricas.verificado}
        </p>
        <p>
          {t("admin.sospechosos")}: {metricas.sospechoso}
        </p>
        <p>
          {t("admin.rechazados")}: {metricas.rechazado}
        </p>
      </div>

      <div className="mt-6">
        <GraficaMetricas puntos={metricas.por_dia} />
      </div>

      <h2 className="mt-8 text-lg font-medium text-texto">
        {t("admin.motivos")}
      </h2>
      {metricas.motivos.length === 0 ? (
        <p className="mt-2 text-sm text-gris">{t("admin.sin_motivos")}</p>
      ) : (
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="border-b border-borde text-left text-gris">
              <th scope="col" className="py-2 font-normal">
                {t("admin.motivo")}
              </th>
              <th scope="col" className="py-2 font-normal">
                {t("admin.frecuencia")}
              </th>
            </tr>
          </thead>
          <tbody>
            {metricas.motivos.map((motivo) => (
              <tr key={motivo.motivo} className="border-b border-borde">
                <th scope="row" className="py-2 text-left font-normal">
                  {motivo.motivo}
                </th>
                <td className="py-2">{motivo.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
