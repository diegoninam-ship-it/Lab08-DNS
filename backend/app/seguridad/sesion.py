from fastapi import Cookie, Depends, HTTPException, Response
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.config import obtener_configuracion
from app.db import obtener_db
from app.modelos import Estado, Usuario
from app.seguridad.jwt import crear_token, decodificar_token

NOMBRE_COOKIE_SESION = "techstore_token"


def establecer_cookie_sesion(response: Response, usuario_id: int, token_version: int, ahora) -> None:
    configuracion = obtener_configuracion()
    token = crear_token(usuario_id, token_version, ahora)
    response.set_cookie(
        key=NOMBRE_COOKIE_SESION,
        value=token,
        httponly=True,
        samesite="strict",
        path="/api",
        secure=configuracion.cookie_secure,
        max_age=configuracion.jwt_expira_minutos * 60,
    )


def borrar_cookie_sesion(response: Response) -> None:
    response.delete_cookie(key=NOMBRE_COOKIE_SESION, path="/api")


def obtener_usuario_actual(
    techstore_token: str | None = Cookie(default=None, alias=NOMBRE_COOKIE_SESION),
    db: Session = Depends(obtener_db),
) -> Usuario:
    error_no_autenticado = HTTPException(status_code=401, detail="No autenticado")

    if techstore_token is None:
        raise error_no_autenticado

    try:
        payload = decodificar_token(techstore_token)
    except PyJWTError:
        raise error_no_autenticado

    usuario = db.get(Usuario, int(payload["sub"]))
    if (
        usuario is None
        or usuario.estado != Estado.ACTIVO
        or usuario.rol is None
        or usuario.token_version != payload["ver"]
    ):
        raise error_no_autenticado

    return usuario
