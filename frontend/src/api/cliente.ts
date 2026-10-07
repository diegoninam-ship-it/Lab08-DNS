export class ErrorApiError extends Error {
  status: number;
  detail: string;
  intentos_restantes?: number;

  constructor(status: number, detail: string, intentos_restantes?: number) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.intentos_restantes = intentos_restantes;
  }
}

async function peticion<T>(
  ruta: string,
  opciones: RequestInit = {},
): Promise<T> {
  const metodo = (opciones.method ?? "GET").toUpperCase();
  const encabezados: Record<string, string> = {
    ...(opciones.headers as Record<string, string> | undefined),
  };

  if (metodo !== "GET" && metodo !== "HEAD") {
    encabezados["Content-Type"] = "application/json";
  }

  const respuesta = await fetch(`/api${ruta}`, {
    ...opciones,
    method: metodo,
    headers: encabezados,
    credentials: "include",
  });

  if (respuesta.status === 204) {
    return undefined as T;
  }

  const esJson = respuesta.headers.get("content-type")?.includes("application/json");
  const cuerpo = esJson ? await respuesta.json() : undefined;

  if (!respuesta.ok) {
    const detalle =
      typeof cuerpo?.detail === "string" ? cuerpo.detail : "Ocurrio un error inesperado";
    throw new ErrorApiError(respuesta.status, detalle, cuerpo?.intentos_restantes);
  }

  return cuerpo as T;
}

export const api = {
  get: <T>(ruta: string) => peticion<T>(ruta),
  post: <T>(ruta: string, cuerpo?: unknown) =>
    peticion<T>(ruta, { method: "POST", body: cuerpo !== undefined ? JSON.stringify(cuerpo) : "{}" }),
  put: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "PUT", body: JSON.stringify(cuerpo) }),
  patch: <T>(ruta: string, cuerpo: unknown) =>
    peticion<T>(ruta, { method: "PATCH", body: JSON.stringify(cuerpo) }),
  delete: <T>(ruta: string) => peticion<T>(ruta, { method: "DELETE", body: "{}" }),
};
