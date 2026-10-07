from cryptography.fernet import Fernet

from app.config import obtener_configuracion


def cifrar(valor: str) -> str:
    configuracion = obtener_configuracion()
    fernet = Fernet(configuracion.mfa_clave_cifrado.encode())
    return fernet.encrypt(valor.encode()).decode()


def descifrar(valor_cifrado: str) -> str:
    configuracion = obtener_configuracion()
    fernet = Fernet(configuracion.mfa_clave_cifrado.encode())
    return fernet.decrypt(valor_cifrado.encode()).decode()
