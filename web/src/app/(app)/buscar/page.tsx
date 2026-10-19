import { VistaBusqueda } from "@/components/buscador/VistaBusqueda";

type Props = {
  searchParams: {
    q?: string;
    cadenas?: string;
    job?: string;
    cache?: string;
  };
};

export default function PaginaBuscar({ searchParams }: Props) {
  const consulta = searchParams.q ?? "";
  const cadenas = (searchParams.cadenas ?? "").split(",").filter(Boolean);
  const job = searchParams.job ?? null;
  const cacheHit = searchParams.cache === "1";

  return (
    <VistaBusqueda
      consulta={consulta}
      cadenas={cadenas}
      job={job}
      cacheHit={cacheHit}
    />
  );
}
