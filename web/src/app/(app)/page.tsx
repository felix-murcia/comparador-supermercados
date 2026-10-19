import { t } from "@/lib/i18n";

export default function PaginaInicio() {
  return (
    <section className="mx-auto max-w-lectura text-center">
      <h1 className="text-3xl font-medium text-texto">{t("inicio.titulo")}</h1>
      <p className="mt-3 text-gris">{t("inicio.subtitulo")}</p>
      <a
        href="/buscar"
        className="mt-6 inline-block rounded-pill bg-primario px-5 py-2.5 text-sm font-medium text-white hover:bg-primario-oscuro"
      >
        {t("inicio.ir_a_buscar")}
      </a>
    </section>
  );
}
