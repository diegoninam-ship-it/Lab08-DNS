import bcrypt

LIMITE_BYTES_BCRYPT = 72


class ContrasenaDemasiadoLargaError(ValueError):
    pass


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
