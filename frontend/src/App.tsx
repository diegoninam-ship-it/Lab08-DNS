import { BrowserRouter, Route, Routes } from "react-router";
import { AuthProvider } from "./contexto/AuthContext";
import { Layout } from "./componentes/Layout";
import { RutaProtegida } from "./componentes/RutaProtegida";
import { Login } from "./paginas/Login";
import { Registro } from "./paginas/Registro";
import { Mfa } from "./paginas/Mfa";
import { Productos } from "./paginas/Productos";
import { Reportes } from "./paginas/Reportes";
import { Auditoria } from "./paginas/Auditoria";
import { Administracion } from "./paginas/Administracion";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Layout>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/registro" element={<Registro />} />
            <Route path="/mfa" element={<Mfa />} />
            <Route
              path="/"
              element={
                <RutaProtegida>
                  <Productos />
                </RutaProtegida>
              }
            />
            <Route
              path="/reportes"
              element={
                <RutaProtegida rolesPermitidos={["ADMIN", "GERENTE", "AUDITOR"]}>
                  <Reportes />
                </RutaProtegida>
              }
            />
            <Route
              path="/auditoria"
              element={
                <RutaProtegida rolesPermitidos={["ADMIN", "AUDITOR"]}>
                  <Auditoria />
                </RutaProtegida>
              }
            />
            <Route
              path="/administracion"
              element={
                <RutaProtegida rolesPermitidos={["ADMIN"]}>
                  <Administracion />
                </RutaProtegida>
              }
            />
          </Routes>
        </Layout>
      </AuthProvider>
    </BrowserRouter>
  );
}
