from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.esquemas.tienda import TiendaSalida
from app.modelos.enums import Estado, Rol


class UsuarioActualizarEntrada(BaseModel):
    estado: Estado | None = None
    rol: Rol | None = None
    tienda_id: int | None = None


class UsuarioAdminSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre_completo: str
    rol: Rol | None
    estado: Estado
    tienda: TiendaSalida
    intentos_fallidos: int
    bloqueado_hasta: datetime | None
    mfa_activo: bool
    creado_en: datetime
    actualizado_en: datetime
