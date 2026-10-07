import type { ReactNode } from "react";
import { Navigate } from "react-router";
import { useAuth } from "../contexto/AuthContext";
import type { Rol } from "../tipos";

interface Props {
  children: ReactNode;
  rolesPermitidos?: Rol[];
}

export function RutaProtegida({ children, rolesPermitidos }: Props) {
  const { usuario, cargando } = useAuth();

  if (cargando) {
    return <p className="cargando">Cargando...</p>;
  }

  if (!usuario) {
    return <Navigate to="/login" replace />;
  }

  if (rolesPermitidos && (!usuario.rol || !rolesPermitidos.includes(usuario.rol))) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
