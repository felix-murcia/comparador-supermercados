import { GraficaHistorico } from "@/components/producto/GraficaHistorico";
import { llamarApiServidor } from "@/lib/api";
import { t } from "@/lib/i18n";

type Props = {
  params: { slug: string };
  searchParams: { meses?: string; provincia?: string };
};

type PrecioVigente = {
  cadena: string;
  nombre_cadena: string;
  precio_eur: string;
  precio_por_litro_kg: string | null;
  url_producto: string | null;
  fecha_consulta: string | null;
};

type PuntoHistorico = {
  cadena: string;
  fecha: string;
  precio_eur: string;
};

type Ficha = {
  producto: {
    id: string;
    nombre: string;
    marca: string | null;
    categoria: string | null;
    formato: string | null;
    ean: string | null;
    litros_o_kg: string | null;
  };
  precios_actuales: PrecioVigente[];
  historico: PuntoHistorico[];
};

const RANGOS = [
  { meses: 1, clave: "producto.rango_1m" },
  { meses: 3, clave: "producto.rango_3m" },
  { meses: 6, clave: "producto.rango_6m" },
  { meses: 12, clave: "producto.rango_1a" },
];

const PRECIO = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
});

const UNIDAD = new Intl.NumberFormat("es-ES", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

async function cargarFicha(
  slug: string,
  meses: number,
  provincia?: string,
): Promise<Ficha | null> {
  const parametros = new URLSearchParams({ meses: String(meses) });
  if (provincia) {
    parametros.set("provincia", provincia);
  }

  try {
    const respuesta = await llamarApiServidor(
      `/v1/productos/${encodeURIComponent(slug)}?${parametros.toString()}`,
    );
    if (!respuesta.ok) {
      return null;
    }
    return (await respuesta.json()) as Ficha;
  } catch {
    return null;
  }
}

function puntosPorFecha(historico: PuntoHistorico[]) {
  const porFecha = new Map<string, Record<string, string | number>>();
  for (const punto of historico) {
    const fecha = punto.fecha.slice(0, 10);
    const fila = porFecha.get(fecha) ?? {};
    fila[punto.cadena] = Number(punto.precio_eur);
    porFecha.set(fecha, fila);
  }
  return [...porFecha.entries()]
    .sort(([izquierda], [derecha]) => izquierda.localeCompare(derecha))
    .map(([fecha, valores]) => ({ fecha, ...valores }));
}

export default async function PaginaProducto({ params, searchParams }: Props) {
  const meses = Number(searchParams.meses ?? 3);
  const ficha = await cargarFicha(
    params.slug,
    Number.isFinite(meses) && meses > 0 ? meses : 3,
    searchParams.provincia,
  );

  if (!ficha) {
    return (
      <section className="mx-auto max-w-lectura text-center">
        <h1 className="text-2xl font-medium text-texto">
          {t("producto.no_encontrado")}
        </h1>
      </section>
    );
  }

  const puntos = puntosPorFecha(ficha.historico);
  const cadenas = [...new Set(ficha.historico.map((punto) => punto.cadena))];

  return (
    <article className="mx-auto max-w-contenido">
      <header className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-medium text-texto">
            {ficha.producto.nombre}
          </h1>
          <p className="mt-1 text-sm text-gris">
            {[ficha.producto.marca, ficha.producto.formato]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <button
          type="button"
          className="rounded-lg border border-borde px-4 py-2 text-sm text-texto transition-colors duration-150 hover:bg-superficie"
        >
          {t("lista.anadir")}
        </button>
      </header>

      <section className="mt-8">
        <h2 className="text-lg font-medium text-texto">
          {t("producto.precio_actual")}
        </h2>
        {ficha.precios_actuales.length === 0 ? (
          <p className="mt-2 text-sm text-gris">{t("producto.sin_precios")}</p>
        ) : (
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-borde text-left text-gris">
                <th scope="col" className="py-2 font-normal">
                  {t("producto.cadena")}
                </th>
                <th scope="col" className="py-2 font-normal">
                  {t("producto.precio")}
                </th>
                <th scope="col" className="py-2 font-normal">
                  {t("producto.precio_unidad")}
                </th>
                <th scope="col" className="py-2 font-normal">
                  {t("producto.enlace")}
                </th>
              </tr>
            </thead>
            <tbody>
              {ficha.precios_actuales.map((precio) => (
                <tr key={precio.cadena} className="border-b border-borde">
                  <th scope="row" className="py-2 text-left font-normal">
                    {precio.nombre_cadena}
                  </th>
                  <td className="py-2">{PRECIO.format(Number(precio.precio_eur))}</td>
                  <td className="py-2 text-gris">
                    {precio.precio_por_litro_kg
                      ? `${UNIDAD.format(Number(precio.precio_por_litro_kg))} €/kg-L`
                      : "—"}
                  </td>
                  <td className="py-2">
                    {precio.url_producto ? (
                      <a
                        href={precio.url_producto}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primario transition-colors duration-150 hover:underline"
                      >
                        {t("producto.ver_producto")}
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="mt-10">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-medium text-texto">
            {t("producto.historico")}
          </h2>
          <nav aria-label={t("producto.rango")} className="flex gap-1">
            {RANGOS.map((rango) => {
              const activo = rango.meses === meses;
              return (
                <a
                  key={rango.meses}
                  href={`/producto/${params.slug}?meses=${rango.meses}`}
                  aria-current={activo ? "page" : undefined}
                  className={`rounded-pill px-3 py-1 text-sm ${
                    activo
                      ? "bg-primario-suave text-primario-oscuro"
                      : "text-gris transition-colors duration-150 hover:bg-superficie"
                  }`}
                >
                  {t(rango.clave)}
                </a>
              );
            })}
          </nav>
        </div>

        {puntos.length === 0 ? (
          <p className="mt-3 text-sm text-gris">{t("producto.sin_historico")}</p>
        ) : (
          <div className="mt-4">
            <GraficaHistorico puntos={puntos} cadenas={cadenas} />
          </div>
        )}
      </section>
    </article>
  );
}
