"""T3 (seccion 14.3): cada accion de la seccion 10 deja su registro de
auditoria (incluidos los 403), ningun registro contiene secretos, y los
reportes calculan valores correctos con el alcance por rol correcto.

Los calculos de totales/stock_bajo y el alcance por rol de los reportes
ya se prueban en tests/integration/test_reportes.py; aqui se agrega el
caso de una tienda sin productos. ACCESO_DENEGADO ya se prueba en
tests/integration/test_productos.py; aqui se enumeran sistematicamente
el resto de las acciones de la seccion 10 para confirmar que cada una
efectivamente escribe su fila, con el valor exacto de `accion`.
"""

from datetime import datetime, timedelta, timezone

import pyotp
from sqlalchemy import select

import app.servicios.oauth_proveedores as oauth_proveedores
from app.modelos import Auditoria, Estado, Rol, Usuario
from app.seguridad.cifrado import cifrar, descifrar
from app.seguridad.contrasenas import hash_contrasena
from app.seguridad.mfa import generar_secreto
from app.servicios.oauth_proveedores import IdentidadExterna
from tests.integration.test_oauth import ProveedorFalso, _iniciar_login_social


def _ultima_auditoria(db, accion, usuario_id=None):
    consulta = select(Auditoria).where(Auditoria.accion == accion)
    if usuario_id is not None:
        consulta = consulta.where(Auditoria.usuario_id == usuario_id)
    consulta = consulta.order_by(Auditoria.id.desc())
    return db.scalar(consulta)


def _crear_usuario_con_mfa_activo(db, tienda, rol=Rol.EMPLEADO, email="con-mfa-t3@test.pe"):
    secreto = generar_secreto()
    usuario = Usuario(
        email=email,
        nombre_completo="Con MFA",
        password_hash=hash_contrasena("Demo1234!"),
        tienda_id=tienda.id,
        rol=rol,
        estado=Estado.ACTIVO,
        mfa_secreto_cifrado=cifrar(secreto),
        mfa_activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario, secreto


# --- Autenticacion: cada accion de la seccion 10 deja su registro ------


def test_registro_deja_auditoria(cliente, db, tienda):
    cliente.post(
        "/api/auth/registro",
        json={"email": "aud-registro@test.pe", "contrasena": "Demo1234!", "nombre_completo": "X", "tienda_id": tienda.id},
    )

    usuario = db.scalar(select(Usuario).where(Usuario.email == "aud-registro@test.pe"))
    assert _ultima_auditoria(db, "REGISTRO", usuario.id) is not None


def test_login_ok_deja_auditoria(cliente, db, tienda, reloj_falso):
    usuario, secreto = _crear_usuario_con_mfa_activo(db, tienda, email="aud-login-ok@test.pe")
    respuesta_login = cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"})
    codigo = pyotp.TOTP(secreto).at(reloj_falso.ahora().timestamp())
    cliente.post(
        "/api/auth/mfa/verificar",
        json={"desafio_token": respuesta_login.json()["desafio_token"], "codigo": codigo},
    )

    assert _ultima_auditoria(db, "LOGIN_OK", usuario.id) is not None


def test_login_fallido_deja_auditoria(cliente, db, tienda):
    usuario, _secreto = _crear_usuario_con_mfa_activo(db, tienda, email="aud-login-fallido@test.pe")
    cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "ClaveMala1!"})

    assert _ultima_auditoria(db, "LOGIN_FALLIDO", usuario.id) is not None


def test_cuenta_bloqueada_deja_auditoria(cliente, db, tienda):
    usuario, _secreto = _crear_usuario_con_mfa_activo(db, tienda, email="aud-bloqueo@test.pe")
    for _ in range(5):
        cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "ClaveMala1!"})

    assert _ultima_auditoria(db, "CUENTA_BLOQUEADA", usuario.id) is not None


def test_login_rechazado_deja_auditoria_con_motivo(cliente, db, tienda):
    usuario = Usuario(
        email="aud-pendiente@test.pe",
        nombre_completo="Pendiente",
        password_hash=hash_contrasena("Demo1234!"),
        tienda_id=tienda.id,
        rol=None,
        estado=Estado.PENDIENTE,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"})

    registro = _ultima_auditoria(db, "LOGIN_RECHAZADO", usuario.id)
    assert registro is not None
    assert "motivo" in registro.detalle


def test_mfa_enrolado_deja_auditoria(cliente, db, tienda, fabrica_usuario, reloj_falso):
    usuario = fabrica_usuario(tienda, Rol.EMPLEADO)
    respuesta_login = cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"})
    db.refresh(usuario)
    secreto = descifrar(usuario.mfa_secreto_cifrado)
    codigo = pyotp.TOTP(secreto).at(reloj_falso.ahora().timestamp())

    cliente.post(
        "/api/auth/mfa/verificar",
        json={"desafio_token": respuesta_login.json()["desafio_token"], "codigo": codigo},
    )

    assert _ultima_auditoria(db, "MFA_ENROLADO", usuario.id) is not None


def test_mfa_fallido_deja_auditoria(cliente, db, tienda, fabrica_usuario):
    usuario = fabrica_usuario(tienda, Rol.EMPLEADO)
    respuesta_login = cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"})

    cliente.post(
        "/api/auth/mfa/verificar",
        json={"desafio_token": respuesta_login.json()["desafio_token"], "codigo": "000000"},
    )

    assert _ultima_auditoria(db, "MFA_FALLIDO", usuario.id) is not None


def test_mfa_desafio_agotado_deja_auditoria(cliente, db, tienda, fabrica_usuario):
    usuario = fabrica_usuario(tienda, Rol.EMPLEADO)
    respuesta_login = cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"})
    desafio_token = respuesta_login.json()["desafio_token"]

    for _ in range(3):
        cliente.post("/api/auth/mfa/verificar", json={"desafio_token": desafio_token, "codigo": "000000"})

    assert _ultima_auditoria(db, "MFA_DESAFIO_AGOTADO", usuario.id) is not None


def test_logout_deja_auditoria(cliente, db, tienda, reloj_falso):
    usuario, secreto = _crear_usuario_con_mfa_activo(db, tienda, email="aud-logout@test.pe")
    respuesta_login = cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "Demo1234!"})
    codigo = pyotp.TOTP(secreto).at(reloj_falso.ahora().timestamp())
    cliente.post(
        "/api/auth/mfa/verificar",
        json={"desafio_token": respuesta_login.json()["desafio_token"], "codigo": codigo},
    )

    cliente.post("/api/auth/logout", json={})

    assert _ultima_auditoria(db, "LOGOUT", usuario.id) is not None


# --- Productos ------------------------------------------------------------


def test_stock_actualizado_deja_auditoria_con_antes_despues(
    cliente, db, tienda, fabrica_usuario, fabrica_producto, autenticar
):
    producto = fabrica_producto(tienda, stock=10)
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    cliente.patch(f"/api/productos/{producto.id}/stock", json={"stock": 50})

    registro = _ultima_auditoria(db, "STOCK_ACTUALIZADO")
    assert registro is not None
    assert registro.detalle == {"antes": 10, "despues": 50}


def test_producto_eliminado_deja_auditoria_con_snapshot(
    cliente, db, tienda, fabrica_usuario, fabrica_producto, autenticar
):
    producto = fabrica_producto(tienda, sku="AUD-DEL")
    producto_id = producto.id
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    cliente.delete(f"/api/productos/{producto_id}", headers={"Content-Type": "application/json"})

    registro = _ultima_auditoria(db, "PRODUCTO_ELIMINADO")
    assert registro is not None
    assert registro.recurso_id == str(producto_id)
    assert registro.detalle["antes"]["sku"] == "AUD-DEL"


# --- Administracion ---------------------------------------------------


def test_usuario_actualizado_deja_auditoria(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    objetivo = fabrica_usuario(tienda, None, estado=Estado.PENDIENTE, email="aud-usuario-actualizado@test.pe")
    autenticar(admin)

    cliente.patch(
        f"/api/usuarios/{objetivo.id}",
        json={"estado": "ACTIVO", "rol": "EMPLEADO"},
        headers={"Content-Type": "application/json"},
    )

    registro = _ultima_auditoria(db, "USUARIO_ACTUALIZADO")
    assert registro is not None
    assert registro.detalle["despues"] == {"estado": "ACTIVO", "rol": "EMPLEADO", "tienda_id": tienda.id}


def test_usuario_desbloqueado_deja_auditoria(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    objetivo = fabrica_usuario(tienda, Rol.EMPLEADO, email="aud-desbloqueo@test.pe")
    autenticar(admin)

    cliente.post(f"/api/usuarios/{objetivo.id}/desbloquear", json={})

    assert _ultima_auditoria(db, "USUARIO_DESBLOQUEADO") is not None


def test_mfa_restablecido_deja_auditoria(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    objetivo = fabrica_usuario(tienda, Rol.EMPLEADO, email="aud-mfa-reset@test.pe")
    autenticar(admin)

    cliente.post(f"/api/usuarios/{objetivo.id}/mfa/restablecer", json={})

    assert _ultima_auditoria(db, "MFA_RESTABLECIDO") is not None


def test_tienda_creada_deja_auditoria(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    cliente.post("/api/tiendas", json={"nombre": "Tienda Auditada", "ciudad": "X"}, headers={"Content-Type": "application/json"})

    assert _ultima_auditoria(db, "TIENDA_CREADA") is not None


def test_tienda_editada_deja_auditoria(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    cliente.put(
        f"/api/tiendas/{tienda.id}",
        json={"nombre": "Tienda Editada T3", "ciudad": tienda.ciudad},
        headers={"Content-Type": "application/json"},
    )

    registro = _ultima_auditoria(db, "TIENDA_EDITADA")
    assert registro is not None
    assert registro.detalle["despues"]["nombre"] == "Tienda Editada T3"


def test_acceso_denegado_deja_auditoria(cliente, db, tienda, fabrica_usuario, fabrica_producto, autenticar):
    producto = fabrica_producto(tienda)
    empleado = fabrica_usuario(tienda, Rol.EMPLEADO)
    autenticar(empleado)

    cliente.delete(f"/api/productos/{producto.id}", headers={"Content-Type": "application/json"})

    assert _ultima_auditoria(db, "ACCESO_DENEGADO", empleado.id) is not None


def test_login_social_rechazado_deja_auditoria(cliente, db, tienda, monkeypatch):
    identidad = IdentidadExterna(proveedor_uid="t3-999", email="no-registrado-t3@test.pe", email_verificado=True)
    monkeypatch.setattr(oauth_proveedores, "obtener_proveedor", lambda nombre: ProveedorFalso(identidad))
    state = _iniciar_login_social(cliente)

    cliente.get(
        "/api/auth/oauth/google/callback",
        params={"code": "codigo-valido", "state": state},
        follow_redirects=False,
    )

    registro = _ultima_auditoria(db, "LOGIN_SOCIAL_RECHAZADO")
    assert registro is not None
    assert registro.detalle["motivo"] == "no_registrado"


# --- Ningun registro contiene secretos ------------------------------------


def test_ningun_registro_de_auditoria_contiene_secretos(cliente, db, tienda):
    contrasena = "SecretoNoDebeAparecer1!"
    codigo_incorrecto = "000000"

    cliente.post(
        "/api/auth/registro",
        json={"email": "sin-secretos@test.pe", "contrasena": contrasena, "nombre_completo": "X", "tienda_id": tienda.id},
    )
    usuario = db.scalar(select(Usuario).where(Usuario.email == "sin-secretos@test.pe"))
    usuario.estado = Estado.ACTIVO
    usuario.rol = Rol.EMPLEADO
    db.commit()

    cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": "OtraClaveMala1!"})
    respuesta_login = cliente.post("/api/auth/login", json={"email": usuario.email, "contrasena": contrasena})
    cliente.post(
        "/api/auth/mfa/verificar",
        json={"desafio_token": respuesta_login.json()["desafio_token"], "codigo": codigo_incorrecto},
    )

    registros = db.scalars(select(Auditoria)).all()
    assert len(registros) > 0

    hash_contrasena_usuario = usuario.password_hash
    for registro in registros:
        contenido_detalle = str(registro.detalle) if registro.detalle else ""
        assert contrasena not in contenido_detalle
        assert codigo_incorrecto not in contenido_detalle
        assert hash_contrasena_usuario not in contenido_detalle

        for campo in (registro.email_intentado, registro.ip, registro.recurso, registro.recurso_id):
            if campo:
                assert contrasena not in campo
                assert codigo_incorrecto not in campo
                assert hash_contrasena_usuario not in campo


# --- Reportes: caso adicional de calculo (alcance por rol ya cubierto) --


def test_reporte_inventario_tienda_sin_productos_devuelve_ceros(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    respuesta = cliente.get("/api/reportes/inventario", params={"tienda_id": tienda.id})

    assert respuesta.status_code == 200
    reporte = respuesta.json()[0]
    assert reporte["total_productos"] == 0
    assert reporte["total_unidades"] == 0
    assert reporte["valor_inventario"] == "0.00"
    assert reporte["stock_bajo"] == []
