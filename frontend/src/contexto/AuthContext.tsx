import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api, ErrorApiError } from "../api/cliente";
import type { Usuario } from "../tipos";

interface AuthContextValor {
  usuario: Usuario | null;
  cargando: boolean;
  refrescar: () => Promise<void>;
  cerrarSesion: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValor | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  const refrescar = useCallback(async () => {
    try {
      const actual = await api.get<Usuario>("/auth/me");
      setUsuario(actual);
    } catch (error) {
      if (error instanceof ErrorApiError && error.status === 401) {
        setUsuario(null);
      } else {
        throw error;
      }
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    refrescar();
  }, [refrescar]);

  const cerrarSesion = useCallback(async () => {
    await api.post("/auth/logout");
    setUsuario(null);
  }, []);

  return (
    <AuthContext.Provider value={{ usuario, cargando, refrescar, cerrarSesion }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValor {
  const contexto = useContext(AuthContext);
  if (!contexto) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }
  return contexto;
}
