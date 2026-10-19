import { t } from "@/lib/i18n";

export default function PaginaListas() {
  return (
    <section className="mx-auto max-w-lectura">
      <h1 className="text-2xl font-medium text-texto">{t("listas.titulo")}</h1>
      <p className="mt-2 text-gris">{t("proximamente")}</p>
    </section>
  );
}
