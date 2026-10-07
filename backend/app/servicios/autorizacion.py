from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.modelos import Usuario
from app.servicios.auditoria import obtener_ip_cliente, registrar_auditoria


def exigir(
    permitido: bool,
    *,
    db: Session,
    usuario: Usuario,
    request: Request,
    recurso: str,
    recurso_id: int | str | None = None,
    detalle: dict | None = None,
) -> None:
    """Deniega por defecto: si `permitido` es False, registra ACCESO_DENEGADO y lanza 403."""
    if permitido:
        return

    registrar_auditoria(
        db,
        accion="ACCESO_DENEGADO",
        usuario_id=usuario.id,
        recurso=recurso,
        recurso_id=recurso_id,
        detalle=detalle,
        ip=obtener_ip_cliente(request),
    )
    db.commit()
    raise HTTPException(status_code=403, detail="No tiene permisos para esta accion")
