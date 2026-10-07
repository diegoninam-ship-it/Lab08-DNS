import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, ErrorApiError } from "../api/cliente";
import { useAuth } from "../contexto/AuthContext";
import type { ListadoProductos, Producto, Tienda } from "../tipos";

interface FormularioProducto {
  tienda_id: number | "";
  sku: string;
  nombre: string;
  descripcion: string;
  precio: string;
  stock: number;
}

const FORMULARIO_VACIO: FormularioProducto = {
  tienda_id: "",
  sku: "",
  nombre: "",
  descripcion: "",
  precio: "",
  stock: 0,
};

export function Productos() {
  const { usuario } = useAuth();
  const [tiendas, setTiendas] = useState<Tienda[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const tamano = 10;
  const [busqueda, setBusqueda] = useState("");
  const [tiendaFiltro, setTiendaFiltro] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);
  const [mostrarCreacion, setMostrarCreacion] = useState(false);
  const [formulario, setFormulario] = useState<FormularioProducto>(FORMULARIO_VACIO);
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [formularioEdicion, setFormularioEdicion] = useState<FormularioProducto>(FORMULARIO_VACIO);
  const [stockEnEdicion, setStockEnEdicion] = useState<Record<number, string>>({});

  if (!usuario) {
    return null;
  }

  const puedeCrear = usuario.rol === "ADMIN" || usuario.rol === "GERENTE";

  function puedeEditar(producto: Producto): boolean {
    return (
      usuario!.rol === "ADMIN" ||
      (usuario!.rol === "GERENTE" && producto.tienda.id === usuario!.tienda.id)
    );
  }

  function puedeActualizarStock(producto: Producto): boolean {
    return (
      usuario!.rol === "ADMIN" ||
      ((usuario!.rol === "GERENTE" || usuario!.rol === "EMPLEADO") &&
        producto.tienda.id === usuario!.tienda.id)
    );
  }

  useEffect(() => {
    api.get<Tienda[]>("/tiendas").then(setTiendas).catch(() => undefined);
  }, []);

  async function cargar() {
    setError(null);
    const parametros = new URLSearchParams();
    if (tiendaFiltro !== "") parametros.set("tienda_id", String(tiendaFiltro));
    if (busqueda) parametros.set("q", busqueda);
    parametros.set("pagina", String(pagina));
    parametros.set("tamano", String(tamano));
    try {
      const respuesta = await api.get<ListadoProductos>(`/productos?${parametros.toString()}`);
      setProductos(respuesta.items);
      setTotal(respuesta.total);
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo cargar el listado");
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pagina, tiendaFiltro]);

  function manejarBuscar(evento: FormEvent) {
    evento.preventDefault();
    setPagina(1);
    cargar();
  }

  async function manejarCrear(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      await api.post("/productos", {
        tienda_id: usuario!.rol === "GERENTE" ? usuario!.tienda.id : formulario.tienda_id,
        sku: formulario.sku,
        nombre: formulario.nombre,
        descripcion: formulario.descripcion || null,
        precio: formulario.precio,
        stock: formulario.stock,
      });
      setMostrarCreacion(false);
      setFormulario(FORMULARIO_VACIO);
      await cargar();
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo crear el producto");
    }
  }

  function iniciarEdicion(producto: Producto) {
    setEditandoId(producto.id);
    setFormularioEdicion({
      tienda_id: producto.tienda.id,
      sku: producto.sku,
      nombre: producto.nombre,
      descripcion: producto.descripcion ?? "",
      precio: producto.precio,
      stock: producto.stock,
    });
  }

  async function guardarEdicion(evento: FormEvent, id: number) {
    evento.preventDefault();
    setError(null);
    try {
      await api.put(`/productos/${id}`, {
        sku: formularioEdicion.sku,
        nombre: formularioEdicion.nombre,
        descripcion: formularioEdicion.descripcion || null,
        precio: formularioEdicion.precio,
      });
      setEditandoId(null);
      await cargar();
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo editar el producto");
    }
  }

  async function guardarStock(id: number) {
    setError(null);
    const valor = stockEnEdicion[id];
    if (valor === undefined) return;
    try {
      await api.patch(`/productos/${id}/stock`, { stock: Number(valor) });
      setStockEnEdicion((anterior) => {
        const { [id]: _omitido, ...resto } = anterior;
        return resto;
      });
      await cargar();
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo actualizar el stock");
    }
  }

  async function eliminar(id: number) {
    setError(null);
    try {
      await api.delete(`/productos/${id}`);
      await cargar();
    } catch (err) {
      setError(err instanceof ErrorApiError ? err.detail : "No se pudo eliminar el producto");
    }
  }

  const totalPaginas = Math.max(1, Math.ceil(total / tamano));

  return (
    <div>
      <h1>Productos</h1>
      {error && <p className="alerta-error">{error}</p>}

      <form className="barra-filtros" onSubmit={manejarBuscar}>
        <input
          type="text"
          placeholder="Buscar por nombre o SKU"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
        />
        <select
          value={tiendaFiltro}
          onChange={(e) => {
            setTiendaFiltro(e.target.value === "" ? "" : Number(e.target.value));
            setPagina(1);
          }}
        >
          <option value="">Todas las tiendas</option>
          {tiendas.map((t) => (
            <option key={t.id} value={t.id}>
              {t.nombre}
            </option>
          ))}
        </select>
        <button type="submit">Buscar</button>
        {puedeCrear && (
          <button type="button" onClick={() => setMostrarCreacion((v) => !v)}>
            {mostrarCreacion ? "Cancelar" : "+ Nuevo producto"}
          </button>
        )}
      </form>

      {mostrarCreacion && (
        <form className="tarjeta formulario-inline" onSubmit={manejarCrear}>
          <h2>Nuevo producto</h2>
          {usuario.rol === "ADMIN" && (
            <label>
              Tienda
              <select
                value={formulario.tienda_id}
                onChange={(e) => setFormulario({ ...formulario, tienda_id: Number(e.target.value) })}
                required
              >
                <option value="">Selecciona una tienda</option>
                {tiendas.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.nombre}
                  </option>
                ))}
              </select>
            </label>
          )}
          {usuario.rol === "GERENTE" && <p>Se creara en tu tienda: {usuario.tienda.nombre}</p>}
          <label>
            SKU
            <input
              value={formulario.sku}
              onChange={(e) => setFormulario({ ...formulario, sku: e.target.value })}
              required
            />
          </label>
          <label>
            Nombre
            <input
              value={formulario.nombre}
              onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
              required
            />
          </label>
          <label>
            Descripcion
            <input
              value={formulario.descripcion}
              onChange={(e) => setFormulario({ ...formulario, descripcion: e.target.value })}
            />
          </label>
          <label>
            Precio
            <input
              type="number"
              step="0.01"
              min="0"
              value={formulario.precio}
              onChange={(e) => setFormulario({ ...formulario, precio: e.target.value })}
              required
            />
          </label>
          <label>
            Stock
            <input
              type="number"
              min="0"
              value={formulario.stock}
              onChange={(e) => setFormulario({ ...formulario, stock: Number(e.target.value) })}
              required
            />
          </label>
          <button type="submit">Crear</button>
        </form>
      )}

      <table className="tabla">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Nombre</th>
            <th>Descripcion</th>
            <th>Precio</th>
            <th>Stock</th>
            <th>Tienda</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {productos.map((producto) =>
            editandoId === producto.id ? (
              <tr key={producto.id}>
                <td colSpan={7}>
                  <form className="formulario-inline" onSubmit={(e) => guardarEdicion(e, producto.id)}>
                    <input
                      value={formularioEdicion.sku}
                      onChange={(e) => setFormularioEdicion({ ...formularioEdicion, sku: e.target.value })}
                      required
                    />
                    <input
                      value={formularioEdicion.nombre}
                      onChange={(e) => setFormularioEdicion({ ...formularioEdicion, nombre: e.target.value })}
                      required
                    />
                    <input
                      value={formularioEdicion.descripcion}
                      onChange={(e) =>
                        setFormularioEdicion({ ...formularioEdicion, descripcion: e.target.value })
                      }
                    />
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formularioEdicion.precio}
                      onChange={(e) => setFormularioEdicion({ ...formularioEdicion, precio: e.target.value })}
                      required
                    />
                    <button type="submit">Guardar</button>
                    <button type="button" onClick={() => setEditandoId(null)}>
                      Cancelar
                    </button>
                  </form>
                </td>
              </tr>
            ) : (
              <tr key={producto.id}>
                <td>{producto.sku}</td>
                <td>{producto.nombre}</td>
                <td>{producto.descripcion}</td>
                <td>S/ {producto.precio}</td>
                <td>
                  {puedeActualizarStock(producto) ? (
                    <span className="editor-stock">
                      <input
                        type="number"
                        min="0"
                        value={stockEnEdicion[producto.id] ?? producto.stock}
                        onChange={(e) =>
                          setStockEnEdicion({ ...stockEnEdicion, [producto.id]: e.target.value })
                        }
                      />
                      <button type="button" onClick={() => guardarStock(producto.id)}>
                        Guardar
                      </button>
                    </span>
                  ) : (
                    producto.stock
                  )}
                </td>
                <td>{producto.tienda.nombre}</td>
                <td>
                  {puedeEditar(producto) && (
                    <>
                      <button type="button" onClick={() => iniciarEdicion(producto)}>
                        Editar
                      </button>
                      <button type="button" onClick={() => eliminar(producto.id)}>
                        Eliminar
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ),
          )}
          {productos.length === 0 && (
            <tr>
              <td colSpan={7}>No hay productos para mostrar.</td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="paginacion">
        <button type="button" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>
          Anterior
        </button>
        <span>
          Pagina {pagina} de {totalPaginas} ({total} productos)
        </span>
        <button
          type="button"
          disabled={pagina >= totalPaginas}
          onClick={() => setPagina((p) => p + 1)}
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
