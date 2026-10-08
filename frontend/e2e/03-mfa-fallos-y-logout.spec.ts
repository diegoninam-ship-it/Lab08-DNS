import { test, expect } from "@playwright/test";
import { generarCodigoFresco, leerUsuarios, type UsuarioE2E } from "./ayudantes";

let usuarios: Record<string, UsuarioE2E>;

test.beforeAll(() => {
  usuarios = leerUsuarios();
});

test("3 codigos MFA fallidos agotan el desafio y regresan al login", async ({ page }) => {
  const usuario = usuarios.empleado;

  await page.goto("/login");
  await page.getByLabel("Correo").fill(usuario.email);
  await page.getByLabel("Contrasena").fill(usuario.contrasena);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await page.waitForURL("**/mfa");

  for (let intento = 1; intento <= 3; intento++) {
    await page.getByLabel("Codigo").fill("000000");
    await page.getByRole("button", { name: "Verificar" }).click();
    if (intento < 3) {
      await expect(page.getByText(/intentos restantes/i)).toBeVisible();
    }
  }

  // Al agotarse el desafio (3er fallo) la aplicacion vuelve sola al login.
  await page.waitForURL("**/login");
  await expect(page.getByRole("heading", { name: "Ingresar a TechStore" })).toBeVisible();
  await expect(page.getByText(/desafio.*invalido|expirado/i)).toBeVisible();
});

test("login exitoso y logout limpia la sesion por completo", async ({ page }) => {
  const usuario = usuarios.empleado;

  await page.goto("/login");
  await page.getByLabel("Correo").fill(usuario.email);
  await page.getByLabel("Contrasena").fill(usuario.contrasena);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await page.waitForURL("**/mfa");

  const codigo = await generarCodigoFresco(usuario.secreto);
  await page.getByLabel("Codigo").fill(codigo);
  await page.getByRole("button", { name: "Verificar" }).click();
  await expect(page.getByRole("heading", { name: "Productos" })).toBeVisible();

  await page.getByRole("button", { name: "Cerrar sesion" }).click();
  await page.waitForURL("**/login");

  // Una sesion cerrada no debe poder volver a entrar sin loguearse de nuevo.
  await page.goto("/");
  await page.waitForURL("**/login");
});
