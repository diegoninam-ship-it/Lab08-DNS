import { useEffect, useState } from "react";
import { api, ErrorApiError } from "../api/cliente";
import { useAuth } from "../contexto/AuthContext";
import type { ReporteInventarioTienda, Tienda } from "../tipos";

export function Reportes() {
  const { usuario } = useAuth();
  const [tiendas, setTiendas] = useState<Tienda[]>([]);
  const [tiendaFiltro, setTiendaFiltro] = useState<number | "">("");
  const [reporte, setReporte] = useState<ReporteInventarioTienda[]>([]);
  const [error, setError] = useState<string | null>(null);

  const puedeElegirTienda = usuario?.rol === "ADMIN" || usuario?.rol === "AUDITOR";

  useEffect(() => {
    if (puedeElegirTienda) {
      api.get<Tienda[]>("/tiendas").then(setTiendas).catch(() => undefined);
    }
  }, [puedeElegirTienda]);

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tiendaFiltro]);

  async function cargar() {
    setError(null);
    const parametros = new URLSearchParams();
    if (tiendaFiltro !== "") parametros.set("tienda_id", String(tiendaFiltro));
    try {
      const respuesta = await api.get<ReporteInventarioTienda[]>(
        `/reportes/inventario?${parametros.toString()}`,
      );
      setReporte(respuesta);
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo cargar el reporte");
    }
  }

  return (
    <div>
      <h1>Reporte de inventario</h1>
      {error && <p className="alerta-error">{error}</p>}

      {puedeElegirTienda && (
        <select
          value={tiendaFiltro}
          onChange={(e) => setTiendaFiltro(e.target.value === "" ? "" : Number(e.target.value))}
        >
          <option value="">Todas las tiendas</option>
          {tiendas.map((t) => (
            <option key={t.id} value={t.id}>
              {t.nombre}
            </option>
          ))}
        </select>
      )}

      {reporte.map((bloque) => (
        <div key={bloque.tienda.id} className="tarjeta bloque-reporte">
          <h2>
            {bloque.tienda.nombre} ({bloque.tienda.ciudad})
          </h2>
          <p>Total de productos: {bloque.total_productos}</p>
          <p>Total de unidades: {bloque.total_unidades}</p>
          <p>Valor del inventario: S/ {bloque.valor_inventario}</p>

          {bloque.stock_bajo.length > 0 && (
            <>
              <h3>Stock bajo</h3>
              <table className="tabla">
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Nombre</th>
                    <th>Stock</th>
                  </tr>
                </thead>
                <tbody>
                  {bloque.stock_bajo.map((producto) => (
                    <tr key={producto.id}>
                      <td>{producto.sku}</td>
                      <td>{producto.nombre}</td>
                      <td>{producto.stock}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      ))}

      {reporte.length === 0 && !error && <p>No hay datos para mostrar.</p>}
    </div>
  );
}
