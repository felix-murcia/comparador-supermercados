"use client";

import { signIn } from "next-auth/react";

import { LogoGoogle, LogoMicrosoft } from "@/components/logos";
import es from "@/locales/es.json";

export function FormularioLogin({ destino }: { destino: string }) {
  return (
    <div className="login__botones">
      <button
        type="button"
        className="login__boton"
        onClick={() => signIn("google", { callbackUrl: destino })}
      >
        <LogoGoogle />
        <span>{es.login.google}</span>
      </button>
      <button
        type="button"
        className="login__boton"
        onClick={() => signIn("microsoft", { callbackUrl: destino })}
      >
        <LogoMicrosoft />
        <span>{es.login.microsoft}</span>
      </button>
    </div>
  );
}
