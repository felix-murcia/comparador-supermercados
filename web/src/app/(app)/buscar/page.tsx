import es from "@/locales/es.json";

export default function PaginaBuscar() {
  return (
    <section>
      <h1>{es.buscar.titulo}</h1>
      <form className="buscador" action="/buscar" method="get">
        <label className="oculto" htmlFor="q">
          {es.buscar.campo}
        </label>
        <input
          className="buscador__campo"
          id="q"
          name="q"
          type="search"
          placeholder={es.buscar.placeholder}
        />
        <button className="buscador__boton" type="submit">
          {es.buscar.boton}
        </button>
      </form>
    </section>
  );
}
