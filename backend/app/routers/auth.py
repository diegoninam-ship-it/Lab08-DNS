import hashlib
import math
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import obtener_configuracion
from app.db import obtener_db
from app.esquemas.auth import (
    LoginEntrada,
    MfaIniciarEntrada,
    MfaVerificarEntrada,
    RegistroEntrada,
    UsuarioSalida,
)
from app.modelos import DesafioMfa, Estado, Tienda, Usuario
from app.reloj import Reloj, obtener_reloj
from app.seguridad.cifrado import cifrar, descifrar
from app.seguridad.contrasenas import hash_contrasena, verificar_contrasena
from app.seguridad.mfa import construir_otpauth_uri, generar_secreto, verificar_codigo
from app.seguridad.sesion import (
    borrar_cookie_sesion,
    establecer_cookie_sesion,
    obtener_usuario_actual,
)
from app.servicios.auditoria import obtener_ip_cliente, registrar_auditoria

router = APIRouter(prefix="/auth", tags=["auth"])

CONTRASENA_FICTICIA = "ContrasenaFicticiaParaTiempoConstante1!"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _generar_token_opaco() -> str:
    return secrets.token_urlsafe(32)


def _crear_desafio_mfa(db: Session, usuario: Usuario, reloj: Reloj) -> tuple[DesafioMfa, str]:
    configuracion = obtener_configuracion()
    token = _generar_token_opaco()
    desafio = DesafioMfa(
        usuario_id=usuario.id,
        token_hash=_hash_token(token),
        expira_en=reloj.ahora() + timedelta(minutes=configuracion.desafio_minutos),
    )
    db.add(desafio)
    db.flush()
    return desafio, token


def _obtener_desafio_valido(db: Session, token: str, reloj: Reloj) -> DesafioMfa:
    desafio = db.scalar(select(DesafioMfa).where(DesafioMfa.token_hash == _hash_token(token)))
    if desafio is None or desafio.usado or desafio.expira_en < reloj.ahora():
        raise HTTPException(status_code=401, detail="Desafio invalido o expirado")
    return desafio


def _preparar_enrolamiento(usuario: Usuario) -> str:
    if usuario.mfa_secreto_cifrado is None:
        secreto = generar_secreto()
        usuario.mfa_secreto_cifrado = cifrar(secreto)
    else:
        secreto = descifrar(usuario.mfa_secreto_cifrado)
    return construir_otpauth_uri(secreto, usuario.email)


def _respuesta_desafio(usuario: Usuario, token: str) -> dict:
    if not usuario.mfa_activo:
        otpauth_uri = _preparar_enrolamiento(usuario)
        return {"paso": "MFA_ENROLAMIENTO", "desafio_token": token, "otpauth_uri": otpauth_uri}
    return {"paso": "MFA_REQUERIDO", "desafio_token": token}


@router.post("/registro", status_code=201)
def registrar_usuario(datos: RegistroEntrada, db: Session = Depends(obtener_db)):
    existente = db.scalar(select(Usuario).where(Usuario.email == datos.email))
    if existente is not None:
        raise HTTPException(status_code=409, detail="El correo ya esta registrado")

    tienda = db.get(Tienda, datos.tienda_id)
    if tienda is None:
        raise HTTPException(status_code=422, detail="La tienda indicada no existe")

    usuario = Usuario(
        email=datos.email,
        nombre_completo=datos.nombre_completo,
        password_hash=hash_contrasena(datos.contrasena),
        tienda_id=tienda.id,
        rol=None,
        estado=Estado.PENDIENTE,
    )
    db.add(usuario)
    db.flush()
    registrar_auditoria(
        db,
        accion="REGISTRO",
        usuario_id=usuario.id,
        recurso="usuario",
        recurso_id=usuario.id,
    )
    db.commit()
    return {"detail": "Registro exitoso, pendiente de activacion por un administrador"}


@router.post("/login")
def login(datos: LoginEntrada, request: Request, db: Session = Depends(obtener_db), reloj: Reloj = Depends(obtener_reloj)):
    configuracion = obtener_configuracion()
    ip = obtener_ip_cliente(request)

    usuario = db.scalar(select(Usuario).where(Usuario.email == datos.email))
    if usuario is None:
        hash_contrasena(CONTRASENA_FICTICIA)
        registrar_auditoria(db, accion="LOGIN_FALLIDO", email_intentado=datos.email, ip=ip)
        db.commit()
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

    ahora = reloj.ahora()

    if usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > ahora:
        minutos_restantes = math.ceil((usuario.bloqueado_hasta - ahora).total_seconds() / 60)
        raise HTTPException(
            status_code=423,
            detail=f"Cuenta bloqueada. Intenta nuevamente en {minutos_restantes} minutos",
        )

    if not verificar_contrasena(datos.contrasena, usuario.password_hash):
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= configuracion.login_max_intentos:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=configuracion.bloqueo_minutos)
            usuario.intentos_fallidos = 0
            registrar_auditoria(db, accion="CUENTA_BLOQUEADA", usuario_id=usuario.id, ip=ip)
        registrar_auditoria(db, accion="LOGIN_FALLIDO", usuario_id=usuario.id, email_intentado=datos.email, ip=ip)
        db.commit()
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

    usuario.intentos_fallidos = 0

    if usuario.estado != Estado.ACTIVO:
        motivo = "La cuenta esta pendiente de activacion" if usuario.estado == Estado.PENDIENTE else "La cuenta esta desactivada"
        registrar_auditoria(db, accion="LOGIN_RECHAZADO", usuario_id=usuario.id, detalle={"motivo": motivo}, ip=ip)
        db.commit()
        raise HTTPException(status_code=403, detail=motivo)

    _desafio, token = _crear_desafio_mfa(db, usuario, reloj)
    respuesta = _respuesta_desafio(usuario, token)
    db.commit()
    return respuesta


@router.post("/mfa/iniciar")
def mfa_iniciar(datos: MfaIniciarEntrada, db: Session = Depends(obtener_db), reloj: Reloj = Depends(obtener_reloj)):
    desafio = _obtener_desafio_valido(db, datos.desafio_token, reloj)
    usuario = db.get(Usuario, desafio.usuario_id)

    if not usuario.mfa_activo:
        otpauth_uri = _preparar_enrolamiento(usuario)
        db.commit()
        return {"paso": "MFA_ENROLAMIENTO", "otpauth_uri": otpauth_uri}

    db.commit()
    return {"paso": "MFA_REQUERIDO"}


@router.post("/mfa/verificar")
def mfa_verificar(
    datos: MfaVerificarEntrada,
    request: Request,
    response: Response,
    db: Session = Depends(obtener_db),
    reloj: Reloj = Depends(obtener_reloj),
):
    configuracion = obtener_configuracion()
    ip = obtener_ip_cliente(request)
    desafio = _obtener_desafio_valido(db, datos.desafio_token, reloj)
    usuario = db.get(Usuario, desafio.usuario_id)

    if usuario.mfa_secreto_cifrado is None:
        raise HTTPException(status_code=401, detail="Desafio invalido o expirado")

    secreto = descifrar(usuario.mfa_secreto_cifrado)
    contador = verificar_codigo(secreto, datos.codigo, usuario.mfa_ultimo_contador, reloj.ahora())

    if contador is None:
        desafio.intentos += 1
        registrar_auditoria(db, accion="MFA_FALLIDO", usuario_id=usuario.id, ip=ip)

        if desafio.intentos >= configuracion.mfa_max_intentos:
            desafio.usado = True
            registrar_auditoria(db, accion="MFA_DESAFIO_AGOTADO", usuario_id=usuario.id, ip=ip)
            db.commit()
            raise HTTPException(status_code=401, detail="Desafio invalido o expirado")

        db.commit()
        intentos_restantes = configuracion.mfa_max_intentos - desafio.intentos
        return JSONResponse(
            status_code=401,
            content={"detail": "Codigo invalido", "intentos_restantes": intentos_restantes},
        )

    desafio.usado = True
    usuario.mfa_ultimo_contador = contador
    primera_activacion = not usuario.mfa_activo
    usuario.mfa_activo = True
    db.flush()

    registrar_auditoria(
        db,
        accion="MFA_ENROLADO" if primera_activacion else "LOGIN_OK",
        usuario_id=usuario.id,
        ip=ip,
    )

    establecer_cookie_sesion(response, usuario.id, usuario.token_version, reloj.ahora())
    db.commit()
    db.refresh(usuario)
    return {"usuario": UsuarioSalida.model_validate(usuario)}


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    usuario: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_db),
):
    usuario.token_version += 1
    registrar_auditoria(db, accion="LOGOUT", usuario_id=usuario.id)
    db.commit()
    borrar_cookie_sesion(response)


@router.get("/me", response_model=UsuarioSalida)
def me(usuario: Usuario = Depends(obtener_usuario_actual)):
    return usuario
