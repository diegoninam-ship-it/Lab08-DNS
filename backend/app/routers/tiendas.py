from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import obtener_db
from app.esquemas.tienda import TiendaCrearEntrada, TiendaEditarEntrada, TiendaSalida
from app.modelos import Rol, Tienda, Usuario
from app.seguridad.sesion import obtener_usuario_actual
from app.servicios.auditoria import obtener_ip_cliente, registrar_auditoria
from app.servicios.autorizacion import exigir

router = APIRouter(tags=["tiendas"])


@router.get("/tiendas", response_model=list[TiendaSalida])
def listar_tiendas(db: Session = Depends(obtener_db)) -> list[Tienda]:
    return list(db.scalars(select(Tienda).order_by(Tienda.nombre)))


@router.post("/tiendas", response_model=TiendaSalida, status_code=201)
def crear_tienda(
    datos: TiendaCrearEntrada,
    request: Request,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    exigir(usuario.rol == Rol.ADMIN, db=db, usuario=usuario, request=request, recurso="tienda")

    existente = db.scalar(select(Tienda).where(Tienda.nombre == datos.nombre))
    if existente is not None:
        raise HTTPException(status_code=409, detail="Ya existe una tienda con ese nombre")

    tienda = Tienda(nombre=datos.nombre, ciudad=datos.ciudad)
    db.add(tienda)
    db.flush()

    registrar_auditoria(
        db,
        accion="TIENDA_CREADA",
        usuario_id=usuario.id,
        recurso="tienda",
        recurso_id=tienda.id,
        detalle={"despues": {"nombre": tienda.nombre, "ciudad": tienda.ciudad}},
        ip=obtener_ip_cliente(request),
    )
    db.commit()
    db.refresh(tienda)
    return tienda


@router.put("/tiendas/{tienda_id}", response_model=TiendaSalida)
def editar_tienda(
    tienda_id: int,
    datos: TiendaEditarEntrada,
    request: Request,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    exigir(usuario.rol == Rol.ADMIN, db=db, usuario=usuario, request=request, recurso="tienda", recurso_id=tienda_id)

    tienda = db.get(Tienda, tienda_id)
    if tienda is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")

    if datos.nombre != tienda.nombre:
        conflicto = db.scalar(select(Tienda).where(Tienda.nombre == datos.nombre, Tienda.id != tienda.id))
        if conflicto is not None:
            raise HTTPException(status_code=409, detail="Ya existe una tienda con ese nombre")

    antes = {"nombre": tienda.nombre, "ciudad": tienda.ciudad}
    tienda.nombre = datos.nombre
    tienda.ciudad = datos.ciudad
    db.flush()

    registrar_auditoria(
        db,
        accion="TIENDA_EDITADA",
        usuario_id=usuario.id,
        recurso="tienda",
        recurso_id=tienda.id,
        detalle={"antes": antes, "despues": {"nombre": tienda.nombre, "ciudad": tienda.ciudad}},
        ip=obtener_ip_cliente(request),
    )
    db.commit()
    db.refresh(tienda)
    return tienda
