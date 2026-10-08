# TechStore

Gestión de inventario para una cadena de tiendas de tecnología, con
autenticación por contraseña y social, MFA obligatorio (TOTP), 4 roles
con control de acceso por tienda, auditoría y reportes.

Proyecto del laboratorio **GLAB-S08** (Tecsup, semana 8: IAM y MFA). La
especificación completa está en [CONTEXT.md](CONTEXT.md).

## Stack

- **Backend**: FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL, JWT en
  cookie `HttpOnly`, MFA TOTP (`pyotp`), login social Google/GitHub.
- **Frontend**: React 19 + TypeScript + Vite + react-router.
- **Infraestructura**: Docker Compose (PostgreSQL, backend, frontend
  servido con nginx).

## Prerrequisitos

- Python 3.14, Node 24, Docker Desktop (con Compose v2).
- Un archivo `.env` en la raíz (copiar `.env.example` y completar los
  secretos). **Nunca se versiona.**

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"                              # JWT_SECRET y POSTGRES_PASSWORD
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # MFA_CLAVE_CIFRADO
```

Las credenciales de Google/GitHub (`GOOGLE_CLIENT_ID`, etc.) son
opcionales: si faltan, el login social responde `503` pero el resto de
la aplicación funciona con normalidad.

## Modos de trabajo

**Nunca** correr Vite en el puerto 8080 y el stack completo de Compose
al mismo tiempo (ambos usan ese puerto).

### Desarrollo (recarga en caliente)

```bash
docker compose up -d db
```

Backend (en `backend/`, con el entorno virtual activado):

```bash
python -m venv venv
venv\Scripts\activate          # PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Frontend (en `frontend/`, en otra terminal):

```bash
npm install
npm run dev
```

La app queda disponible en **http://localhost:8080** (Vite sirve el
frontend y hace proxy de `/api` hacia `http://localhost:8000`).

### Stack completo (demo / E2E / verificación de Docker)

```bash
docker compose up -d --build
```

Levanta `db`, `migrate` (aplica las migraciones y siembra los datos,
tarea única) y luego `backend` y `frontend`. La app queda en
**http://localhost:8080**, servida por nginx (`/` → SPA compilada,
`/api/` → backend, sin recortar el prefijo).

### Pruebas del backend

```bash
cd backend
pytest
```

Usan exclusivamente `TEST_DATABASE_URL` (una base cuyo nombre termina
en `_test`; se niegan a correr contra cualquier otra) y aplican una
migración real de Alembic, no `create_all`.

## Datos semilla

3 tiendas, 7 usuarios (contraseña `Demo1234!`, ninguno con MFA
configurado) y 12 productos. Ver la sección 13 de
[CONTEXT.md](CONTEXT.md) para el detalle completo, incluidos los
correos de cada rol.

## Estructura

Ver la sección 6 de [CONTEXT.md](CONTEXT.md).

## Estado del proyecto

El progreso por fase, las decisiones de diseño y el changelog se
documentan en [CONTEXT.md](CONTEXT.md) (secciones 3, 17–19). La
etapa 4 (infraestructura IAM en AWS) es responsabilidad del usuario y
queda fuera del alcance de este repositorio como código.
