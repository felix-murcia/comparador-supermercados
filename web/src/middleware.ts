import { getToken } from "next-auth/jwt";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { decodificarToken } from "@/lib/token";

const RUTA_LOGIN = "/login";

/**
 * Protege las rutas de la aplicación: sin sesión válida se redirige a
 * `/login`; con sesión en `/login` se vuelve a la raíz.
 */
export async function middleware(request: NextRequest) {
  const token = await getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
    decode: decodificarToken,
  });
  const { pathname, search } = request.nextUrl;

  if (pathname === RUTA_LOGIN) {
    if (!token) {
      return NextResponse.next();
    }
    return NextResponse.redirect(new URL("/", request.url));
  }

  if (!token) {
    const login = new URL(RUTA_LOGIN, request.url);
    login.searchParams.set("callbackUrl", `${pathname}${search}`);
    return NextResponse.redirect(login);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api/auth|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js|map|xml|txt|webmanifest)$).*)",
  ],
};
