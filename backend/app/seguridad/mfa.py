from datetime import datetime

import pyotp

from app.config import obtener_configuracion

PASO_SEGUNDOS = 30
VENTANA_VALIDA = 1


def generar_secreto() -> str:
    return pyotp.random_base32()


def construir_otpauth_uri(secreto: str, email: str) -> str:
    configuracion = obtener_configuracion()
    totp = pyotp.TOTP(secreto)
    return totp.provisioning_uri(name=email, issuer_name=configuracion.mfa_emisor)


def verificar_codigo(secreto: str, codigo: str, contador_anterior: int | None, ahora: datetime) -> int | None:
    """Verifica el codigo TOTP con ventana de +-30s y anti-reutilizacion.

    Devuelve el contador de tiempo usado si el codigo es valido y no fue
    usado antes (contador estrictamente mayor que `contador_anterior`), o
    None si el codigo es invalido o ya fue utilizado.
    """
    totp = pyotp.TOTP(secreto)
    contador_actual = int(ahora.timestamp() // PASO_SEGUNDOS)
    for offset in range(-VENTANA_VALIDA, VENTANA_VALIDA + 1):
        contador = contador_actual + offset
        if contador_anterior is not None and contador <= contador_anterior:
            continue
        if totp.verify(codigo, for_time=contador * PASO_SEGUNDOS, valid_window=0):
            return contador
    return None
