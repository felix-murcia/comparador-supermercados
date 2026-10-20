import { FormularioLogin } from "@/components/FormularioLogin";
import { t } from "@/lib/i18n";

type Props = {
  searchParams: { callbackUrl?: string | string[] };
};

export default function PaginaLogin({ searchParams }: Props) {
  const destino =
    typeof searchParams.callbackUrl === "string" ? searchParams.callbackUrl : "/";

  // Sin credenciales configuradas, el botón de Microsoft se muestra
  // deshabilitado en lugar de fallar al pulsar.
  const microsoftDisponible = Boolean(process.env.MICROSOFT_CLIENT_ID);

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="flex w-full max-w-sm flex-col items-center">
        <h1 className="text-center text-2xl font-medium text-texto">
          {t("login.titulo")}
        </h1>
        <p className="mt-2 text-center text-sm text-gris">{t("login.subtitulo")}</p>
        <FormularioLogin
          destino={destino}
          microsoftDisponible={microsoftDisponible}
        />
        <p className="mt-6 text-center text-xs text-gris">{t("login.legal")}</p>
      </div>
    </main>
  );
}
