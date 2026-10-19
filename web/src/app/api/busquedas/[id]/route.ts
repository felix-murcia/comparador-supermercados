import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { llamarApi } from "@/lib/api";

/** Proxy de la web hacia `GET /v1/busquedas/{id}` de la API. */
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  const respuesta = await llamarApi(request, `/v1/busquedas/${params.id}`);
  const datos = await respuesta.json().catch(() => ({}));

  return NextResponse.json(datos, { status: respuesta.status });
}
