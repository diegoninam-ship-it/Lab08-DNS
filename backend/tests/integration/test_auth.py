import pyotp
import pytest
from sqlalchemy import select

from app.modelos import Estado, Rol, Usuario
from app.seguridad.cifrado import descifrar
from app.seguridad.contrasenas import hash_contrasena


def _crear_usuario_activo(db, tienda, email="usuario@test.pe", contrasena="Demo1234!", rol=Rol.EMPLEADO):
    usuario = Usuario(
        email=email,
        nombre_completo="Usuario de prueba",
        password_hash=hash_contrasena(contrasena),
        tienda_id=tienda.id,
        rol=rol,
        estado=Estado.ACTIVO,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def _codigo_valido(usuario, db, reloj_falso):
    db.refresh(usuario)
    secreto = descifrar(usuario.mfa_secreto_cifrado)
    return pyotp.TOTP(secreto).at(reloj_falso.ahora().timestamp())


# --- Registro -----------------------------------------------------------


def test_registro_exitoso_queda_pendiente_sin_rol(cliente, db, tienda):
    respuesta = cliente.post(
        "/api/auth/registro",
        json={
            "email": "Nuevo@Test.PE",
            "contrasena": "Demo1234!",
            "nombre_completo": "Nuevo Usuario",
            "tienda_id": tienda.id,
        },
    )

    assert respuesta.status_code == 201

    usuario = db.scalar(select(Usuario).where(Usuario.email == "nuevo@test.pe"))
    assert usuario is not None
    assert usuario.estado == Estado.PENDIENTE
    assert usuario.rol is None


def test_registro_correo_duplicado_devuelve_409(cliente, tienda):
    datos = {
        "email": "dup@test.pe",
        "contrasena": "Demo1234!",
        "nombre_completo": "Dup",
        "tienda_id": tienda.id,
    }
    cliente.post("/api/auth/registro", json=datos)

    respuesta = cliente.post("/api/auth/registro", json=datos)

    assert respuesta.status_code == 409


@pytest.mark.parametrize(
    "contrasena",
    [
        "Corta1!",
        "sinmayuscula1!",
        "SINNUMERO!",
        "SinEspecial1",
        "A1!" + "x" * 80,
    ],
)
def test_registro_contrasena_que_viola_la_politica_devuelve_422(cliente, tienda, contrasena):
    respuesta = cliente.post(
        "/api/auth/registro",
        json={
            "email": "politica@test.pe",
            "contrasena": contrasena,
            "nombre_completo": "Politica",
            "tienda_id": tienda.id,
        },
    )

    assert respuesta.status_code == 422


def test_registro_tienda_inexistente_devuelve_422(cliente):
    respuesta = cliente.post(
        "/api/auth/registro",
        json={
            "email": "sin-tienda@test.pe",
            "contrasena": "Demo1234!",
            "nombre_completo": "Sin Tienda",
            "tienda_id": 9999,
        },
    )

    assert respuesta.status_code == 422


# --- Login y bloqueo -----------------------------------------------------


def test_login_correo_inexistente_devuelve_401_mismo_mensaje_que_contrasena_incorrecta(cliente, db, tienda):
    usuario = _crear_usuario_activo(db, tienda)

    respuesta_inexistente = cliente.post(
        "/api/auth/login", json={"email": "no-existe@test.pe", "contrasena": "Demo1234!"}
    )
    respuesta_incorrecta = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "ClaveMala1!"}
    )

    assert respuesta_inexistente.status_code == 401
    assert respuesta_incorrecta.status_code == 401
    assert respuesta_inexistente.json()["detail"] == respuesta_incorrecta.json()["detail"]


def test_login_bloquea_cuenta_al_quinto_intento_fallido(cliente, db, tienda, reloj_falso):
    usuario = _crear_usuario_activo(db, tienda)

    for _ in range(5):
        respuesta = cliente.post(
            "/api/auth/login", json={"email": usuario.email, "contrasena": "ClaveMala1!"}
        )
        assert respuesta.status_code == 401

    respuesta_bloqueada = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )

    assert respuesta_bloqueada.status_code == 423


def test_login_se_desbloquea_automaticamente_tras_el_tiempo_configurado(cliente, db, tienda, reloj_falso):
    usuario = _crear_usuario_activo(db, tienda)
    for _ in range(5):
        cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "ClaveMala1!"})

    reloj_falso.avanzar(minutes=16)

    respuesta = cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"})

    assert respuesta.status_code == 200


def test_login_usuario_pendiente_devuelve_403(cliente, db, tienda):
    usuario = Usuario(
        email="pendiente@test.pe",
        nombre_completo="Pendiente",
        password_hash=hash_contrasena("Demo1234!"),
        tienda_id=tienda.id,
        rol=None,
        estado=Estado.PENDIENTE,
    )
    db.add(usuario)
    db.commit()

    respuesta = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )

    assert respuesta.status_code == 403


def test_login_usuario_desactivado_devuelve_403(cliente, db, tienda):
    usuario = _crear_usuario_activo(db, tienda)
    usuario.estado = Estado.DESACTIVADO
    db.commit()

    respuesta = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )

    assert respuesta.status_code == 403


# --- MFA -------------------------------------------------------------


def test_login_activo_sin_mfa_inicia_enrolamiento(cliente, db, tienda, reloj_falso):
    usuario = _crear_usuario_activo(db, tienda)

    respuesta = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["paso"] == "MFA_ENROLAMIENTO"
    assert cuerpo["otpauth_uri"].startswith("otpauth://totp/")
    assert "desafio_token" in cuerpo


def test_flujo_completo_enrolamiento_mfa_y_sesion(cliente, db, tienda, reloj_falso):
    usuario = _crear_usuario_activo(db, tienda)

    respuesta_login = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )
    desafio_token = respuesta_login.json()["desafio_token"]
    codigo = _codigo_valido(usuario, db, reloj_falso)

    respuesta_verificar = cliente.post(
        "/api/auth/mfa/verificar", json={"desafio_token": desafio_token, "codigo": codigo}
    )

    assert respuesta_verificar.status_code == 200
    assert "techstore_token" in respuesta_verificar.cookies

    db.refresh(usuario)
    assert usuario.mfa_activo is True

    respuesta_me = cliente.get("/api/auth/me")
    assert respuesta_me.status_code == 200
    assert respuesta_me.json()["email"] == usuario.email

    respuesta_logout = cliente.post("/api/auth/logout", json={})
    assert respuesta_logout.status_code == 204

    respuesta_me_tras_logout = cliente.get("/api/auth/me")
    assert respuesta_me_tras_logout.status_code == 401


def test_mfa_codigo_invalido_devuelve_intentos_restantes(cliente, db, tienda, reloj_falso):
    usuario = _crear_usuario_activo(db, tienda)
    respuesta_login = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )
    desafio_token = respuesta_login.json()["desafio_token"]

    respuesta = cliente.post(
        "/api/auth/mfa/verificar", json={"desafio_token": desafio_token, "codigo": "000000"}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["intentos_restantes"] == 2


def test_mfa_desafio_se_agota_tras_tres_intentos_fallidos(cliente, db, tienda, reloj_falso):
    usuario = _crear_usuario_activo(db, tienda)
    respuesta_login = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )
    desafio_token = respuesta_login.json()["desafio_token"]

    for _ in range(3):
        respuesta = cliente.post(
            "/api/auth/mfa/verificar", json={"desafio_token": desafio_token, "codigo": "000000"}
        )

    assert respuesta.status_code == 401
    assert "intentos_restantes" not in respuesta.json()

    codigo_valido = _codigo_valido(usuario, db, reloj_falso)
    respuesta_tras_agotado = cliente.post(
        "/api/auth/mfa/verificar", json={"desafio_token": desafio_token, "codigo": codigo_valido}
    )

    assert respuesta_tras_agotado.status_code == 401


def test_mfa_codigo_ya_usado_no_se_puede_reutilizar(cliente, db, tienda, reloj_falso):
    usuario = _crear_usuario_activo(db, tienda)
    respuesta_login = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )
    desafio_token = respuesta_login.json()["desafio_token"]
    codigo = _codigo_valido(usuario, db, reloj_falso)

    primera = cliente.post(
        "/api/auth/mfa/verificar", json={"desafio_token": desafio_token, "codigo": codigo}
    )
    assert primera.status_code == 200

    respuesta_login_2 = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )
    desafio_token_2 = respuesta_login_2.json()["desafio_token"]

    segunda = cliente.post(
        "/api/auth/mfa/verificar", json={"desafio_token": desafio_token_2, "codigo": codigo}
    )

    assert segunda.status_code == 401


def test_mfa_desafio_expirado_devuelve_401(cliente, db, tienda, reloj_falso):
    usuario = _crear_usuario_activo(db, tienda)
    respuesta_login = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )
    desafio_token = respuesta_login.json()["desafio_token"]
    codigo = _codigo_valido(usuario, db, reloj_falso)

    reloj_falso.avanzar(minutes=6)

    respuesta = cliente.post(
        "/api/auth/mfa/verificar", json={"desafio_token": desafio_token, "codigo": codigo}
    )

    assert respuesta.status_code == 401


def test_mfa_iniciar_devuelve_el_mismo_secreto_mientras_no_se_confirme(cliente, db, tienda, reloj_falso):
    usuario = _crear_usuario_activo(db, tienda)
    respuesta_login = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )
    desafio_token = respuesta_login.json()["desafio_token"]
    otpauth_uri_login = respuesta_login.json()["otpauth_uri"]

    respuesta_iniciar = cliente.post("/api/auth/mfa/iniciar", json={"desafio_token": desafio_token})

    assert respuesta_iniciar.status_code == 200
    assert respuesta_iniciar.json()["otpauth_uri"] == otpauth_uri_login


def test_mfa_iniciar_para_usuario_con_mfa_ya_activo_no_pide_enrolamiento(cliente, db, tienda, reloj_falso):
    usuario = _crear_usuario_activo(db, tienda)
    primer_login = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )
    codigo = _codigo_valido(usuario, db, reloj_falso)
    cliente.post(
        "/api/auth/mfa/verificar",
        json={"desafio_token": primer_login.json()["desafio_token"], "codigo": codigo},
    )

    segundo_login = cliente.post(
        "/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"}
    )
    assert segundo_login.json()["paso"] == "MFA_REQUERIDO"

    respuesta_iniciar = cliente.post(
        "/api/auth/mfa/iniciar", json={"desafio_token": segundo_login.json()["desafio_token"]}
    )

    assert respuesta_iniciar.status_code == 200
    assert respuesta_iniciar.json() == {"paso": "MFA_REQUERIDO"}


# --- CSRF por Content-Type -------------------------------------------


def test_post_sin_content_type_json_devuelve_415(cliente):
    respuesta = cliente.post(
        "/api/auth/login",
        content=b'{"email": "a@test.pe", "contrasena": "Demo1234!"}',
        headers={"Content-Type": "text/plain"},
    )

    assert respuesta.status_code == 415
