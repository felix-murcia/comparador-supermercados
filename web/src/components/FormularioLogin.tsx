"use client";

import { signIn } from "next-auth/react";

import { LogoGoogle, LogoMicrosoft } from "@/components/logos";
import { t } from "@/lib/i18n";

type Props = {
  destino: string;
  microsoftDisponible: boolean;
};

export function FormularioLogin({ destino, microsoftDisponible }: Props) {
  return (
    <div className="mt-6 flex w-full flex-col gap-3">
      <button
        type="button"
        className="flex w-full items-center justify-center gap-2.5 rounded-lg border border-borde bg-white px-4 py-2.5 text-sm text-texto transition-colors duration-150 hover:bg-superficie"
        onClick={() => signIn("google", { callbackUrl: destino })}
      >
        <LogoGoogle />
        <span>{t("login.google")}</span>
      </button>
      <button
        type="button"
        className="flex w-full items-center justify-center gap-2.5 rounded-lg border border-borde bg-white px-4 py-2.5 text-sm text-texto transition-colors duration-150 hover:bg-superficie disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-white"
        onClick={() => signIn("microsoft", { callbackUrl: destino })}
        disabled={!microsoftDisponible}
        title={microsoftDisponible ? undefined : t("login.microsoft_no_disponible")}
      >
        <LogoMicrosoft />
        <span>{t("login.microsoft")}</span>
      </button>
      {microsoftDisponible ? null : (
        <p className="text-center text-xs text-gris">
          {t("login.microsoft_no_disponible")}
        </p>
      )}
    </div>
  );
}
