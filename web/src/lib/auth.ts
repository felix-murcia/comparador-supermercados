import type { NextAuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";
import GoogleProvider from "next-auth/providers/google";

import { codificarToken, decodificarToken, ttlSesionSegundos } from "@/lib/token";

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
