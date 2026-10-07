from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import obtener_db
from app.esquemas.producto import (
    ListadoProductosSalida,
    ProductoCrearEntrada,
    ProductoEditarEntrada,
    ProductoSalida,
    StockActualizarEntrada,
)
from app.modelos import Producto, Rol, Tienda, Usuario
from app.seguridad.sesion import obtener_usuario_actual
from app.servicios.auditoria import obtener_ip_cliente, registrar_auditoria
from app.servicios.autorizacion import exigir

router = APIRouter(prefix="/productos", tags=["productos"])


def _snapshot_producto(producto: Producto) -> dict:
    return {
        "sku": producto.sku,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "precio": str(producto.precio),
        "stock": producto.stock,
        "tienda_id": producto.tienda_id,
    }


def _obtener_o_404(db: Session, producto_id: int) -> Producto:
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.get("", response_model=ListadoProductosSalida)
def listar_productos(
    tienda_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    tamano: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    consulta = select(Producto)
    if tienda_id is not None:
        consulta = consulta.where(Producto.tienda_id == tienda_id)
    if q:
        patron = f"%{q}%"
        consulta = consulta.where(or_(Producto.nombre.ilike(patron), Producto.sku.ilike(patron)))

    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    items = db.scalars(
        consulta.order_by(Producto.id).offset((pagina - 1) * tamano).limit(tamano)
    ).all()

    return {"total": total, "pagina": pagina, "tamano": tamano, "items": items}


@router.get("/{producto_id}", response_model=ProductoSalida)
def obtener_producto(
    producto_id: int,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    return _obtener_o_404(db, producto_id)


@router.post("", response_model=ProductoSalida, status_code=201)
def crear_producto(
    datos: ProductoCrearEntrada,
    request: Request,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    exigir(
        usuario.rol in (Rol.ADMIN, Rol.GERENTE),
        db=db,
        usuario=usuario,
        request=request,
        recurso="producto",
    )

    if usuario.rol == Rol.GERENTE:
        tienda_id = usuario.tienda_id
    else:
        if datos.tienda_id is None:
            raise HTTPException(status_code=422, detail="tienda_id es obligatorio")
        tienda_id = datos.tienda_id

    tienda = db.get(Tienda, tienda_id)
    if tienda is None:
        raise HTTPException(status_code=422, detail="La tienda indicada no existe")

    existente = db.scalar(
        select(Producto).where(Producto.tienda_id == tienda_id, Producto.sku == datos.sku)
    )
    if existente is not None:
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese SKU en la tienda")

    producto = Producto(
        tienda_id=tienda_id,
        sku=datos.sku,
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        precio=datos.precio,
        stock=datos.stock,
        actualizado_por=usuario.id,
    )
    db.add(producto)
    db.flush()

    registrar_auditoria(
        db,
        accion="PRODUCTO_CREADO",
        usuario_id=usuario.id,
        recurso="producto",
        recurso_id=producto.id,
        detalle={"despues": _snapshot_producto(producto)},
        ip=obtener_ip_cliente(request),
    )
    db.commit()
    db.refresh(producto)
    return producto


@router.put("/{producto_id}", response_model=ProductoSalida)
def editar_producto(
    producto_id: int,
    datos: ProductoEditarEntrada,
    request: Request,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    producto = _obtener_o_404(db, producto_id)

    exigir(
        usuario.rol == Rol.ADMIN
        or (usuario.rol == Rol.GERENTE and producto.tienda_id == usuario.tienda_id),
        db=db,
        usuario=usuario,
        request=request,
        recurso="producto",
        recurso_id=producto.id,
    )

    if datos.sku != producto.sku:
        conflicto = db.scalar(
            select(Producto).where(
                Producto.tienda_id == producto.tienda_id,
                Producto.sku == datos.sku,
                Producto.id != producto.id,
            )
        )
        if conflicto is not None:
            raise HTTPException(status_code=409, detail="Ya existe un producto con ese SKU en la tienda")

    antes = _snapshot_producto(producto)

    producto.sku = datos.sku
    producto.nombre = datos.nombre
    producto.descripcion = datos.descripcion
    producto.precio = datos.precio
    producto.actualizado_por = usuario.id
    db.flush()

    registrar_auditoria(
        db,
        accion="PRODUCTO_EDITADO",
        usuario_id=usuario.id,
        recurso="producto",
        recurso_id=producto.id,
        detalle={"antes": antes, "despues": _snapshot_producto(producto)},
        ip=obtener_ip_cliente(request),
    )
    db.commit()
    db.refresh(producto)
    return producto


@router.patch("/{producto_id}/stock", response_model=ProductoSalida)
def actualizar_stock(
    producto_id: int,
    datos: StockActualizarEntrada,
    request: Request,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    producto = _obtener_o_404(db, producto_id)

    exigir(
        usuario.rol == Rol.ADMIN
        or (usuario.rol in (Rol.GERENTE, Rol.EMPLEADO) and producto.tienda_id == usuario.tienda_id),
        db=db,
        usuario=usuario,
        request=request,
        recurso="producto",
        recurso_id=producto.id,
    )

    antes = producto.stock
    producto.stock = datos.stock
    producto.actualizado_por = usuario.id
    db.flush()

    registrar_auditoria(
        db,
        accion="STOCK_ACTUALIZADO",
        usuario_id=usuario.id,
        recurso="producto",
        recurso_id=producto.id,
        detalle={"antes": antes, "despues": producto.stock},
        ip=obtener_ip_cliente(request),
    )
    db.commit()
    db.refresh(producto)
    return producto


@router.delete("/{producto_id}", status_code=204)
def eliminar_producto(
    producto_id: int,
    request: Request,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    producto = _obtener_o_404(db, producto_id)

    exigir(
        usuario.rol == Rol.ADMIN
        or (usuario.rol == Rol.GERENTE and producto.tienda_id == usuario.tienda_id),
        db=db,
        usuario=usuario,
        request=request,
        recurso="producto",
        recurso_id=producto.id,
    )

    antes = _snapshot_producto(producto)
    producto_id_eliminado = producto.id
    db.delete(producto)

    registrar_auditoria(
        db,
        accion="PRODUCTO_ELIMINADO",
        usuario_id=usuario.id,
        recurso="producto",
        recurso_id=producto_id_eliminado,
        detalle={"antes": antes},
        ip=obtener_ip_cliente(request),
    )
    db.commit()
