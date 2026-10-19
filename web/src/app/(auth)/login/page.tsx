import { FormularioLogin } from "@/components/FormularioLogin";
import es from "@/locales/es.json";

type Props = {
  searchParams: { callbackUrl?: string | string[] };
};

export default function PaginaLogin({ searchParams }: Props) {
  const destino =
    typeof searchParams.callbackUrl === "string" ? searchParams.callbackUrl : "/";

  return (
    <main className="login">
      <div className="login__tarjeta">
        <h1 className="login__titulo">{es.login.titulo}</h1>
        <p className="login__subtitulo">{es.login.subtitulo}</p>
        <FormularioLogin destino={destino} />
        <p className="login__legal">{es.login.legal}</p>
      </div>
    </main>
  );
}
