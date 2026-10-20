import { FormularioPerfil } from "@/components/perfil/FormularioPerfil";
import { llamarApiServidor } from "@/lib/api";
import { t } from "@/lib/i18n";

type Perfil = {
  nombre: string | null;
  provincia: string | null;
};

async function cargarPerfil(): Promise<Perfil> {
  try {
    const respuesta = await llamarApiServidor("/v1/me");
    if (!respuesta.ok) {
      return { nombre: "", provincia: "" };
    }
    const datos = await respuesta.json();
    return {
      nombre: datos.nombre ?? "",
      provincia: datos.provincia ?? "",
    };
  } catch {
    return { nombre: "", provincia: "" };
  }
}

async function cargarProvincias(): Promise<string[]> {
  try {
    const respuesta = await llamarApiServidor("/v1/provincias");
    if (!respuesta.ok) {
      return [];
    }
    const datos = await respuesta.json();
    return Array.isArray(datos.provincias) ? datos.provincias : [];
  } catch {
    return [];
  }
}

export default async function PaginaPerfil() {
  const [perfil, provincias] = await Promise.all([
    cargarPerfil(),
    cargarProvincias(),
  ]);

  return (
    <section className="mx-auto max-w-lectura">
      <h1 className="text-2xl font-medium text-texto">{t("perfil.titulo")}</h1>
      <FormularioPerfil
        nombreInicial={perfil.nombre ?? ""}
        provinciaInicial={perfil.provincia ?? ""}
        provincias={provincias}
      />
    </section>
  );
}
