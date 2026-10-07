from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.esquemas.tienda import TiendaSalida
from app.modelos.enums import Rol
from app.seguridad.contrasenas import validar_politica_contrasena


class RegistroEntrada(BaseModel):
    email: EmailStr
    contrasena: str
    nombre_completo: str = Field(min_length=1, max_length=120)
    tienda_id: int

    @field_validator("email")
    @classmethod
    def _normalizar_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("contrasena")
    @classmethod
    def _validar_contrasena(cls, v: str) -> str:
        validar_politica_contrasena(v)
        return v


class LoginEntrada(BaseModel):
    email: EmailStr
    contrasena: str

    @field_validator("email")
    @classmethod
    def _normalizar_email(cls, v: str) -> str:
        return v.strip().lower()


class MfaIniciarEntrada(BaseModel):
    desafio_token: str


class MfaVerificarEntrada(BaseModel):
    desafio_token: str
    codigo: str


class UsuarioSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre_completo: str
    rol: Rol | None
    tienda: TiendaSalida
