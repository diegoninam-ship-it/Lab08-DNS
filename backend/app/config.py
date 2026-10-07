from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
_RUTA_ENV = _RAIZ_REPOSITORIO / ".env"


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file=_RUTA_ENV, env_file_encoding="utf-8", extra="ignore")

    database_url: str
    test_database_url: str | None = None

    jwt_secret: str
    jwt_expira_minutos: int = 30

    mfa_clave_cifrado: str
    mfa_emisor: str = "TechStore"

    login_max_intentos: int = 5
    bloqueo_minutos: int = 15

    mfa_max_intentos: int = 3
    desafio_minutos: int = 5

    google_client_id: str | None = None
    google_client_secret: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = None

    url_publica: str = "http://localhost:8080"
    cookie_secure: bool = False
    stock_bajo_umbral: int = 5

    @field_validator("database_url")
    @classmethod
    def _validar_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL debe usar el driver postgresql+psycopg://")
        return v

    @field_validator("test_database_url")
    @classmethod
    def _validar_test_database_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("postgresql+psycopg://"):
            raise ValueError("TEST_DATABASE_URL debe usar el driver postgresql+psycopg://")
        nombre_bd = v.rsplit("/", 1)[-1]
        if not nombre_bd.endswith("_test"):
            raise ValueError("TEST_DATABASE_URL debe apuntar a una base cuyo nombre termine en _test")
        return v

    @field_validator("jwt_secret")
    @classmethod
    def _validar_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET debe tener al menos 32 caracteres")
        return v

    @field_validator("jwt_expira_minutos")
    @classmethod
    def _validar_jwt_expira_minutos(cls, v: int) -> int:
        if not (5 <= v <= 1440):
            raise ValueError("JWT_EXPIRA_MINUTOS debe estar entre 5 y 1440")
        return v

    @field_validator("mfa_clave_cifrado")
    @classmethod
    def _validar_mfa_clave_cifrado(cls, v: str) -> str:
        try:
            Fernet(v.encode())
        except Exception as exc:
            raise ValueError("MFA_CLAVE_CIFRADO debe ser una clave Fernet valida") from exc
        return v

    @model_validator(mode="after")
    def _validar_positivos(self) -> "Configuracion":
        campos_positivos = {
            "login_max_intentos": self.login_max_intentos,
            "bloqueo_minutos": self.bloqueo_minutos,
            "mfa_max_intentos": self.mfa_max_intentos,
            "desafio_minutos": self.desafio_minutos,
            "stock_bajo_umbral": self.stock_bajo_umbral,
        }
        for nombre, valor in campos_positivos.items():
            if valor <= 0:
                raise ValueError(f"{nombre} debe ser un entero positivo")
        return self


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
