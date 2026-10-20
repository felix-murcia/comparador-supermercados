import { cookies } from "next/headers";
import { getToken } from "next-auth/jwt";
import { NextRequest } from "next/server";
import type { NextRequest as NextRequestTipo } from "next/server";

// URL interna del servicio de API dentro de la red de Compose. Las llamadas
// se hacen siempre desde el servidor (route handlers y Server Components),
// nunca desde el navegador, que usa los proxies /api/* de Next.
const BASE_API = process.env.API_INTERNAL_URL ?? "http://api:8000";

/** Token JWT de la sesión actual (cookie de Auth.js), en crudo. */
export async function tokenDeSesion(
  request: NextRequestTipo,
): Promise<string | null> {
  return getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
    raw: true,
  });
}

/** Token de la sesión en un Server Component (lee las cookies de la petición). */
export async function tokenDeSesionCookies(): Promise<string | null> {
  const almacen = await cookies();
  const cabecera = almacen
    .getAll()
    .map((cookie) => `${cookie.name}=${cookie.value}`)
    .join("; ");
  if (!cabecera) {
    return null;
  }

  const peticion = new NextRequest(
    process.env.NEXTAUTH_URL ?? "http://localhost:3000",
    { headers: new Headers({ cookie: cabecera }) },
  );
  return getToken({
    req: peticion,
    secret: process.env.NEXTAUTH_SECRET,
    raw: true,
  });
}

/**
 * Llama a la API de FastAPI desde el servidor de Next.js reenviando el
 * token de sesión, para no exponerlo al navegador ni depender de CORS.
 */
export async function llamarApi(
  request: NextRequestTipo,
  ruta: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = await tokenDeSesion(request);
  return _llamar(ruta, init, token);
}

/** Igual que `llamarApi`, pero desde un Server Component (lee las cookies). */
export async function llamarApiServidor(
  ruta: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = await tokenDeSesionCookies();
  return _llamar(ruta, init, token);
}

async function _llamar(
  ruta: string,
  init: RequestInit,
  token: string | null,
): Promise<Response> {
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
