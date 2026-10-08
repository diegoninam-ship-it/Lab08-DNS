import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import { api, ErrorApiError } from "../api/cliente";
import type { PasoLogin } from "../tipos";

const MENSAJES_ERROR_OAUTH: Record<string, string> = {
  no_registrado: "No existe una cuenta activa vinculada a ese correo.",
  pendiente: "La cuenta esta pendiente de activacion por un administrador.",
  desactivada: "La cuenta esta desactivada.",
  correo_no_verificado: "El proveedor no reporto el correo como verificado.",
  estado_invalido: "La sesion con el proveedor expiro o no es valida. Intenta de nuevo.",
  proveedor_no_configurado: "Ese proveedor de inicio de sesion no esta configurado.",
};

export function Login() {
  const [email, setEmail] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);
  const navegar = useNavigate();
  const [parametros] = useSearchParams();
  const location = useLocation();

  const errorOauth = parametros.get("error");
  const mensajeNavegacion =
    location.state && typeof location.state === "object" && "mensaje" in location.state
      ? String((location.state as { mensaje: string }).mensaje)
      : null;

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setCargando(true);
    try {
      const respuesta = await api.post<PasoLogin>("/auth/login", { email, contrasena });
      navegar("/mfa", { state: respuesta });
    } catch (err) {
      if (err instanceof ErrorApiError) {
        setError(err.detail);
      } else {
        setError("Ocurrio un error inesperado");
      }
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="pagina-centrada">
      <form className="tarjeta formulario" onSubmit={manejarEnvio}>
        <h1>Ingresar a TechStore</h1>

        {errorOauth && (
          <p className="alerta-error">
            {MENSAJES_ERROR_OAUTH[errorOauth] ?? "No se pudo completar el inicio de sesion social."}
          </p>
        )}
        {mensajeNavegacion && <p className="alerta-error">{mensajeNavegacion}</p>}
        {error && <p className="alerta-error">{error}</p>}

        <label>
          Correo
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
          />
        </label>

        <label>
          Contrasena
          <input
            type="password"
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>

        <button type="submit" disabled={cargando}>
          {cargando ? "Ingresando..." : "Ingresar"}
        </button>

        <div className="separador">o continua con</div>

        <div className="botones-sociales">
          <a className="boton-social" href="/api/auth/oauth/google/login">
            Google
          </a>
          <a className="boton-social" href="/api/auth/oauth/github/login">
            GitHub
          </a>
        </div>

        <p className="enlace-secundario">
          ¿No tienes cuenta? <Link to="/registro">Registrate</Link>
        </p>
      </form>
    </div>
  );
}
