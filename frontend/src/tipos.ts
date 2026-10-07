export type Rol = "ADMIN" | "GERENTE" | "EMPLEADO" | "AUDITOR";
export type Estado = "PENDIENTE" | "ACTIVO" | "DESACTIVADO";

export interface Tienda {
  id: number;
  nombre: string;
  ciudad: string;
}

export interface Usuario {
  id: number;
  email: string;
  nombre_completo: string;
  rol: Rol | null;
  tienda: Tienda;
}

export interface UsuarioAdmin {
  id: number;
  email: string;
  nombre_completo: string;
  rol: Rol | null;
  estado: Estado;
  tienda: Tienda;
  intentos_fallidos: number;
  bloqueado_hasta: string | null;
  mfa_activo: boolean;
  creado_en: string;
  actualizado_en: string;
}

export interface Producto {
  id: number;
  sku: string;
  nombre: string;
  descripcion: string | null;
  precio: string;
  stock: number;
  tienda: Tienda;
  actualizado_por: number | null;
  creado_en: string;
  actualizado_en: string;
}

export interface ListadoProductos {
  total: number;
  pagina: number;
  tamano: number;
  items: Producto[];
}

export interface ReporteInventarioTienda {
  tienda: Tienda;
  total_productos: number;
  total_unidades: number;
  valor_inventario: string;
  stock_bajo: Producto[];
}

export interface RegistroAuditoria {
  id: number;
  usuario_id: number | null;
  email_intentado: string | null;
  accion: string;
  recurso: string | null;
  recurso_id: string | null;
  detalle: Record<string, unknown> | null;
  ip: string | null;
  creado_en: string;
}

export interface ListadoAuditoria {
  total: number;
  pagina: number;
  tamano: number;
  items: RegistroAuditoria[];
}

export type PasoLogin =
  | { paso: "MFA_REQUERIDO"; desafio_token: string }
  | { paso: "MFA_ENROLAMIENTO"; desafio_token: string; otpauth_uri: string };

export type PasoMfaIniciar =
  | { paso: "MFA_REQUERIDO" }
  | { paso: "MFA_ENROLAMIENTO"; otpauth_uri: string };

export interface ErrorApi {
  detail: string;
  intentos_restantes?: number;
}
