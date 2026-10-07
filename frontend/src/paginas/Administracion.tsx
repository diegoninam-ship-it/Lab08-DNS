import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, ErrorApiError } from "../api/cliente";
import { useAuth } from "../contexto/AuthContext";
import type { Estado, Rol, Tienda, UsuarioAdmin } from "../tipos";

const ROLES: Rol[] = ["ADMIN", "GERENTE", "EMPLEADO", "AUDITOR"];
const ESTADOS: Estado[] = ["PENDIENTE", "ACTIVO", "DESACTIVADO"];

export function Administracion() {
  const { usuario } = useAuth();
  const [usuarios, setUsuarios] = useState<UsuarioAdmin[]>([]);
  const [filtroEstado, setFiltroEstado] = useState<Estado | "">("");
  const [tiendas, setTiendas] = useState<Tienda[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);

  const [nombreTienda, setNombreTienda] = useState("");
  const [ciudadTienda, setCiudadTienda] = useState("");

  async function cargarUsuarios() {
    setError(null);
    const parametros = new URLSearchParams();
    if (filtroEstado) parametros.set("estado", filtroEstado);
    try {
      const lista = await api.get<UsuarioAdmin[]>(`/usuarios?${parametros.toString()}`);
      setUsuarios(lista);
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo cargar los usuarios");
    }
  }

  async function cargarTiendas() {
    try {
      setTiendas(await api.get<Tienda[]>("/tiendas"));
    } catch {
      /* ignorado: la tabla de tiendas es secundaria en esta pantalla */
    }
  }

  useEffect(() => {
    cargarUsuarios();
    cargarTiendas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtroEstado]);

  async function actualizarUsuario(id: number, cambios: Partial<{ estado: Estado; rol: Rol; tienda_id: number }>) {
    setError(null);
    setMensaje(null);
    try {
      await api.patch(`/usuarios/${id}`, cambios);
      setMensaje("Usuario actualizado.");
      await cargarUsuarios();
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo actualizar el usuario");
    }
  }

  async function desbloquear(id: number) {
    setError(null);
    setMensaje(null);
    try {
      await api.post(`/usuarios/${id}/desbloquear`);
      setMensaje("Usuario desbloqueado.");
      await cargarUsuarios();
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo desbloquear al usuario");
    }
  }

  async function restablecerMfa(id: number) {
    setError(null);
    setMensaje(null);
    try {
      await api.post(`/usuarios/${id}/mfa/restablecer`);
      setMensaje("MFA restablecido.");
      await cargarUsuarios();
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo restablecer el MFA");
    }
  }

  async function crearTienda(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setMensaje(null);
    try {
      await api.post("/tiendas", { nombre: nombreTienda, ciudad: ciudadTienda });
      setNombreTienda("");
      setCiudadTienda("");
      setMensaje("Tienda creada.");
      await cargarTiendas();
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo crear la tienda");
    }
  }

  return (
    <div>
      <h1>Administracion</h1>
      {error && <p className="alerta-error">{error}</p>}
      {mensaje && <p className="alerta-exito">{mensaje}</p>}

      <section>
        <h2>Usuarios</h2>
        <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value as Estado | "")}>
          <option value="">Todos los estados</option>
          {ESTADOS.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>

        <table className="tabla">
          <thead>
            <tr>
              <th>Correo</th>
              <th>Nombre</th>
              <th>Estado</th>
              <th>Rol</th>
              <th>Tienda</th>
              <th>Bloqueado</th>
              <th>MFA</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td>{u.nombre_completo}</td>
                <td>
                  <select
                    value={u.estado}
                    disabled={u.id === usuario?.id}
                    onChange={(e) => actualizarUsuario(u.id, { estado: e.target.value as Estado })}
                  >
                    {ESTADOS.map((e) => (
                      <option key={e} value={e}>
                        {e}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <select
                    value={u.rol ?? ""}
                    disabled={u.id === usuario?.id}
                    onChange={(e) => actualizarUsuario(u.id, { rol: e.target.value as Rol })}
                  >
                    <option value="" disabled>
                      Sin rol
                    </option>
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <select
                    value={u.tienda.id}
                    disabled={u.id === usuario?.id}
                    onChange={(e) => actualizarUsuario(u.id, { tienda_id: Number(e.target.value) })}
                  >
                    {tiendas.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.nombre}
                      </option>
                    ))}
                  </select>
                </td>
                <td>{u.bloqueado_hasta ? new Date(u.bloqueado_hasta).toLocaleString() : "-"}</td>
                <td>{u.mfa_activo ? "Activo" : "Sin activar"}</td>
                <td>
                  <button type="button" disabled={u.id === usuario?.id} onClick={() => desbloquear(u.id)}>
                    Desbloquear
                  </button>
                  <button type="button" disabled={u.id === usuario?.id} onClick={() => restablecerMfa(u.id)}>
                    Restablecer MFA
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>Tiendas</h2>
        <ul>
          {tiendas.map((t) => (
            <li key={t.id}>
              {t.nombre} ({t.ciudad})
            </li>
          ))}
        </ul>

        <form className="formulario-inline" onSubmit={crearTienda}>
          <input placeholder="Nombre" value={nombreTienda} onChange={(e) => setNombreTienda(e.target.value)} required />
          <input placeholder="Ciudad" value={ciudadTienda} onChange={(e) => setCiudadTienda(e.target.value)} required />
          <button type="submit">Crear tienda</button>
        </form>
      </section>
    </div>
  );
}
