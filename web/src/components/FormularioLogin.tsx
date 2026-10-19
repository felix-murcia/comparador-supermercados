"use client";

import { signIn } from "next-auth/react";

import { LogoGoogle, LogoMicrosoft } from "@/components/logos";
import { t } from "@/lib/i18n";

export function FormularioLogin({ destino }: { destino: string }) {
  return (
    <div className="mt-6 flex w-full flex-col gap-3">
      <button
        type="button"
        className="flex w-full items-center justify-center gap-2.5 rounded-pill border border-borde bg-white px-4 py-2.5 text-sm text-texto hover:bg-primario-suave"
        onClick={() => signIn("google", { callbackUrl: destino })}
      >
        <LogoGoogle />
        <span>{t("login.google")}</span>
      </button>
      <button
        type="button"
        className="flex w-full items-center justify-center gap-2.5 rounded-pill border border-borde bg-white px-4 py-2.5 text-sm text-texto hover:bg-primario-suave"
        onClick={() => signIn("microsoft", { callbackUrl: destino })}
      >
        <LogoMicrosoft />
        <span>{t("login.microsoft")}</span>
      </button>
    </div>
  );
}
