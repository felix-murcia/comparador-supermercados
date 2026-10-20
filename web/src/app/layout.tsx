import type { Metadata } from "next";
import type { ReactNode } from "react";

import { t } from "@/lib/i18n";

import "./globals.css";

export const metadata: Metadata = {
  title: t("meta.titulo"),
  description: t("meta.descripcion"),
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
