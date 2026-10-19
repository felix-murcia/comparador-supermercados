"use client";

import { t } from "@/lib/i18n";

/** Barra de progreso con el porcentaje real del job. */
export function BarraProgreso({ progreso }: { progreso: number }) {
  const valor = Math.max(0, Math.min(100, progreso));

  return (
    <div className="w-full">
      <div
        role="progressbar"
        aria-valuenow={valor}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={t("buscar.progreso")}
        className="h-2 w-full overflow-hidden rounded-pill bg-primario-suave"
      >
        <div
          className="h-2 rounded-pill bg-primario transition-[width] duration-500"
          style={{ width: `${valor}%` }}
        />
      </div>
      <p className="mt-2 text-center text-sm text-gris">
        {t("buscar.progreso_texto")} {valor}%
      </p>
    </div>
  );
}
