import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { llamarApi } from "@/lib/api";

/** Proxy de la web hacia `PATCH /v1/me` de la API. */
export async function PATCH(request: NextRequest) {
  const cuerpo = await request.json().catch(() => ({}));
  const respuesta = await llamarApi(request, "/v1/me", {
    method: "PATCH",
    body: JSON.stringify(cuerpo),
  });
  const datos = await respuesta.json().catch(() => ({}));

  return NextResponse.json(datos, { status: respuesta.status });
}
