import re

import bcrypt

LIMITE_BYTES_BCRYPT = 72

PATRON_MAYUSCULA = re.compile(r"[A-Z]")
PATRON_DIGITO = re.compile(r"[0-9]")
PATRON_ESPECIAL = re.compile(r"[^A-Za-z0-9]")


class ContrasenaDemasiadoLargaError(ValueError):
    pass


class PoliticaContrasenaError(ValueError):
    pass


def validar_politica_contrasena(contrasena: str) -> None:
    if len(contrasena) < 8:
        raise PoliticaContrasenaError("La contrasena debe tener al menos 8 caracteres")
    if not PATRON_MAYUSCULA.search(contrasena):
        raise PoliticaContrasenaError("La contrasena debe tener al menos una mayuscula")
    if not PATRON_DIGITO.search(contrasena):
        raise PoliticaContrasenaError("La contrasena debe tener al menos un numero")
    if not PATRON_ESPECIAL.search(contrasena):
        raise PoliticaContrasenaError("La contrasena debe tener al menos un caracter especial")
    if len(contrasena.encode("utf-8")) > LIMITE_BYTES_BCRYPT:
        raise PoliticaContrasenaError(
            f"La contrasena supera el limite de {LIMITE_BYTES_BCRYPT} bytes en UTF-8"
        )


def _validar_longitud(contrasena: str) -> bytes:
    contrasena_bytes = contrasena.encode("utf-8")
    if len(contrasena_bytes) > LIMITE_BYTES_BCRYPT:
        raise ContrasenaDemasiadoLargaError(
            f"La contrasena supera el limite de {LIMITE_BYTES_BCRYPT} bytes en UTF-8"
        )
    return contrasena_bytes


def hash_contrasena(contrasena: str) -> str:
    contrasena_bytes = _validar_longitud(contrasena)
    return bcrypt.hashpw(contrasena_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_contrasena(contrasena: str, hash_almacenado: str) -> bool:
    contrasena_bytes = _validar_longitud(contrasena)
    return bcrypt.checkpw(contrasena_bytes, hash_almacenado.encode("utf-8"))
