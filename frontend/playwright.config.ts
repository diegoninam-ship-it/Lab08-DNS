import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // Algunas pruebas esperan deliberadamente a una ventana TOTP nueva (hasta 30s)
  // para evitar colisiones de anti-reutilizacion al reusar un secreto ya usado.
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:8080",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
