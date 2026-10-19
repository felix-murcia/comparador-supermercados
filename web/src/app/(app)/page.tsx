import Link from "next/link";

import es from "@/locales/es.json";

export default function PaginaInicio() {
  return (
    <section className="inicio">
      <h1 className="inicio__titulo">{es.inicio.titulo}</h1>
      <p className="inicio__subtitulo">{es.inicio.subtitulo}</p>
      <Link className="inicio__enlace" href="/buscar">
        {es.inicio.ir_a_buscar}
      </Link>
    </section>
  );
}
