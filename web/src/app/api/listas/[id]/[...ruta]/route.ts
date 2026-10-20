import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { llamarApi } from "@/lib/api";

type Contexto = {
  params: { id: string; ruta: string[] };
};

/** Proxy genérico de las listas hacia la API (`/v1/listas/...`). */
async function reenviar(request: NextRequest, metodo: string, contexto: Contexto) {
  const { id, ruta } = contexto.params;
  const destino = ruta?.length
    ? `/v1/listas/${id}/${ruta.join("/")}`
    : `/v1/listas/${id}`;

  const conCuerpo = metodo !== "GET" && metodo !== "DELETE";
  const cuerpo = conCuerpo ? await request.json().catch(() => ({})) : undefined;

  const respuesta = await llamarApi(request, destino, {
    method: metodo,
    ...(cuerpo === undefined ? {} : { body: JSON.stringify(cuerpo) }),
  });
  const datos = await respuesta.json().catch(() => ({}));

  return NextResponse.json(datos, { status: respuesta.status });
}

export async function GET(request: NextRequest, contexto: Contexto) {
  return reenviar(request, "GET", contexto);
}

export async function POST(request: NextRequest, contexto: Contexto) {
  return reenviar(request, "POST", contexto);
}

export async function PATCH(request: NextRequest, contexto: Contexto) {
  return reenviar(request, "PATCH", contexto);
}

export async function DELETE(request: NextRequest, contexto: Contexto) {
  return reenviar(request, "DELETE", contexto);
}
