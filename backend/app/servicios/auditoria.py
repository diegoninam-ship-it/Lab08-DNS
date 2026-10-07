from fastapi import Request
from sqlalchemy.orm import Session

from app.modelos import Auditoria


def obtener_ip_cliente(request: Request) -> str | None:
    return request.client.host if request.client else None


def registrar_auditoria(
    db: Session,
    *,
    accion: str,
    usuario_id: int | None = None,
    email_intentado: str | None = None,
    recurso: str | None = None,
    recurso_id: int | str | None = None,
    detalle: dict | None = None,
    ip: str | None = None,
) -> None:
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            email_intentado=email_intentado,
            accion=accion,
            recurso=recurso,
            recurso_id=str(recurso_id) if recurso_id is not None else None,
            detalle=detalle,
            ip=ip,
        )
    )
