import { test, expect, type Page } from "@playwright/test";
import { generarCodigo, guardarUsuarios } from "./ayudantes";

const CONTRASENA = "Demo1234!";
const TIENDA_REGISTRO = "Lima Centro (Lima)";
const sufijo = Date.now();

const usuarios = {
  empleado: { email: `e2e-empleado-${sufijo}@test.pe`, nombre: "E2E Empleado", rol: "EMPLEADO", secreto: "" },
  gerente: { email: `e2e-gerente-${sufijo}@test.pe`, nombre: "E2E Gerente", rol: "GERENTE", secreto: "" },
  auditor: { email: `e2e-auditor-${sufijo}@test.pe`, nombre: "E2E Auditor", rol: "AUDITOR", secreto: "" },
};

async function registrar(page: Page, datos: { nombre: string; email: string }) {
  await page.goto("/registro");
  await page.getByLabel("Nombre completo").fill(datos.nombre);
  await page.getByLabel("Correo").fill(datos.email);
  await page.getByLabel("Contrasena").fill(CONTRASENA);
  await page.getByLabel("Tienda").selectOption({ label: TIENDA_REGISTRO });
  await page.getByRole("button", { name: "Registrarme" }).click();
  await expect(page.getByText("Registro exitoso")).toBeVisible();
}

/** Inicia sesion, lee la clave MFA en texto (enrolamiento) y verifica el codigo generado con otplib. */
async function enrolarYLoguear(page: Page, email: string, contrasena = CONTRASENA): Promise<string> {
  await page.goto("/login");
  await page.getByLabel("Correo").fill(email);
  await page.getByLabel("Contrasena").fill(contrasena);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await page.waitForURL("**/mfa");

  const claveTexto = page.locator(".clave-texto code");
  await expect(claveTexto).toBeVisible();
  const secreto = (await claveTexto.textContent())?.trim();
  if (!secreto) throw new Error("No se pudo leer la clave MFA en texto junto al QR");

  const codigo = await generarCodigo(secreto);
  await page.getByLabel("Codigo").fill(codigo);
  await page.getByRole("button", { name: "Verificar" }).click();
  await expect(page.getByRole("heading", { name: "Productos" })).toBeVisible();

  return secreto;
}

test("T4: registro deja pendiente, ADMIN activa, enrolamiento MFA con clave en texto y login", async ({ page }) => {
  await test.step("el registro deja al usuario pendiente de activacion", async () => {
    await registrar(page, usuarios.empleado);
    await expect(page.getByText(/pendiente de activacion/i)).toBeVisible();
  });

  await test.step("se registran tambien gerente y auditor (pendientes)", async () => {
    await registrar(page, usuarios.gerente);
    await registrar(page, usuarios.auditor);
  });

  await test.step("el ADMIN se enrola en MFA (primer ingreso) y activa a los tres con su rol", async () => {
    await enrolarYLoguear(page, "admin@techstore.pe");

    await page.goto("/administracion");
    for (const clave of ["empleado", "gerente", "auditor"] as const) {
      const datos = usuarios[clave];
      const fila = page.locator("tr", { hasText: datos.email });
      await expect(fila).toBeVisible();

      // El rol debe asignarse antes que el estado: activar sin rol es 422 en el backend.
      await fila.locator("select").nth(1).selectOption(datos.rol);
      await expect(page.getByText("Usuario actualizado.")).toBeVisible();
      await fila.locator("select").nth(0).selectOption("ACTIVO");
      await expect(page.getByText("Usuario actualizado.")).toBeVisible();
    }

    await page.getByRole("button", { name: "Cerrar sesion" }).click();
    await page.waitForURL("**/login");
  });

  await test.step("el empleado recien activado lee la clave MFA, genera el codigo con otplib y entra", async () => {
    usuarios.empleado.secreto = await enrolarYLoguear(page, usuarios.empleado.email);
    await page.getByRole("button", { name: "Cerrar sesion" }).click();
    await page.waitForURL("**/login");
  });

  await test.step("gerente y auditor tambien se enrolan (se reutilizan en las siguientes pruebas)", async () => {
    usuarios.gerente.secreto = await enrolarYLoguear(page, usuarios.gerente.email);
    await page.getByRole("button", { name: "Cerrar sesion" }).click();
    await page.waitForURL("**/login");

    usuarios.auditor.secreto = await enrolarYLoguear(page, usuarios.auditor.email);
    await page.getByRole("button", { name: "Cerrar sesion" }).click();
    await page.waitForURL("**/login");
  });

  guardarUsuarios({
    empleado: { email: usuarios.empleado.email, contrasena: CONTRASENA, secreto: usuarios.empleado.secreto, rol: "EMPLEADO" },
    gerente: { email: usuarios.gerente.email, contrasena: CONTRASENA, secreto: usuarios.gerente.secreto, rol: "GERENTE" },
    auditor: { email: usuarios.auditor.email, contrasena: CONTRASENA, secreto: usuarios.auditor.secreto, rol: "AUDITOR" },
  });
});
