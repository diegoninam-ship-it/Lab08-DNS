import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import text

_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
_RUTA_BACKEND = _RAIZ_REPOSITORIO / "backend"
_valores_env = dotenv_values(_RAIZ_REPOSITORIO / ".env")

_test_database_url = _valores_env.get("TEST_DATABASE_URL")
if not _test_database_url:
    raise RuntimeError("TEST_DATABASE_URL no esta definida en el .env de la raiz")

_nombre_bd = _test_database_url.rsplit("/", 1)[-1]
if not _nombre_bd.endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL debe apuntar a una base cuyo nombre termine en '_test'")

# Las pruebas usan unicamente la base de pruebas: se fija aqui, nunca en el entorno de la terminal.
os.environ["DATABASE_URL"] = _test_database_url

from app.config import obtener_configuracion  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app import modelos  # noqa: E402,F401
from app.main import create_app  # noqa: E402
from app.modelos import Tienda  # noqa: E402
from app.reloj import obtener_reloj  # noqa: E402

obtener_configuracion.cache_clear()


class RelojFalso:
    def __init__(self, ahora: datetime) -> None:
        self._ahora = ahora

    def ahora(self) -> datetime:
        return self._ahora

    def avanzar(self, **kwargs) -> None:
        self._ahora += timedelta(**kwargs)


@pytest.fixture(scope="session", autouse=True)
def _esquema_de_pruebas():
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_RUTA_BACKEND,
        check=True,
        env={**os.environ},
    )
    yield


@pytest.fixture(autouse=True)
def _base_de_datos_limpia(_esquema_de_pruebas):
    yield
    with engine.begin() as conexion:
        tablas = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conexion.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def db():
    from app.db import SesionLocal

    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture
def reloj_falso(app):
    # Base = hora real: el exp del JWT lo valida PyJWT con el reloj del sistema,
    # no con este reloj inyectable, asi que no puede arrancar en el pasado/futuro lejano.
    reloj = RelojFalso(datetime.now(timezone.utc))
    app.dependency_overrides[obtener_reloj] = lambda: reloj
    yield reloj
    app.dependency_overrides.pop(obtener_reloj, None)


@pytest.fixture
def cliente(app):
    return TestClient(app)


@pytest.fixture
def tienda(db):
    tienda = Tienda(nombre="Tienda de pruebas", ciudad="Lima")
    db.add(tienda)
    db.commit()
    db.refresh(tienda)
    return tienda
