# TESTING.md — TechStore

Estado de las pruebas al cierre de la etapa 3 (Testing), fase **T5**.
Ver [CONTEXT.md](../CONTEXT.md) para la especificación completa y el
detalle fase por fase (secciones 14 y 19).

## 1. Backend (pytest)

```bash
cd backend
pytest
```

- **226 pruebas, todas en verde** (0 fallos, 0 omitidas).
- **Cobertura total: 90.81 %** (umbral exigido: ≥ 90 %, impuesto por
  `--cov-fail-under=90` en `pytest.ini` desde el cierre de T5; antes
  se dejó sin exigir deliberadamente durante D2–D8 para no bloquear
  las fases intermedias mientras el código aún no estaba completo).
- Usan exclusivamente `TEST_DATABASE_URL` (una base cuyo nombre
  termina en `_test`) y aplican una migración real de Alembic, no
  `create_all`; se niegan a correr contra cualquier otra base.
- **Una única migración de Alembic**, verificada con `alembic check`
  que coincide exactamente con los modelos (sin operaciones
  pendientes).

### 1.1 Conteo por archivo

| Archivo | Casos | Fase que lo introdujo |
|---|---:|---|
| `tests/unit/test_cifrado.py` | 1 | D3 |
| `tests/unit/test_config.py` | 7 | D2 |
| `tests/unit/test_contrasenas.py` | 10 | D2/D3/T2 |
| `tests/unit/test_jwt.py` | 2 | D3 |
| `tests/unit/test_mfa.py` | 4 | D3 |
| `tests/integration/test_salud.py` | 1 | D2 |
| `tests/integration/test_tiendas.py` | 2 | D2 |
| `tests/integration/test_auth.py` | 22 | D3 |
| `tests/integration/test_oauth.py` | 12 | D4/T1/T3 |
| `tests/integration/test_productos.py` | 26 | D5 |
| `tests/integration/test_reportes.py` | 6 | D6 |
| `tests/integration/test_auditoria.py` | 6 | D6 |
| `tests/integration/test_usuarios_admin.py` | 9 | D6 |
| `tests/integration/test_tiendas_admin.py` | 5 | D6 |
| `tests/integration/test_t1_matriz_permisos.py` | 83 | T1 |
| `tests/integration/test_t2_seguridad.py` | 10 | T2 |
| `tests/integration/test_t3_auditoria_reportes.py` | 20 | T3 |
| **Total** | **226** | |

### 1.2 Cobertura por módulo (resumen)

100 % en modelos, esquemas, `db.py`, `reloj.py`, `seguridad/jwt.py`,
`seguridad/mfa.py`, `seguridad/cifrado.py`, `seguridad/contrasenas.py`,
`seguridad/csrf.py`, `servicios/auditoria.py`, `servicios/autorizacion.py`,
routers de `salud`/`tiendas`/`reportes`. El resto de routers y
`seguridad/sesion.py` están en 92–99 % (ramas defensivas de error que
no es practico forzar, p. ej. un desafío MFA sin secreto asociado).
`app/servicios/oauth_proveedores.py` está al 45–58 % porque las
pruebas simulan el proveedor por inyección de dependencias (sección
14.1: "ninguna prueba llama a Google o GitHub") — las líneas sin
cubrir son las llamadas HTTP reales a `GoogleOAuthProveedor` y
`GithubOAuthProveedor`, que solo se ejercitan con credenciales y
consentimiento reales (manual, fuera del alcance del agente).
`app/seed.py` está al 0 % en el reporte de cobertura porque se ejecuta
como script en `migrate`, no importado por las pruebas; se verifica
manualmente (ejecutándolo dos veces seguidas) en cada fase que lo usa.

## 2. End-to-end (Playwright)

```bash
cd frontend
npx playwright test
```

Requiere el stack completo de Compose arriba (`docker compose up -d
--build`, con `http://localhost:8080` disponible) y navegadores de
Playwright instalados (`npx playwright install chromium`).

- **6 pruebas, todas en verde**, corridas contra el stack completo
  (nginx + backend + PostgreSQL) con una **base de datos recién
  creada** (`docker compose down -v && docker compose up -d --build`).
- Los códigos TOTP se generan con `otplib` (API v13: `generate({secret})`),
  nunca con la librería `pyotp` del backend.

### 2.1 Casos cubiertos

| Archivo | Caso |
|---|---|
| `e2e/01-registro-activacion-mfa.spec.ts` | El registro deja al usuario `PENDIENTE` |
| | El ADMIN se enrola en MFA en su primer ingreso (lee la clave en texto junto al QR) |
| | El ADMIN activa a empleado, gerente y auditor asignándoles su rol |
| | El usuario recién activado se enrola en MFA (clave en texto + código generado con `otplib`) y entra |
| `e2e/02-restricciones-por-rol.spec.ts` | Empleado: sin opción de crear ni editar precio; sí actualiza el stock de su propia tienda |
| | Gerente: sin ninguna acción sobre productos de otra tienda; sí sobre los de la suya |
| | Auditor: sin ninguna acción de escritura en ningún lado, y sin acceso a Administración |
| `e2e/03-mfa-fallos-y-logout.spec.ts` | 3 códigos MFA fallidos agotan el desafío y la aplicación vuelve sola al login |
| | Login exitoso y logout limpia la sesión por completo (no se puede volver a `/` sin loguearse) |

## 3. Verificación manual del stack completo

Checklist ejecutado en el cierre de D8 y vuelto a confirmar en T5:

- [x] `docker compose up -d --build` limpio (sin contenedores ni
      volúmenes previos) levanta `db`, `migrate`, `backend` y
      `frontend` sin errores.
- [x] `migrate` aplica la migración y siembra los datos de forma
      idempotente (verificado corriendo el seed dos veces).
- [x] Login completo (contraseña + MFA con código TOTP real) a través
      de nginx en `http://localhost:8080`, verificado con `curl` y en
      el navegador.
- [x] `alembic check` confirma que la única migración coincide
      exactamente con los modelos.

## 4. Lo que queda fuera del alcance del agente

- Probar el login social real (Google/GitHub) con una cuenta real y
  consentimiento real del usuario — las credenciales ya están en el
  `.env` local del usuario; el agente solo verificó que el backend
  responde `302` (no `503`) con ellas, sin completar el consentimiento
  externo.
- La etapa 4 (infraestructura IAM en AWS) es responsabilidad del
  usuario (sección 16 de CONTEXT.md).
