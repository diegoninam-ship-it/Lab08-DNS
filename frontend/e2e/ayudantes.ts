import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { generate } from "otplib";

const directorioActual = path.dirname(fileURLToPath(import.meta.url));
const RUTA_ESTADO = path.join(directorioActual, ".estado", "usuarios.json");

export interface UsuarioE2E {
  email: string;
  contrasena: string;
  secreto: string;
  rol: string;
}

export function guardarUsuarios(usuarios: Record<string, UsuarioE2E>): void {
  fs.mkdirSync(path.dirname(RUTA_ESTADO), { recursive: true });
  fs.writeFileSync(RUTA_ESTADO, JSON.stringify(usuarios, null, 2), "utf-8");
}

export function leerUsuarios(): Record<string, UsuarioE2E> {
  return JSON.parse(fs.readFileSync(RUTA_ESTADO, "utf-8"));
}

export async function generarCodigo(secreto: string): Promise<string> {
  return generate({ secret: secreto });
}

/**
 * El backend rechaza por anti-reutilizacion un codigo cuyo contador de
 * tiempo (ventana de 30s) ya fue usado antes para ese usuario. Como la
 * suite de E2E corre mucho mas rapido que 30s, reusar el secreto de un
 * usuario que ya inicio sesion antes en la misma corrida puede caer en la
 * misma ventana. Esta variante espera al inicio de una ventana TOTP nueva
 * antes de generar el codigo, para no depender de que haya pasado tiempo
 * real suficiente.
 */
export async function generarCodigoFresco(secreto: string, pasoSegundos = 30): Promise<string> {
  const ahora = Date.now();
  const msEnVentanaActual = ahora % (pasoSegundos * 1000);
  const msHastaSiguienteVentana = pasoSegundos * 1000 - msEnVentanaActual + 500;
  await new Promise((resolve) => setTimeout(resolve, msHastaSiguienteVentana));
  return generate({ secret: secreto });
}
