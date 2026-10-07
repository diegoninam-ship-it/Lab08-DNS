import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router";
import { api, ErrorApiError } from "../api/cliente";
import type { Tienda } from "../tipos";

export function Registro() {
  const [tiendas, setTiendas] = useState<Tienda[]>([]);
  const [email, setEmail] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [nombreCompleto, setNombreCompleto] = useState("");
  const [tiendaId, setTiendaId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState(false);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    api
      .get<Tienda[]>("/tiendas")
      .then((lista) => {
        setTiendas(lista);
        if (lista.length > 0) {
          setTiendaId(lista[0].id);
        }
      })
      .catch(() => setError("No se pudieron cargar las tiendas"));
  }, []);

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setCargando(true);
    try {
      await api.post("/auth/registro", {
        email,
        contrasena,
        nombre_completo: nombreCompleto,
        tienda_id: tiendaId,
      });
      setExito(true);
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

  if (exito) {
    return (
      <div className="pagina-centrada">
        <div className="tarjeta">
          <h1>Registro exitoso</h1>
          <p>Tu cuenta quedo pendiente de activacion por un administrador.</p>
          <Link to="/login">Volver a ingresar</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="pagina-centrada">
      <form className="tarjeta formulario" onSubmit={manejarEnvio}>
        <h1>Crear cuenta</h1>

        {error && <p className="alerta-error">{error}</p>}

        <label>
          Nombre completo
          <input
            type="text"
            value={nombreCompleto}
            onChange={(e) => setNombreCompleto(e.target.value)}
            required
          />
        </label>

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
            autoComplete="new-password"
          />
          <small>8+ caracteres, mayuscula, numero y caracter especial.</small>
        </label>

        <label>
          Tienda
          <select
            value={tiendaId}
            onChange={(e) => setTiendaId(Number(e.target.value))}
            required
          >
            {tiendas.map((tienda) => (
              <option key={tienda.id} value={tienda.id}>
                {tienda.nombre} ({tienda.ciudad})
              </option>
            ))}
          </select>
        </label>

        <button type="submit" disabled={cargando}>
          {cargando ? "Registrando..." : "Registrarme"}
        </button>

        <p className="enlace-secundario">
          ¿Ya tienes cuenta? <Link to="/login">Ingresa</Link>
        </p>
      </form>
    </div>
  );
}
