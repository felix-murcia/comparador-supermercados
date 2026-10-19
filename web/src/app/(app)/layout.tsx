import Link from "next/link";
import type { ReactNode } from "react";

import { getSession } from "@/lib/session";
import es from "@/locales/es.json";

export default async function LayoutApp({ children }: { children: ReactNode }) {
  const session = await getSession();
  const usuario = session?.user?.name ?? session?.user?.email ?? "";

  return (
    <div className="app">
      <header className="app__cabecera">
        <Link className="app__marca" href="/">
          {es.app.nombre}
        </Link>
        <span className="app__usuario">{usuario}</span>
      </header>
      <main className="app__contenido">{children}</main>
    </div>
  );
}
