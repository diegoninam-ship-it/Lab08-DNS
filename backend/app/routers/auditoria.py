from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import obtener_db
from app.esquemas.auditoria import ListadoAuditoriaSalida
from app.modelos import Auditoria, Rol, Usuario
from app.seguridad.sesion import obtener_usuario_actual
from app.servicios.autorizacion import exigir

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("", response_model=ListadoAuditoriaSalida)
def listar_auditoria(
    request: Request,
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    accion: str | None = Query(default=None),
    usuario_id: int | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    exigir(
        usuario.rol in (Rol.ADMIN, Rol.AUDITOR),
        db=db,
        usuario=usuario,
        request=request,
        recurso="auditoria",
    )

    consulta = select(Auditoria)
    if desde is not None:
        consulta = consulta.where(Auditoria.creado_en >= desde)
    if hasta is not None:
        consulta = consulta.where(Auditoria.creado_en <= hasta)
    if accion is not None:
        consulta = consulta.where(Auditoria.accion == accion)
    if usuario_id is not None:
        consulta = consulta.where(Auditoria.usuario_id == usuario_id)

    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    items = db.scalars(
        consulta.order_by(Auditoria.creado_en.desc(), Auditoria.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).all()

    return {"total": total, "pagina": pagina, "tamano": tamano, "items": items}
