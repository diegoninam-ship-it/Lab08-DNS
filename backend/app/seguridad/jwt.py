from datetime import datetime, timedelta

import jwt

from app.config import obtener_configuracion

ALGORITMO = "HS256"


def crear_token(usuario_id: int, token_version: int, ahora: datetime) -> str:
    configuracion = obtener_configuracion()
    payload = {
        "sub": str(usuario_id),
        "ver": token_version,
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + timedelta(minutes=configuracion.jwt_expira_minutos)).timestamp()),
    }
    return jwt.encode(payload, configuracion.jwt_secret, algorithm=ALGORITMO)


def decodificar_token(token: str) -> dict:
    configuracion = obtener_configuracion()
    return jwt.decode(token, configuracion.jwt_secret, algorithms=[ALGORITMO])
