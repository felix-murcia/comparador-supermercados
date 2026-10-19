import { t } from "@/lib/i18n";

export default function PaginaPerfil() {
  return (
    <section className="mx-auto max-w-lectura">
      <h1 className="text-2xl font-medium text-texto">{t("perfil.titulo")}</h1>
      <p className="mt-2 text-gris">{t("proximamente")}</p>
    </section>
  );
}
