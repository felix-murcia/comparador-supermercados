import type { NextAuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";
import GoogleProvider from "next-auth/providers/google";
import type { JWT } from "next-auth/jwt";
import { SignJWT, jwtVerify } from "jose";

const SEGUNDOS_POR_DEFECTO = 60 * 60 * 24 * 30; // 30 días

function ttlSesionSegundos(): number {
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
async function codificarToken({
  token,
  secret,
  maxAge,
}: {
  token?: JWT;
  secret: string | Buffer;
  maxAge?: number;
}): Promise<string> {
  const ahora = Math.floor(Date.now() / 1000);
  const ttl = maxAge ?? ttlSesionSegundos();
  return new SignJWT({ ...token })
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setIssuedAt(ahora)
    .setExpirationTime(ahora + ttl)
    .sign(claveFirma(secret));
}

async function decodificarToken({
  token,
  secret,
}: {
  token?: string;
  secret: string | Buffer;
}): Promise<JWT | null> {
  if (!token) {
    return null;
  }
  try {
    const { payload } = await jwtVerify(token, claveFirma(secret), {
      algorithms: ["HS256"],
    });
    return payload as JWT;
  } catch {
    return null;
  }
}

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
    }),
    AzureADProvider({
      id: "microsoft",
      name: "Microsoft",
      clientId: process.env.MICROSOFT_CLIENT_ID ?? "",
      clientSecret: process.env.MICROSOFT_CLIENT_SECRET ?? "",
      tenantId: process.env.MICROSOFT_TENANT_ID ?? "common",
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET,
  session: {
    strategy: "jwt",
    maxAge: ttlSesionSegundos(),
  },
  jwt: {
    encode: codificarToken,
    decode: decodificarToken,
  },
  pages: {
    signIn: "/login",
  },
  callbacks: {
    jwt({ token, account }) {
      if (account) {
        token.provider = account.provider;
        token.provider_id = account.providerAccountId;
      }
      return token;
    },
  },
};
