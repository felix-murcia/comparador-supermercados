import { getServerSession } from "next-auth";
import type { Session } from "next-auth";

import { authOptions } from "@/lib/auth";

/** Sesión del usuario en un Server Component (null si no hay cookie válida). */
export async function getSession(): Promise<Session | null> {
  return getServerSession(authOptions);
}
