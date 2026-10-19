import { SignJWT, jwtVerify } from "jose";
import type { JWT, JWTDecodeParams, JWTEncodeParams } from "next-auth/jwt";

const ALGORITMO = "HS256";
const SEGUNDOS_POR_DEFECTO = 60 * 60 * 24 * 30; // 30 días

export function ttlSesionSegundos(): number {
  const configurado = Number(process.env.SESSION_TTL_SEGUNDOS);
  return Number.isFinite(configurado) && configurado > 0
    ? configurado
    : SEGUNDOS_POR_DEFECTO;
}

function claveFirma(secreto: string | Buffer): Uint8Array {
  return new TextEncoder().encode(secreto.toString());
}

/**
 * JWT propio (HS256) en lugar del JWE por defecto de Auth.js: la API de
 * FastAPI valida el mismo token con `NEXTAUTH_SECRET` (ADR-012).
 */
export async function codificarToken({
  token,
  secret,
  maxAge,
}: JWTEncodeParams): Promise<string> {
  const ahora = Math.floor(Date.now() / 1000);
  const ttl = maxAge ?? ttlSesionSegundos();
  return new SignJWT({ ...token })
    .setProtectedHeader({ alg: ALGORITMO, typ: "JWT" })
    .setIssuedAt(ahora)
    .setExpirationTime(ahora + ttl)
    .sign(claveFirma(secret));
}

export async function decodificarToken({
  token,
  secret,
}: JWTDecodeParams): Promise<JWT | null> {
  if (!token) {
    return null;
  }
  try {
    const { payload } = await jwtVerify(token, claveFirma(secret), {
      algorithms: [ALGORITMO],
    });
    return payload as JWT;
  } catch {
    return null;
  }
}
