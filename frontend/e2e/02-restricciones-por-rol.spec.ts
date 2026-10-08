import { test, expect, type Page } from "@playwright/test";
import { generarCodigoFresco, leerUsuarios, type UsuarioE2E } from "./ayudantes";

let usuarios: Record<string, UsuarioE2E>;

test.beforeAll(() => {
  usuarios = leerUsuarios();
});

async function loguearConSecretoConocido(page: Page, usuario: UsuarioE2E) {
  await page.goto("/login");
  await page.getByLabel("Correo").fill(usuario.email);
  await page.getByLabel("Contrasena").fill(usuario.contrasena);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await page.waitForURL("**/mfa");

  const codigo = await generarCodigoFresco(usuario.secreto);
  await page.getByLabel("Codigo").fill(codigo);
  await page.getByRole("button", { name: "Verificar" }).click();
  await expect(page.getByRole("heading", { name: "Productos" })).toBeVisible();
}

test("Empleado no tiene opcion de crear ni editar precio, pero si actualiza su propio stock", async ({ page }) => {
  await loguearConSecretoConocido(page, usuarios.empleado);

  await expect(page.getByRole("button", { name: "+ Nuevo producto" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Editar" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Eliminar" })).toHaveCount(0);
  await expect(page.locator(".editor-stock").first()).toBeVisible();
});

test("Gerente no tiene ninguna accion sobre productos de otra tienda", async ({ page }) => {
  await loguearConSecretoConocido(page, usuarios.gerente);
  const selectorTienda = page.getByRole("combobox");

  await selectorTienda.selectOption({ label: "Arequipa Mall" });
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.locator("tbody tr").first()).toBeVisible();

  await expect(page.getByRole("button", { name: "Editar" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Eliminar" })).toHaveCount(0);
  await expect(page.locator(".editor-stock")).toHaveCount(0);

  // En su propia tienda si debe poder editar/eliminar.
  await selectorTienda.selectOption({ label: "Lima Centro" });
  await page.getByRole("button", { name: "Buscar" }).click();
  await expect(page.getByRole("button", { name: "Editar" }).first()).toBeVisible();
});

test("Auditor no tiene ninguna accion de escritura en ningun lado", async ({ page }) => {
  await loguearConSecretoConocido(page, usuarios.auditor);

  await expect(page.getByRole("button", { name: "+ Nuevo producto" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Editar" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Eliminar" })).toHaveCount(0);
  await expect(page.locator(".editor-stock")).toHaveCount(0);

  // Puede ver reportes y auditoria, pero no administracion (solo ADMIN).
  await expect(page.getByRole("link", { name: "Reportes" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Auditoria" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Administracion" })).toHaveCount(0);

  await page.goto("/administracion");
  await expect(page).toHaveURL(/\/$/);
});
