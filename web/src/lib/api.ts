import { getToken } from "next-auth/jwt";
import type { NextRequest } from "next/server";

const BASE_API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Token JWT de la sesión actual (cookie de Auth.js), en crudo. */
export async function tokenDeSesion(request: NextRequest): Promise<string | null> {
  return getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
    raw: true,
  });
}

/**
 * Llama a la API de FastAPI desde el servidor de Next.js reenviando el
 * token de sesión, para no exponerlo al navegador ni depender de CORS.
 */
export async function llamarApi(
  request: NextRequest,
  ruta: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = await tokenDeSesion(request);
  const cabeceras: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string> | undefined) ?? {}),
  };
  if (token) {
    cabeceras.Authorization = `Bearer ${token}`;
  }

  return fetch(`${BASE_API}${ruta}`, {
    ...init,
    headers: cabeceras,
    cache: "no-store",
  });
}
