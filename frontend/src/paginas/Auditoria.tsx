import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, ErrorApiError } from "../api/cliente";
import type { ListadoAuditoria } from "../tipos";

export function Auditoria() {
  const [accion, setAccion] = useState("");
  const [usuarioId, setUsuarioId] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [pagina, setPagina] = useState(1);
  const tamano = 20;
  const [listado, setListado] = useState<ListadoAuditoria | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function cargar() {
    setError(null);
    const parametros = new URLSearchParams();
    if (accion) parametros.set("accion", accion);
    if (usuarioId) parametros.set("usuario_id", usuarioId);
    if (desde) parametros.set("desde", new Date(desde).toISOString());
    if (hasta) parametros.set("hasta", new Date(hasta).toISOString());
    parametros.set("pagina", String(pagina));
    parametros.set("tamano", String(tamano));
    try {
      const respuesta = await api.get<ListadoAuditoria>(`/auditoria?${parametros.toString()}`);
      setListado(respuesta);
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo cargar la auditoria");
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pagina]);

  function manejarFiltrar(evento: FormEvent) {
    evento.preventDefault();
    setPagina(1);
    cargar();
  }

  const totalPaginas = Math.max(1, Math.ceil((listado?.total ?? 0) / tamano));

  return (
    <div>
      <h1>Bitacora de auditoria</h1>
      {error && <p className="alerta-error">{error}</p>}

      <form className="barra-filtros" onSubmit={manejarFiltrar}>
        <input placeholder="Accion (ej. LOGIN_OK)" value={accion} onChange={(e) => setAccion(e.target.value)} />
        <input placeholder="ID de usuario" value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)} />
        <input type="datetime-local" value={desde} onChange={(e) => setDesde(e.target.value)} />
        <input type="datetime-local" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        <button type="submit">Filtrar</button>
      </form>

      <table className="tabla">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Accion</th>
            <th>Usuario</th>
            <th>Correo intentado</th>
            <th>Recurso</th>
            <th>IP</th>
            <th>Detalle</th>
          </tr>
        </thead>
        <tbody>
          {listado?.items.map((registro) => (
            <tr key={registro.id}>
              <td>{new Date(registro.creado_en).toLocaleString()}</td>
              <td>{registro.accion}</td>
              <td>{registro.usuario_id ?? "-"}</td>
              <td>{registro.email_intentado ?? "-"}</td>
              <td>
                {registro.recurso ?? "-"} {registro.recurso_id ?? ""}
              </td>
              <td>{registro.ip ?? "-"}</td>
              <td>{registro.detalle ? JSON.stringify(registro.detalle) : "-"}</td>
            </tr>
          ))}
          {listado && listado.items.length === 0 && (
            <tr>
              <td colSpan={7}>No hay registros para mostrar.</td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="paginacion">
        <button type="button" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>
          Anterior
        </button>
        <span>
          Pagina {pagina} de {totalPaginas} ({listado?.total ?? 0} registros)
        </span>
        <button type="button" disabled={pagina >= totalPaginas} onClick={() => setPagina((p) => p + 1)}>
          Siguiente
        </button>
      </div>
    </div>
  );
}
