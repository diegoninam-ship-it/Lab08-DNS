import abc
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config import obtener_configuracion


@dataclass
class IdentidadExterna:
    proveedor_uid: str
    email: str
    email_verificado: bool


class ProveedorOAuthNoConfiguradoError(Exception):
    pass


class ProveedorOAuth(abc.ABC):
    nombre: str

    @abc.abstractmethod
    def construir_url_autorizacion(self, state: str, redirect_uri: str) -> str: ...

    @abc.abstractmethod
    def obtener_identidad(self, code: str, redirect_uri: str) -> IdentidadExterna: ...


class GoogleOAuthProveedor(ProveedorOAuth):
    nombre = "google"

    URL_AUTORIZACION = "https://accounts.google.com/o/oauth2/v2/auth"
    URL_TOKEN = "https://oauth2.googleapis.com/token"
    URL_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"
    SCOPES = "openid email profile"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret

    def construir_url_autorizacion(self, state: str, redirect_uri: str) -> str:
        parametros = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.SCOPES,
            "state": state,
        }
        return f"{self.URL_AUTORIZACION}?{urlencode(parametros)}"

    def obtener_identidad(self, code: str, redirect_uri: str) -> IdentidadExterna:
        with httpx.Client(timeout=10) as cliente:
            respuesta_token = cliente.post(
                self.URL_TOKEN,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            respuesta_token.raise_for_status()
            access_token = respuesta_token.json()["access_token"]

            respuesta_usuario = cliente.get(
                self.URL_USERINFO, headers={"Authorization": f"Bearer {access_token}"}
            )
            respuesta_usuario.raise_for_status()
            datos = respuesta_usuario.json()

        return IdentidadExterna(
            proveedor_uid=str(datos["sub"]),
            email=datos["email"],
            email_verificado=bool(datos.get("email_verified", False)),
        )


class GithubOAuthProveedor(ProveedorOAuth):
    nombre = "github"

    URL_AUTORIZACION = "https://github.com/login/oauth/authorize"
    URL_TOKEN = "https://github.com/login/oauth/access_token"  # noqa: S105
    URL_USUARIO = "https://api.github.com/user"
    URL_EMAILS = "https://api.github.com/user/emails"
    SCOPES = "read:user user:email"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret

    def construir_url_autorizacion(self, state: str, redirect_uri: str) -> str:
        parametros = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": self.SCOPES,
            "state": state,
        }
        return f"{self.URL_AUTORIZACION}?{urlencode(parametros)}"

    def obtener_identidad(self, code: str, redirect_uri: str) -> IdentidadExterna:
        encabezados = {"Accept": "application/json"}
        with httpx.Client(timeout=10, headers=encabezados) as cliente:
            respuesta_token = cliente.post(
                self.URL_TOKEN,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri,
                },
            )
            respuesta_token.raise_for_status()
            access_token = respuesta_token.json()["access_token"]

            encabezados_autorizados = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            }
            usuario = cliente.get(self.URL_USUARIO, headers=encabezados_autorizados).json()
            correos = cliente.get(self.URL_EMAILS, headers=encabezados_autorizados).json()

        correo_principal = next(
            (correo for correo in correos if correo.get("primary") and correo.get("verified")),
            None,
        )

        return IdentidadExterna(
            proveedor_uid=str(usuario["id"]),
            email=(correo_principal["email"] if correo_principal else usuario.get("email")) or "",
            email_verificado=correo_principal is not None,
        )


def obtener_proveedor(nombre: str) -> ProveedorOAuth:
    configuracion = obtener_configuracion()

    if nombre == "google":
        if not configuracion.google_client_id or not configuracion.google_client_secret:
            raise ProveedorOAuthNoConfiguradoError()
        return GoogleOAuthProveedor(configuracion.google_client_id, configuracion.google_client_secret)

    if nombre == "github":
        if not configuracion.github_client_id or not configuracion.github_client_secret:
            raise ProveedorOAuthNoConfiguradoError()
        return GithubOAuthProveedor(configuracion.github_client_id, configuracion.github_client_secret)

    raise ValueError(f"Proveedor desconocido: {nombre}")
