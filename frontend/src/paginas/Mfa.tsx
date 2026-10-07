import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { QRCodeSVG } from "qrcode.react";
import { useLocation, useNavigate } from "react-router";
import { api, ErrorApiError } from "../api/cliente";
import { useAuth } from "../contexto/AuthContext";
import type { PasoMfaIniciar, Usuario } from "../tipos";

function extraerDesafioToken(estadoNavegacion: unknown, hash: string): string | null {
  if (
    estadoNavegacion &&
    typeof estadoNavegacion === "object" &&
    "desafio_token" in estadoNavegacion
  ) {
    return String((estadoNavegacion as { desafio_token: string }).desafio_token);
  }
  const coincidencia = hash.match(/desafio=([^&]+)/);
  return coincidencia ? decodeURIComponent(coincidencia[1]) : null;
}

function extraerSecreto(otpauthUri: string): string | null {
  try {
    const url = new URL(otpauthUri);
    return url.searchParams.get("secret");
  } catch {
    return null;
  }
}

export function Mfa() {
  const location = useLocation();
  const navegar = useNavigate();
  const { refrescar } = useAuth();

  const [desafioToken] = useState<string | null>(() =>
    extraerDesafioToken(location.state, window.location.hash),
  );
  const [otpauthUri, setOtpauthUri] = useState<string | null>(
    location.state && typeof location.state === "object" && "otpauth_uri" in location.state
      ? String((location.state as { otpauth_uri: string }).otpauth_uri)
      : null,
  );
  const [cargandoEstado, setCargandoEstado] = useState(otpauthUri === null);
  const [codigo, setCodigo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (!desafioToken) {
      return;
    }
    // Limpia el fragmento con el token para que nunca quede en el historial del navegador.
    if (window.location.hash) {
      window.history.replaceState(null, "", window.location.pathname);
    }
    if (otpauthUri !== null) {
      return;
    }
    api
      .post<PasoMfaIniciar>("/auth/mfa/iniciar", { desafio_token: desafioToken })
      .then((respuesta) => {
        if (respuesta.paso === "MFA_ENROLAMIENTO") {
          setOtpauthUri(respuesta.otpauth_uri);
        }
      })
      .catch(() => setError("El desafio de inicio de sesion ya no es valido. Vuelve a ingresar."))
      .finally(() => setCargandoEstado(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desafioToken]);

  if (!desafioToken) {
    return (
      <div className="pagina-centrada">
        <div className="tarjeta">
          <p className="alerta-error">No hay un inicio de sesion en curso.</p>
          <button type="button" onClick={() => navegar("/login")}>
            Volver a ingresar
          </button>
        </div>
      </div>
    );
  }

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setCargando(true);
    try {
      const respuesta = await api.post<{ usuario: Usuario }>("/auth/mfa/verificar", {
        desafio_token: desafioToken,
        codigo,
      });
      void respuesta;
      await refrescar();
      navegar("/");
    } catch (err) {
      if (err instanceof ErrorApiError) {
        if (err.intentos_restantes !== undefined) {
          setError(`${err.detail}. Intentos restantes: ${err.intentos_restantes}`);
        } else {
          setError(err.detail);
        }
      } else {
        setError("Ocurrio un error inesperado");
      }
    } finally {
      setCargando(false);
    }
  }

  const secreto = otpauthUri ? extraerSecreto(otpauthUri) : null;

  return (
    <div className="pagina-centrada">
      <form className="tarjeta formulario" onSubmit={manejarEnvio}>
        <h1>Verificacion en dos pasos</h1>

        {cargandoEstado && <p>Cargando...</p>}

        {!cargandoEstado && otpauthUri && (
          <div className="bloque-enrolamiento">
            <p>Escanea este codigo con tu aplicacion de autenticacion (Google Authenticator, Authy, etc.):</p>
            <QRCodeSVG value={otpauthUri} size={200} />
            {secreto && (
              <p className="clave-texto">
                O ingresa la clave manualmente: <code>{secreto}</code>
              </p>
            )}
          </div>
        )}

        {!cargandoEstado && !otpauthUri && <p>Ingresa el codigo de 6 digitos de tu aplicacion.</p>}

        {error && <p className="alerta-error">{error}</p>}

        <label>
          Codigo
          <input
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            required
            autoFocus
          />
        </label>

        <button type="submit" disabled={cargando}>
          {cargando ? "Verificando..." : "Verificar"}
        </button>
      </form>
    </div>
  );
}
