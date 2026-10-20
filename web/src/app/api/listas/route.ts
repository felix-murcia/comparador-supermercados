import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { llamarApi } from "@/lib/api";

/** Proxy de la colección de listas hacia la API (`/v1/listas`). */
async function reenviar(request: NextRequest, metodo: string) {
  const conCuerpo = metodo !== "GET";
  const cuerpo = conCuerpo ? await request.json().catch(() => ({})) : undefined;

  const respuesta = await llamarApi(request, "/v1/listas", {
    method: metodo,
    ...(cuerpo === undefined ? {} : { body: JSON.stringify(cuerpo) }),
  });
  const datos = await respuesta.json().catch(() => ({}));

  return NextResponse.json(datos, { status: respuesta.status });
}

export async function GET(request: NextRequest) {
  return reenviar(request, "GET");
}

export async function POST(request: NextRequest) {
  return reenviar(request, "POST");
}
