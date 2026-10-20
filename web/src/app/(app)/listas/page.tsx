import { ListarListas } from "@/components/listas/ListarListas";
import { llamarApiServidor } from "@/lib/api";

type Lista = {
  id: string;
  nombre: string;
};

async function cargarListas(): Promise<Lista[]> {
  try {
    const respuesta = await llamarApiServidor("/v1/listas");
    if (!respuesta.ok) {
      return [];
    }
    const datos = await respuesta.json();
    return Array.isArray(datos) ? datos : [];
  } catch {
    return [];
  }
}

export default async function PaginaListas() {
  const listas = await cargarListas();

  return <ListarListas listas={listas} />;
}
