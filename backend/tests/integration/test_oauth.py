from sqlalchemy import func, select

import app.servicios.oauth_proveedores as oauth_proveedores
from app.modelos import Estado, IdentidadSocial, Proveedor, Rol, Usuario
from app.servicios.oauth_proveedores import IdentidadExterna, ProveedorOAuth


class ProveedorFalso(ProveedorOAuth):
    nombre = "google"

    def __init__(self, identidad: IdentidadExterna | None = None, codigo_esperado: str = "codigo-valido"):
        self.identidad = identidad
        self.codigo_esperado = codigo_esperado

    def construir_url_autorizacion(self, state: str, redirect_uri: str) -> str:
        return f"https://proveedor-falso.test/autorizar?state={state}"

    def obtener_identidad(self, code: str, redirect_uri: str) -> IdentidadExterna:
        assert code == self.codigo_esperado
        assert self.identidad is not None
        return self.identidad


def _simular_proveedor(monkeypatch, proveedor_falso: ProveedorOAuth):
    monkeypatch.setattr(oauth_proveedores, "obtener_proveedor", lambda nombre: proveedor_falso)


def _crear_usuario(db, tienda, email="social@test.pe", estado=Estado.ACTIVO, rol=Rol.EMPLEADO):
    from app.seguridad.contrasenas import hash_contrasena

    usuario = Usuario(
        email=email,
        nombre_completo="Usuario social",
        password_hash=hash_contrasena("Demo1234!"),
        tienda_id=tienda.id,
        rol=rol,
        estado=estado,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def _iniciar_login_social(cliente):
    respuesta = cliente.get("/api/auth/oauth/google/login", follow_redirects=False)
    assert respuesta.status_code == 302
    state = cliente.cookies.get("techstore_oauth_state")
    assert state is not None
    return state


def test_login_social_proveedor_no_configurado_devuelve_503(cliente, monkeypatch):
    # No depende de que el .env real tenga o no credenciales configuradas:
    # simula explicitamente la ausencia de configuracion para el proveedor.
    def _sin_configurar(nombre):
        raise oauth_proveedores.ProveedorOAuthNoConfiguradoError()

    monkeypatch.setattr(oauth_proveedores, "obtener_proveedor", _sin_configurar)

    respuesta = cliente.get("/api/auth/oauth/google/login", follow_redirects=False)

    assert respuesta.status_code == 503


def test_login_social_genera_cookie_state_lax_y_redirige_302(cliente, monkeypatch):
    _simular_proveedor(monkeypatch, ProveedorFalso())

    respuesta = cliente.get("/api/auth/oauth/google/login", follow_redirects=False)

    assert respuesta.status_code == 302
    assert respuesta.headers["location"].startswith("https://proveedor-falso.test/autorizar")
    cookie_cruda = respuesta.headers["set-cookie"]
    assert "techstore_oauth_state=" in cookie_cruda
    assert "SameSite=lax" in cookie_cruda or "samesite=lax" in cookie_cruda.lower()
    assert "HttpOnly" in cookie_cruda
    assert "Path=/api/auth/oauth" in cookie_cruda


def test_callback_sin_cookie_state_redirige_con_estado_invalido(cliente, monkeypatch):
    _simular_proveedor(monkeypatch, ProveedorFalso())

    respuesta = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": "cualquiera"},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert "error=estado_invalido" in respuesta.headers["location"]


def test_callback_con_state_alterado_redirige_con_estado_invalido(cliente, monkeypatch):
    _simular_proveedor(monkeypatch, ProveedorFalso())
    _iniciar_login_social(cliente)

    respuesta = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": "estado-alterado"},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert "error=estado_invalido" in respuesta.headers["location"]


def test_callback_correo_no_verificado_redirige_con_error(cliente, monkeypatch, db, tienda):
    _crear_usuario(db, tienda, email="noverificado@test.pe")
    identidad = IdentidadExterna(proveedor_uid="123", email="noverificado@test.pe", email_verificado=False)
    _simular_proveedor(monkeypatch, ProveedorFalso(identidad))
    state = _iniciar_login_social(cliente)

    respuesta = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": state},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert "error=correo_no_verificado" in respuesta.headers["location"]


def test_callback_cuenta_inexistente_redirige_con_no_registrado(cliente, monkeypatch):
    identidad = IdentidadExterna(proveedor_uid="999", email="nadie@test.pe", email_verificado=True)
    _simular_proveedor(monkeypatch, ProveedorFalso(identidad))
    state = _iniciar_login_social(cliente)

    respuesta = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": state},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert "error=no_registrado" in respuesta.headers["location"]


def test_callback_cuenta_pendiente_redirige_con_pendiente(cliente, monkeypatch, db, tienda):
    usuario = _crear_usuario(db, tienda, email="pendiente-social@test.pe", estado=Estado.PENDIENTE, rol=None)
    identidad = IdentidadExterna(proveedor_uid="111", email=usuario.email, email_verificado=True)
    _simular_proveedor(monkeypatch, ProveedorFalso(identidad))
    state = _iniciar_login_social(cliente)

    respuesta = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": state},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert "error=pendiente" in respuesta.headers["location"]


def test_callback_cuenta_desactivada_redirige_con_desactivada(cliente, monkeypatch, db, tienda):
    usuario = _crear_usuario(db, tienda, email="desactivado-social@test.pe", estado=Estado.DESACTIVADO)
    identidad = IdentidadExterna(proveedor_uid="222", email=usuario.email, email_verificado=True)
    _simular_proveedor(monkeypatch, ProveedorFalso(identidad))
    state = _iniciar_login_social(cliente)

    respuesta = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": state},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert "error=desactivada" in respuesta.headers["location"]


def test_callback_exitoso_por_correo_verificado_crea_vinculo_y_redirige_a_mfa(cliente, monkeypatch, db, tienda):
    usuario = _crear_usuario(db, tienda, email="vinculo@test.pe")
    identidad = IdentidadExterna(proveedor_uid="333", email=usuario.email, email_verificado=True)
    _simular_proveedor(monkeypatch, ProveedorFalso(identidad))
    state = _iniciar_login_social(cliente)

    respuesta = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": state},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    location = respuesta.headers["location"]
    assert location.startswith("http://localhost:8080/mfa#desafio=")

    vinculo = db.scalar(
        select(IdentidadSocial).where(
            IdentidadSocial.usuario_id == usuario.id,
            IdentidadSocial.proveedor == Proveedor.GOOGLE,
            IdentidadSocial.proveedor_uid == "333",
        )
    )
    assert vinculo is not None


def test_callback_resuelve_por_identidad_social_ya_vinculada_sin_duplicar(cliente, monkeypatch, db, tienda):
    usuario = _crear_usuario(db, tienda, email="ya-vinculado@test.pe")
    db.add(
        IdentidadSocial(
            usuario_id=usuario.id, proveedor=Proveedor.GOOGLE, proveedor_uid="444", email=usuario.email
        )
    )
    db.commit()

    identidad = IdentidadExterna(proveedor_uid="444", email="correo-distinto@test.pe", email_verificado=True)
    _simular_proveedor(monkeypatch, ProveedorFalso(identidad))
    state = _iniciar_login_social(cliente)

    respuesta = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": state},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert "/mfa#desafio=" in respuesta.headers["location"]

    total_vinculos = db.scalar(
        select(func.count())
        .select_from(IdentidadSocial)
        .where(IdentidadSocial.usuario_id == usuario.id, IdentidadSocial.proveedor == Proveedor.GOOGLE)
    )
    assert total_vinculos == 1


def test_cookie_state_es_de_un_solo_uso(cliente, monkeypatch, db, tienda):
    usuario = _crear_usuario(db, tienda, email="un-solo-uso@test.pe")
    identidad = IdentidadExterna(proveedor_uid="555", email=usuario.email, email_verificado=True)
    _simular_proveedor(monkeypatch, ProveedorFalso(identidad))
    state = _iniciar_login_social(cliente)

    primera = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": state},
        follow_redirects=False,
    )
    assert primera.status_code == 302
    assert "/mfa#desafio=" in primera.headers["location"]

    segunda = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": state},
        follow_redirects=False,
    )
    assert "error=estado_invalido" in segunda.headers["location"]


def test_callback_proveedor_desconfigurado_entre_login_y_callback_redirige_con_error(cliente, monkeypatch):
    _simular_proveedor(monkeypatch, ProveedorFalso())
    state = _iniciar_login_social(cliente)

    def _sin_configurar(nombre):
        raise oauth_proveedores.ProveedorOAuthNoConfiguradoError()

    monkeypatch.setattr(oauth_proveedores, "obtener_proveedor", _sin_configurar)

    respuesta = cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": state},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert "error=proveedor_no_configurado" in respuesta.headers["location"]
