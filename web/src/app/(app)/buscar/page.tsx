import { t } from "@/lib/i18n";

export default function PaginaBuscar() {
  return (
    <section className="mx-auto max-w-lectura">
      <h1 className="text-2xl font-medium text-texto">{t("buscar.titulo")}</h1>
      <form className="mt-4 flex gap-2" action="/buscar" method="get">
        <label className="sr-only" htmlFor="q">
          {t("buscar.campo")}
        </label>
        <input
          className="min-w-0 flex-1 rounded-pill border border-borde px-4 py-2.5 text-sm text-texto placeholder:text-gris focus:border-primario"
          id="q"
          name="q"
          type="search"
          placeholder={t("buscar.placeholder")}
        />
        <button
          className="rounded-pill bg-primario px-5 py-2.5 text-sm font-medium text-white hover:bg-primario-oscuro"
          type="submit"
        >
          {t("buscar.boton")}
        </button>
      </form>
    </section>
  );
}
