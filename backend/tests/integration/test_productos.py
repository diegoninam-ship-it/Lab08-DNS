from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.modelos import Auditoria, Estado, Producto, Rol, Tienda, Usuario
from app.seguridad.contrasenas import hash_contrasena
from app.seguridad.jwt import crear_token


def _crear_usuario(db, tienda, rol, email=None):
    email = email or f"{rol.value.lower()}-{tienda.id}@test.pe"
    usuario = Usuario(
        email=email,
        nombre_completo=f"Usuario {rol.value}",
        password_hash=hash_contrasena("Demo1234!"),
        tienda_id=tienda.id,
        rol=rol,
        estado=Estado.ACTIVO,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def _autenticar(cliente, usuario):
    token = crear_token(usuario.id, usuario.token_version, datetime.now(timezone.utc))
    cliente.cookies.set("techstore_token", token)


def _crear_producto(db, tienda, sku="SKU-1", nombre="Producto", precio="100.00", stock=10):
    producto = Producto(
        tienda_id=tienda.id,
        sku=sku,
        nombre=nombre,
        descripcion="Descripcion",
        precio=Decimal(precio),
        stock=stock,
    )
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def _otra_tienda(db):
    tienda = Tienda(nombre="Otra Tienda", ciudad="Arequipa")
    db.add(tienda)
    db.commit()
    db.refresh(tienda)
    return tienda


# --- Listado y lectura (todos los roles) --------------------------------


def test_listar_productos_accesible_para_todos_los_roles(cliente, db, tienda):
    _crear_producto(db, tienda)
    for rol in (Rol.ADMIN, Rol.GERENTE, Rol.EMPLEADO, Rol.AUDITOR):
        usuario = _crear_usuario(db, tienda, rol)
        _autenticar(cliente, usuario)

        respuesta = cliente.get("/api/productos")

        assert respuesta.status_code == 200
        assert respuesta.json()["total"] >= 1


def test_listar_productos_filtra_por_tienda_y_busqueda(cliente, db, tienda):
    otra = _otra_tienda(db)
    _crear_producto(db, tienda, sku="LAP-1", nombre="Laptop Pro")
    _crear_producto(db, otra, sku="MOU-1", nombre="Mouse")
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    respuesta = cliente.get("/api/productos", params={"tienda_id": tienda.id})
    assert respuesta.status_code == 200
    assert all(item["tienda"]["id"] == tienda.id for item in respuesta.json()["items"])

    respuesta_q = cliente.get("/api/productos", params={"q": "laptop"})
    assert respuesta_q.status_code == 200
    assert any(item["sku"] == "LAP-1" for item in respuesta_q.json()["items"])


def test_precio_se_devuelve_como_texto_con_dos_decimales(cliente, db, tienda):
    producto = _crear_producto(db, tienda, precio="749.5")
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    respuesta = cliente.get(f"/api/productos/{producto.id}")

    assert respuesta.status_code == 200
    assert respuesta.json()["precio"] == "749.50"


def test_obtener_producto_inexistente_devuelve_404(cliente, db, tienda):
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    respuesta = cliente.get("/api/productos/9999")

    assert respuesta.status_code == 404


# --- Creacion -------------------------------------------------------------


def test_admin_crea_producto_en_cualquier_tienda(cliente, db, tienda):
    otra = _otra_tienda(db)
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    respuesta = cliente.post(
        "/api/productos",
        json={"tienda_id": otra.id, "sku": "NEW-1", "nombre": "Nuevo", "precio": "10.00", "stock": 5},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["tienda"]["id"] == otra.id


def test_gerente_crea_producto_forzado_a_su_propia_tienda(cliente, db, tienda):
    otra = _otra_tienda(db)
    gerente = _crear_usuario(db, tienda, Rol.GERENTE)
    _autenticar(cliente, gerente)

    respuesta = cliente.post(
        "/api/productos",
        json={"tienda_id": otra.id, "sku": "NEW-2", "nombre": "Nuevo", "precio": "10.00", "stock": 5},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["tienda"]["id"] == tienda.id


def test_empleado_y_auditor_no_pueden_crear_productos(cliente, db, tienda):
    for rol in (Rol.EMPLEADO, Rol.AUDITOR):
        usuario = _crear_usuario(db, tienda, rol)
        _autenticar(cliente, usuario)

        respuesta = cliente.post(
            "/api/productos",
            json={"tienda_id": tienda.id, "sku": f"X-{rol.value}", "nombre": "X", "precio": "1.00", "stock": 1},
        )

        assert respuesta.status_code == 403


def test_crear_producto_con_sku_duplicado_en_la_misma_tienda_devuelve_409(cliente, db, tienda):
    _crear_producto(db, tienda, sku="DUP-1")
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    respuesta = cliente.post(
        "/api/productos",
        json={"tienda_id": tienda.id, "sku": "DUP-1", "nombre": "Otro", "precio": "1.00", "stock": 1},
    )

    assert respuesta.status_code == 409


def test_crear_producto_con_tienda_inexistente_devuelve_422(cliente, db, tienda):
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    respuesta = cliente.post(
        "/api/productos",
        json={"tienda_id": 9999, "sku": "X-1", "nombre": "X", "precio": "1.00", "stock": 1},
    )

    assert respuesta.status_code == 422


# --- Edicion (sku, nombre, descripcion, precio) ---------------------------


def test_admin_edita_producto_de_cualquier_tienda(cliente, db, tienda):
    producto = _crear_producto(db, tienda)
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    respuesta = cliente.put(
        f"/api/productos/{producto.id}",
        json={"sku": producto.sku, "nombre": "Editado", "precio": "200.00"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Editado"
    assert respuesta.json()["precio"] == "200.00"


def test_gerente_no_puede_editar_producto_de_otra_tienda(cliente, db, tienda):
    otra = _otra_tienda(db)
    producto = _crear_producto(db, otra)
    gerente = _crear_usuario(db, tienda, Rol.GERENTE)
    _autenticar(cliente, gerente)

    respuesta = cliente.put(
        f"/api/productos/{producto.id}",
        json={"sku": producto.sku, "nombre": "Hackeado", "precio": "1.00"},
    )

    assert respuesta.status_code == 403


def test_empleado_no_puede_cambiar_precio_por_put(cliente, db, tienda):
    producto = _crear_producto(db, tienda, precio="50.00")
    empleado = _crear_usuario(db, tienda, Rol.EMPLEADO)
    _autenticar(cliente, empleado)

    respuesta = cliente.put(
        f"/api/productos/{producto.id}",
        json={"sku": producto.sku, "nombre": producto.nombre, "precio": "999.00"},
    )

    assert respuesta.status_code == 403
    db.refresh(producto)
    assert str(producto.precio) == "50.00"


def test_auditor_no_puede_editar_productos(cliente, db, tienda):
    producto = _crear_producto(db, tienda)
    auditor = _crear_usuario(db, tienda, Rol.AUDITOR)
    _autenticar(cliente, auditor)

    respuesta = cliente.put(
        f"/api/productos/{producto.id}",
        json={"sku": producto.sku, "nombre": "X", "precio": "1.00"},
    )

    assert respuesta.status_code == 403


def test_editar_producto_inexistente_devuelve_404(cliente, db, tienda):
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    respuesta = cliente.put(
        "/api/productos/9999", json={"sku": "X", "nombre": "X", "precio": "1.00"}
    )

    assert respuesta.status_code == 404


# --- Stock ------------------------------------------------------------


def test_empleado_puede_actualizar_stock_de_su_tienda(cliente, db, tienda):
    producto = _crear_producto(db, tienda, stock=5)
    empleado = _crear_usuario(db, tienda, Rol.EMPLEADO)
    _autenticar(cliente, empleado)

    respuesta = cliente.patch(f"/api/productos/{producto.id}/stock", json={"stock": 42})

    assert respuesta.status_code == 200
    assert respuesta.json()["stock"] == 42


def test_empleado_no_puede_actualizar_stock_de_otra_tienda(cliente, db, tienda):
    otra = _otra_tienda(db)
    producto = _crear_producto(db, otra, stock=5)
    empleado = _crear_usuario(db, tienda, Rol.EMPLEADO)
    _autenticar(cliente, empleado)

    respuesta = cliente.patch(f"/api/productos/{producto.id}/stock", json={"stock": 42})

    assert respuesta.status_code == 403


def test_auditor_no_puede_actualizar_stock(cliente, db, tienda):
    producto = _crear_producto(db, tienda)
    auditor = _crear_usuario(db, tienda, Rol.AUDITOR)
    _autenticar(cliente, auditor)

    respuesta = cliente.patch(f"/api/productos/{producto.id}/stock", json={"stock": 1})

    assert respuesta.status_code == 403


def test_gerente_puede_actualizar_stock_de_su_tienda(cliente, db, tienda):
    producto = _crear_producto(db, tienda, stock=5)
    gerente = _crear_usuario(db, tienda, Rol.GERENTE)
    _autenticar(cliente, gerente)

    respuesta = cliente.patch(f"/api/productos/{producto.id}/stock", json={"stock": 7})

    assert respuesta.status_code == 200
    assert respuesta.json()["stock"] == 7


# --- Eliminacion --------------------------------------------------------


def test_gerente_elimina_producto_de_su_tienda(cliente, db, tienda):
    producto = _crear_producto(db, tienda)
    gerente = _crear_usuario(db, tienda, Rol.GERENTE)
    _autenticar(cliente, gerente)

    respuesta = cliente.delete(f"/api/productos/{producto.id}", headers={"Content-Type": "application/json"})

    assert respuesta.status_code == 204
    restante = db.scalar(select(Producto).where(Producto.id == producto.id))
    assert restante is None


def test_gerente_no_puede_eliminar_producto_de_otra_tienda(cliente, db, tienda):
    otra = _otra_tienda(db)
    producto = _crear_producto(db, otra)
    gerente = _crear_usuario(db, tienda, Rol.GERENTE)
    _autenticar(cliente, gerente)

    respuesta = cliente.delete(f"/api/productos/{producto.id}", headers={"Content-Type": "application/json"})

    assert respuesta.status_code == 403
    assert db.get(Producto, producto.id) is not None


def test_empleado_y_auditor_no_pueden_eliminar(cliente, db, tienda):
    for rol in (Rol.EMPLEADO, Rol.AUDITOR):
        producto = _crear_producto(db, tienda, sku=f"DEL-{rol.value}")
        usuario = _crear_usuario(db, tienda, rol, email=f"del-{rol.value}@test.pe")
        _autenticar(cliente, usuario)

        respuesta = cliente.delete(f"/api/productos/{producto.id}", headers={"Content-Type": "application/json"})

        assert respuesta.status_code == 403


def test_eliminar_producto_inexistente_devuelve_404(cliente, db, tienda):
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    respuesta = cliente.delete("/api/productos/9999", headers={"Content-Type": "application/json"})

    assert respuesta.status_code == 404


# --- Auditoria ----------------------------------------------------------


def test_creacion_de_producto_queda_registrada_en_auditoria(cliente, db, tienda):
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    respuesta = cliente.post(
        "/api/productos",
        json={"tienda_id": tienda.id, "sku": "AUD-1", "nombre": "Auditado", "precio": "5.00", "stock": 1},
    )
    producto_id = respuesta.json()["id"]

    registro = db.scalar(
        select(Auditoria).where(Auditoria.accion == "PRODUCTO_CREADO", Auditoria.recurso_id == str(producto_id))
    )
    assert registro is not None
    assert registro.detalle["despues"]["sku"] == "AUD-1"


def test_acceso_denegado_queda_registrado_en_auditoria(cliente, db, tienda):
    producto = _crear_producto(db, tienda)
    empleado = _crear_usuario(db, tienda, Rol.EMPLEADO)
    _autenticar(cliente, empleado)

    respuesta = cliente.delete(f"/api/productos/{producto.id}", headers={"Content-Type": "application/json"})
    assert respuesta.status_code == 403

    registro = db.scalar(
        select(Auditoria).where(Auditoria.accion == "ACCESO_DENEGADO", Auditoria.usuario_id == empleado.id)
    )
    assert registro is not None


def test_edicion_de_producto_registra_antes_y_despues_con_precio(cliente, db, tienda):
    producto = _crear_producto(db, tienda, precio="30.00")
    admin = _crear_usuario(db, tienda, Rol.ADMIN)
    _autenticar(cliente, admin)

    cliente.put(
        f"/api/productos/{producto.id}",
        json={"sku": producto.sku, "nombre": producto.nombre, "precio": "99.00"},
    )

    registro = db.scalar(
        select(Auditoria).where(Auditoria.accion == "PRODUCTO_EDITADO", Auditoria.recurso_id == str(producto.id))
    )
    assert registro is not None
    assert registro.detalle["antes"]["precio"] == "30.00"
    assert registro.detalle["despues"]["precio"] == "99.00"


# --- Autenticacion defensiva ---------------------------------------------


def test_usuario_pendiente_con_jwt_forjado_devuelve_401(cliente, db, tienda):
    usuario = Usuario(
        email="forjado@test.pe",
        nombre_completo="Forjado",
        password_hash=hash_contrasena("Demo1234!"),
        tienda_id=tienda.id,
        rol=None,
        estado=Estado.PENDIENTE,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    _autenticar(cliente, usuario)

    respuesta = cliente.get("/api/productos")

    assert respuesta.status_code == 401
