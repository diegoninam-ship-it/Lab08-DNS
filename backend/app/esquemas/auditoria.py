from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditoriaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int | None
    email_intentado: str | None
    accion: str
    recurso: str | None
    recurso_id: str | None
    detalle: dict | None
    ip: str | None
    creado_en: datetime


class ListadoAuditoriaSalida(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[AuditoriaSalida]
