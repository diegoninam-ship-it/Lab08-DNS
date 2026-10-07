from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import obtener_configuracion
from app.db import obtener_db
from app.esquemas.reporte import ReporteInventarioTienda
from app.modelos import Producto, Rol, Tienda, Usuario
from app.seguridad.sesion import obtener_usuario_actual
from app.servicios.autorizacion import exigir

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/inventario", response_model=list[ReporteInventarioTienda])
def reporte_inventario(
    request: Request,
    tienda_id: int | None = Query(default=None),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    exigir(
        usuario.rol in (Rol.ADMIN, Rol.GERENTE, Rol.AUDITOR),
        db=db,
        usuario=usuario,
        request=request,
        recurso="reporte_inventario",
    )

    if usuario.rol == Rol.GERENTE:
        exigir(
            tienda_id is None or tienda_id == usuario.tienda_id,
            db=db,
            usuario=usuario,
            request=request,
            recurso="reporte_inventario",
            recurso_id=tienda_id,
        )
        tiendas_ids = [usuario.tienda_id]
    elif tienda_id is not None:
        tiendas_ids = [tienda_id]
    else:
        tiendas_ids = None

    consulta_tiendas = select(Tienda)
    if tiendas_ids is not None:
        consulta_tiendas = consulta_tiendas.where(Tienda.id.in_(tiendas_ids))
    tiendas = db.scalars(consulta_tiendas.order_by(Tienda.nombre)).all()

    umbral = obtener_configuracion().stock_bajo_umbral

    resultado = []
    for tienda in tiendas:
        productos = db.scalars(select(Producto).where(Producto.tienda_id == tienda.id)).all()
        resultado.append(
            ReporteInventarioTienda(
                tienda=tienda,
                total_productos=len(productos),
                total_unidades=sum(p.stock for p in productos),
                valor_inventario=sum((p.precio * p.stock for p in productos), Decimal("0")),
                stock_bajo=[p for p in productos if p.stock <= umbral],
            )
        )
    return resultado
