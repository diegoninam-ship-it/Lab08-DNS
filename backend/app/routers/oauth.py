import secrets
from typing import Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.servicios.oauth_proveedores as oauth_proveedores
from app.config import obtener_configuracion
from app.db import obtener_db
from app.modelos import Estado, IdentidadSocial, Proveedor, Usuario
from app.reloj import Reloj, obtener_reloj
from app.routers.auth import _crear_desafio_mfa
from app.servicios.auditoria import obtener_ip_cliente, registrar_auditoria

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])

NOMBRE_COOKIE_STATE = "techstore_oauth_state"
MINUTOS_STATE = 10
NombreProveedor = Literal["google", "github"]


def _redirect_uri(proveedor: str) -> str:
    configuracion = obtener_configuracion()
    return f"{configuracion.url_publica}/api/auth/oauth/{proveedor}/callback"


def _redirigir_con_error(codigo: str) -> RedirectResponse:
    configuracion = obtener_configuracion()
    respuesta = RedirectResponse(url=f"{configuracion.url_publica}/login?error={codigo}", status_code=302)
    respuesta.delete_cookie(key=NOMBRE_COOKIE_STATE, path="/api/auth/oauth")
    return respuesta


@router.get("/{proveedor}/login")
def oauth_login(proveedor: NombreProveedor):
    try:
        proveedor_oauth = oauth_proveedores.obtener_proveedor(proveedor)
    except oauth_proveedores.ProveedorOAuthNoConfiguradoError:
        raise HTTPException(status_code=503, detail="Proveedor no configurado")

    configuracion = obtener_configuracion()
    state = secrets.token_urlsafe(32)
    url_autorizacion = proveedor_oauth.construir_url_autorizacion(state, _redirect_uri(proveedor))

    respuesta = RedirectResponse(url=url_autorizacion, status_code=302)
    respuesta.set_cookie(
        key=NOMBRE_COOKIE_STATE,
        value=state,
        httponly=True,
        samesite="lax",
        path="/api/auth/oauth",
        secure=configuracion.cookie_secure,
        max_age=MINUTOS_STATE * 60,
    )
    return respuesta


@router.get("/{proveedor}/callback")
def oauth_callback(
    proveedor: NombreProveedor,
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    techstore_oauth_state: str | None = Cookie(default=None, alias=NOMBRE_COOKIE_STATE),
    db: Session = Depends(obtener_db),
    reloj: Reloj = Depends(obtener_reloj),
):
    ip = obtener_ip_cliente(request)

    if (
        techstore_oauth_state is None
        or state is None
        or not secrets.compare_digest(techstore_oauth_state, state)
    ):
        return _redirigir_con_error("estado_invalido")

    try:
        proveedor_oauth = oauth_proveedores.obtener_proveedor(proveedor)
    except oauth_proveedores.ProveedorOAuthNoConfiguradoError:
        return _redirigir_con_error("proveedor_no_configurado")

    identidad = proveedor_oauth.obtener_identidad(code or "", _redirect_uri(proveedor))

    if not identidad.email_verificado:
        registrar_auditoria(
            db,
            accion="LOGIN_SOCIAL_RECHAZADO",
            email_intentado=identidad.email,
            ip=ip,
            detalle={"motivo": "correo_no_verificado", "proveedor": proveedor},
        )
        db.commit()
        return _redirigir_con_error("correo_no_verificado")

    proveedor_enum = Proveedor(proveedor)
    email_normalizado = identidad.email.strip().lower()

    identidad_social = db.scalar(
        select(IdentidadSocial).where(
            IdentidadSocial.proveedor == proveedor_enum,
            IdentidadSocial.proveedor_uid == identidad.proveedor_uid,
        )
    )

    if identidad_social is not None:
        usuario = db.get(Usuario, identidad_social.usuario_id)
    else:
        usuario = db.scalar(select(Usuario).where(Usuario.email == email_normalizado))
        if usuario is not None:
            db.add(
                IdentidadSocial(
                    usuario_id=usuario.id,
                    proveedor=proveedor_enum,
                    proveedor_uid=identidad.proveedor_uid,
                    email=email_normalizado,
                )
            )

    if usuario is None:
        registrar_auditoria(
            db,
            accion="LOGIN_SOCIAL_RECHAZADO",
            email_intentado=email_normalizado,
            ip=ip,
            detalle={"motivo": "no_registrado", "proveedor": proveedor},
        )
        db.commit()
        return _redirigir_con_error("no_registrado")

    if usuario.estado == Estado.PENDIENTE:
        registrar_auditoria(
            db,
            accion="LOGIN_SOCIAL_RECHAZADO",
            usuario_id=usuario.id,
            ip=ip,
            detalle={"motivo": "pendiente", "proveedor": proveedor},
        )
        db.commit()
        return _redirigir_con_error("pendiente")

    if usuario.estado == Estado.DESACTIVADO:
        registrar_auditoria(
            db,
            accion="LOGIN_SOCIAL_RECHAZADO",
            usuario_id=usuario.id,
            ip=ip,
            detalle={"motivo": "desactivada", "proveedor": proveedor},
        )
        db.commit()
        return _redirigir_con_error("desactivada")

    _desafio, token = _crear_desafio_mfa(db, usuario, reloj)
    db.commit()

    configuracion = obtener_configuracion()
    respuesta = RedirectResponse(url=f"{configuracion.url_publica}/mfa#desafio={token}", status_code=302)
    respuesta.delete_cookie(key=NOMBRE_COOKIE_STATE, path="/api/auth/oauth")
    return respuesta
