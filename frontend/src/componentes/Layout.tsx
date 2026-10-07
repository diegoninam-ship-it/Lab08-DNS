import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router";
import { useAuth } from "../contexto/AuthContext";

export function Layout({ children }: { children: ReactNode }) {
  const { usuario, cerrarSesion } = useAuth();
  const navegar = useNavigate();

  async function manejarLogout() {
    await cerrarSesion();
    navegar("/login");
  }

  return (
    <div className="app-layout">
      {usuario && (
        <header className="app-header">
          <nav className="app-nav">
            <span className="app-marca">TechStore</span>
            <Link to="/">Productos</Link>
            {usuario.rol !== "EMPLEADO" && <Link to="/reportes">Reportes</Link>}
            {(usuario.rol === "ADMIN" || usuario.rol === "AUDITOR") && (
              <Link to="/auditoria">Auditoria</Link>
            )}
            {usuario.rol === "ADMIN" && <Link to="/administracion">Administracion</Link>}
          </nav>
          <div className="app-usuario">
            <span>
              {usuario.nombre_completo} · {usuario.rol} · {usuario.tienda.nombre}
            </span>
            <button type="button" onClick={manejarLogout}>
              Cerrar sesion
            </button>
          </div>
        </header>
      )}
      <main className="app-contenido">{children}</main>
    </div>
  );
}
