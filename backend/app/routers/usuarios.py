from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import obtener_db
from app.esquemas.usuario import UsuarioActualizarEntrada, UsuarioAdminSalida
from app.modelos import Estado, Rol, Tienda, Usuario
from app.seguridad.sesion import obtener_usuario_actual
from app.servicios.auditoria import obtener_ip_cliente, registrar_auditoria
from app.servicios.autorizacion import exigir

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def _snapshot_usuario(usuario: Usuario) -> dict:
    return {
        "estado": usuario.estado.value,
        "rol": usuario.rol.value if usuario.rol is not None else None,
        "tienda_id": usuario.tienda_id,
    }


def _obtener_o_404(db: Session, usuario_id: int) -> Usuario:
    objetivo = db.get(Usuario, usuario_id)
    if objetivo is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return objetivo


@router.get("", response_model=list[UsuarioAdminSalida])
def listar_usuarios(
    request: Request,
    estado: Estado | None = Query(default=None),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    exigir(usuario.rol == Rol.ADMIN, db=db, usuario=usuario, request=request, recurso="usuario")

    consulta = select(Usuario)
    if estado is not None:
        consulta = consulta.where(Usuario.estado == estado)
    return db.scalars(consulta.order_by(Usuario.id)).all()


@router.patch("/{usuario_id}", response_model=UsuarioAdminSalida)
def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioActualizarEntrada,
    request: Request,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    exigir(
        usuario.rol == Rol.ADMIN,
        db=db,
        usuario=usuario,
        request=request,
        recurso="usuario",
        recurso_id=usuario_id,
    )

    if usuario_id == usuario.id:
        raise HTTPException(status_code=409, detail="El administrador no puede modificarse a si mismo")

    objetivo = _obtener_o_404(db, usuario_id)
    antes = _snapshot_usuario(objetivo)

    nuevo_estado = datos.estado if datos.estado is not None else objetivo.estado
    nuevo_rol = datos.rol if datos.rol is not None else objetivo.rol

    if nuevo_estado == Estado.ACTIVO and nuevo_rol is None:
        raise HTTPException(status_code=422, detail="Activar un usuario exige asignarle un rol")

    if datos.tienda_id is not None and db.get(Tienda, datos.tienda_id) is None:
        raise HTTPException(status_code=422, detail="La tienda indicada no existe")

    objetivo.estado = nuevo_estado
    objetivo.rol = nuevo_rol
    if datos.tienda_id is not None:
        objetivo.tienda_id = datos.tienda_id
    db.flush()

    registrar_auditoria(
        db,
        accion="USUARIO_ACTUALIZADO",
        usuario_id=usuario.id,
        recurso="usuario",
        recurso_id=objetivo.id,
        detalle={"antes": antes, "despues": _snapshot_usuario(objetivo)},
        ip=obtener_ip_cliente(request),
    )
    db.commit()
    db.refresh(objetivo)
    return objetivo


@router.post("/{usuario_id}/desbloquear", response_model=UsuarioAdminSalida)
def desbloquear_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    exigir(
        usuario.rol == Rol.ADMIN,
        db=db,
        usuario=usuario,
        request=request,
        recurso="usuario",
        recurso_id=usuario_id,
    )

    objetivo = _obtener_o_404(db, usuario_id)
    objetivo.bloqueado_hasta = None
    objetivo.intentos_fallidos = 0
    db.flush()

    registrar_auditoria(
        db,
        accion="USUARIO_DESBLOQUEADO",
        usuario_id=usuario.id,
        recurso="usuario",
        recurso_id=objetivo.id,
        ip=obtener_ip_cliente(request),
    )
    db.commit()
    db.refresh(objetivo)
    return objetivo


@router.post("/{usuario_id}/mfa/restablecer", response_model=UsuarioAdminSalida)
def restablecer_mfa(
    usuario_id: int,
    request: Request,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    exigir(
        usuario.rol == Rol.ADMIN,
        db=db,
        usuario=usuario,
        request=request,
        recurso="usuario",
        recurso_id=usuario_id,
    )

    objetivo = _obtener_o_404(db, usuario_id)
    objetivo.mfa_secreto_cifrado = None
    objetivo.mfa_activo = False
    objetivo.mfa_ultimo_contador = None
    objetivo.token_version += 1
    db.flush()

    registrar_auditoria(
        db,
        accion="MFA_RESTABLECIDO",
        usuario_id=usuario.id,
        recurso="usuario",
        recurso_id=objetivo.id,
        ip=obtener_ip_cliente(request),
    )
    db.commit()
    db.refresh(objetivo)
    return objetivo
