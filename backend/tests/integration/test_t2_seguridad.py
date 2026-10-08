"""T2 (seccion 14.3): casos de seguridad que no quedaron explicitos en
D3/D4/T1 -- politica de contrasena, correo duplicado, bloqueo y mismo
mensaje de error ya se cubren en tests/integration/test_auth.py y
tests/unit/test_contrasenas.py; MFA (enrolamiento, codigo valido/
invalido/agotado/expirado/reutilizado) y OAuth simulado (correo no
verificado, cuenta inexistente, pendiente, vinculacion por correo,
state alterado/ausente/SameSite=Lax, proveedor sin configurar) ya se
cubren en esos mismos archivos y en test_oauth.py.

Este archivo agrega lo que faltaba para la cobertura exhaustiva que
pide T2: atributos exactos de la cookie de sesion, que el secreto MFA
quede cifrado en la base (no en claro), que el propio desafio MFA no
se pueda reutilizar tras verificarse con exito (mas alla del
anti-reuso del codigo TOTP), que el cambio de rol y la desactivacion
tengan efecto inmediato sin volver a iniciar sesion, que el
desbloqueo por ADMIN permita un login real a continuacion, y 415 sin
JSON en mas endpoints de escritura.
"""

import re
from datetime import datetime, timedelta, timezone

import pyotp
import pytest

from app.modelos import Estado, Rol
from app.seguridad.cifrado import descifrar


def _completar_login_con_mfa(cliente, db, usuario, reloj_falso, contrasena="Demo1234!"):
    respuesta_login = cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": contrasena})
    desafio_token = respuesta_login.json()["desafio_token"]

    db.refresh(usuario)
    secreto = descifrar(usuario.mfa_secreto_cifrado)
    codigo = pyotp.TOTP(secreto).at(reloj_falso.ahora().timestamp())

    return cliente.post("/api/auth/mfa/verificar", json={"desafio_token": desafio_token, "codigo": codigo})


# --- Cookie de sesion: HttpOnly, SameSite=Strict, Path ------------------


def test_cookie_sesion_tiene_httponly_samesite_strict_y_path_api(cliente, db, tienda, fabrica_usuario, reloj_falso):
    usuario = fabrica_usuario(tienda, Rol.EMPLEADO)

    respuesta = _completar_login_con_mfa(cliente, db, usuario, reloj_falso)

    assert respuesta.status_code == 200
    cookie_cruda = respuesta.headers["set-cookie"]

    assert cookie_cruda.startswith("techstore_token=")
    assert "HttpOnly" in cookie_cruda
    assert "samesite=strict" in cookie_cruda.lower()

    coincidencia_path = re.search(r"Path=([^;]+)", cookie_cruda)
    assert coincidencia_path is not None
    assert coincidencia_path.group(1) == "/api"


# --- Secreto MFA cifrado en la base --------------------------------------


def test_secreto_mfa_se_almacena_cifrado_no_en_claro(cliente, db, tienda, fabrica_usuario):
    usuario = fabrica_usuario(tienda, Rol.EMPLEADO)

    respuesta_login = cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"})
    otpauth_uri = respuesta_login.json()["otpauth_uri"]
    secreto_en_claro = otpauth_uri.split("secret=")[1].split("&")[0]

    db.refresh(usuario)
    valor_almacenado = usuario.mfa_secreto_cifrado

    assert valor_almacenado is not None
    assert valor_almacenado != secreto_en_claro
    assert secreto_en_claro not in valor_almacenado
    assert descifrar(valor_almacenado) == secreto_en_claro


# --- El desafio MFA no se reutiliza, aunque el codigo sea valido --------


def test_desafio_mfa_no_se_reutiliza_tras_verificarse_con_exito(cliente, db, tienda, fabrica_usuario, reloj_falso):
    usuario = fabrica_usuario(tienda, Rol.EMPLEADO)
    respuesta_login = cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"})
    desafio_token = respuesta_login.json()["desafio_token"]

    db.refresh(usuario)
    secreto = descifrar(usuario.mfa_secreto_cifrado)
    codigo = pyotp.TOTP(secreto).at(reloj_falso.ahora().timestamp())

    primera = cliente.post("/api/auth/mfa/verificar", json={"desafio_token": desafio_token, "codigo": codigo})
    assert primera.status_code == 200

    # Codigo nuevo y valido, pero el desafio ya fue consumido.
    reloj_falso.avanzar(seconds=30)
    codigo_siguiente = pyotp.TOTP(secreto).at(reloj_falso.ahora().timestamp())
    segunda = cliente.post(
        "/api/auth/mfa/verificar", json={"desafio_token": desafio_token, "codigo": codigo_siguiente}
    )

    assert segunda.status_code == 401


# --- Cambio de rol y desactivacion: efecto inmediato ----------------------


def test_desactivar_usuario_tiene_efecto_inmediato_sin_volver_a_loguearse(
    cliente, db, tienda, fabrica_usuario, reloj_falso
):
    usuario = fabrica_usuario(tienda, Rol.EMPLEADO)
    assert _completar_login_con_mfa(cliente, db, usuario, reloj_falso).status_code == 200
    assert cliente.get("/api/auth/me").status_code == 200

    usuario.estado = Estado.DESACTIVADO
    db.commit()

    assert cliente.get("/api/auth/me").status_code == 401


def test_cambio_de_rol_tiene_efecto_inmediato_sin_volver_a_loguearse(cliente, db, tienda, fabrica_usuario, reloj_falso):
    usuario = fabrica_usuario(tienda, Rol.EMPLEADO)
    assert _completar_login_con_mfa(cliente, db, usuario, reloj_falso).status_code == 200
    assert cliente.get("/api/auth/me").json()["rol"] == "EMPLEADO"

    usuario.rol = Rol.GERENTE
    db.commit()

    assert cliente.get("/api/auth/me").json()["rol"] == "GERENTE"


# --- Desbloqueo por ADMIN: permite un login real a continuacion --------


def test_desbloqueo_por_admin_permite_login_correcto_inmediatamente(cliente, db, tienda, fabrica_usuario, autenticar):
    bloqueado = fabrica_usuario(tienda, Rol.EMPLEADO, email="bloqueado-t2@test.pe")
    bloqueado.bloqueado_hasta = datetime.now(timezone.utc) + timedelta(minutes=15)
    bloqueado.intentos_fallidos = 5
    db.commit()

    respuesta_bloqueada = cliente.post(
        "/api/auth/login", json={"email": bloqueado.email, "contrasena": "Demo1234!"}
    )
    assert respuesta_bloqueada.status_code == 423

    admin = fabrica_usuario(tienda, Rol.ADMIN, email="admin-t2@test.pe")
    autenticar(admin)
    respuesta_desbloqueo = cliente.post(f"/api/usuarios/{bloqueado.id}/desbloquear", json={})
    assert respuesta_desbloqueo.status_code == 200

    cliente.cookies.delete("techstore_token")
    respuesta_login = cliente.post("/api/auth/login", json={"email": bloqueado.email, "contrasena": "Demo1234!"})

    assert respuesta_login.status_code == 200


# --- CSRF: 415 sin Content-Type: application/json en mas endpoints -----


@pytest.mark.parametrize(
    "metodo, ruta",
    [
        ("POST", "/api/auth/registro"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/logout"),
        ("POST", "/api/productos"),
    ],
)
def test_mutaciones_sin_content_type_json_devuelven_415(cliente, metodo, ruta):
    respuesta = cliente.request(metodo, ruta, content=b"{}", headers={"Content-Type": "text/plain"})

    assert respuesta.status_code == 415
