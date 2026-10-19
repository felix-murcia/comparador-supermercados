import type { ReactNode } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { getSession } from "@/lib/session";

export default async function LayoutApp({ children }: { children: ReactNode }) {
  const session = await getSession();
  const usuario = session?.user?.name ?? session?.user?.email ?? null;

  return <AppShell usuario={usuario}>{children}</AppShell>;
}
