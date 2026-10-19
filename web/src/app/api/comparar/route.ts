import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { llamarApi } from "@/lib/api";

const PARAMETROS = [
  "q",
  "orden",
  "precio_min",
  "precio_max",
  "marca",
  "categoria",
  "solo_con_stock",
  "provincia",
  "limit",
  "offset",
];

/** Proxy de la web hacia `GET /v1/comparar` de la API. */
export async function GET(request: NextRequest) {
  const entrantes = new URL(request.url).searchParams;
  const salientes = new URLSearchParams();

  for (const clave of PARAMETROS) {
    const valor = entrantes.get(clave);
    if (valor !== null) {
      salientes.set(clave, valor);
    }
  }
  for (const cadena of entrantes.getAll("cadenas")) {
    salientes.append("cadenas", cadena);
  }

  const respuesta = await llamarApi(
    request,
    `/v1/comparar?${salientes.toString()}`,
  );
  const datos = await respuesta.json().catch(() => ({}));

  return NextResponse.json(datos, { status: respuesta.status });
}
