"""T1 (seccion 14.3): cada endpoint de las secciones 9.2-9.4, parametrizado
por rol y por ambito (tienda propia/ajena), verificando que la matriz de
la seccion 4.2 se cumple exactamente. Incluye los casos explicitos del
enunciado: Empleado cambiando precio por PUT -> 403; Gerente eliminando
de otra tienda -> 403; Auditor escribiendo -> 403; usuario pendiente con
JWT forjado -> 401.
"""

from datetime import datetime, timezone

import pytest

from app.modelos import Estado, Rol, Usuario
from app.seguridad.contrasenas import hash_contrasena
from app.seguridad.jwt import crear_token

ROLES = [Rol.ADMIN, Rol.GERENTE, Rol.EMPLEADO, Rol.AUDITOR]


def _autenticar_como(fabrica_usuario, autenticar, tienda, rol):
    usuario = fabrica_usuario(tienda, rol)
    autenticar(usuario)
    return usuario


# --- 9.2 Productos: lectura, abierta a los 4 roles en cualquier tienda --


@pytest.mark.parametrize("rol", ROLES)
def test_matriz_listar_productos(cliente, db, tienda, fabrica_usuario, fabrica_producto, autenticar, rol):
    fabrica_producto(tienda)
    _autenticar_como(fabrica_usuario, autenticar, tienda, rol)

    assert cliente.get("/api/productos").status_code == 200


@pytest.mark.parametrize("rol", ROLES)
def test_matriz_obtener_producto(cliente, db, tienda, fabrica_usuario, fabrica_producto, autenticar, rol):
    producto = fabrica_producto(tienda)
    _autenticar_como(fabrica_usuario, autenticar, tienda, rol)

    assert cliente.get(f"/api/productos/{producto.id}").status_code == 200


# --- 9.2 Productos: creacion ---------------------------------------------


@pytest.mark.parametrize(
    "rol, status_esperado",
    [(Rol.ADMIN, 201), (Rol.GERENTE, 201), (Rol.EMPLEADO, 403), (Rol.AUDITOR, 403)],
)
def test_matriz_crear_producto(cliente, db, tienda, fabrica_usuario, autenticar, rol, status_esperado):
    _autenticar_como(fabrica_usuario, autenticar, tienda, rol)

    respuesta = cliente.post(
        "/api/productos",
        json={
            "tienda_id": tienda.id,
            "sku": f"MTX-CREAR-{rol.value}",
            "nombre": "Producto matriz",
            "precio": "1.00",
            "stock": 1,
        },
    )

    assert respuesta.status_code == status_esperado


# --- 9.2 Productos: edicion (incluye sku/nombre/descripcion/precio) -----


@pytest.mark.parametrize(
    "rol, ambito, status_esperado",
    [
        (Rol.ADMIN, "propia", 200),
        (Rol.ADMIN, "ajena", 200),
        (Rol.GERENTE, "propia", 200),
        (Rol.GERENTE, "ajena", 403),
        (Rol.EMPLEADO, "propia", 403),
        (Rol.EMPLEADO, "ajena", 403),
        (Rol.AUDITOR, "propia", 403),
        (Rol.AUDITOR, "ajena", 403),
    ],
)
def test_matriz_editar_producto(
    cliente, db, tienda, otra_tienda, fabrica_usuario, fabrica_producto, autenticar, rol, ambito, status_esperado
):
    tienda_producto = tienda if ambito == "propia" else otra_tienda
    producto = fabrica_producto(tienda_producto, precio="50.00")
    _autenticar_como(fabrica_usuario, autenticar, tienda, rol)

    respuesta = cliente.put(
        f"/api/productos/{producto.id}",
        json={"sku": producto.sku, "nombre": producto.nombre, "precio": "999.00"},
    )

    assert respuesta.status_code == status_esperado
    if status_esperado == 403:
        db.refresh(producto)
        assert str(producto.precio) == "50.00"


def test_matriz_empleado_no_cambia_precio_por_put(cliente, db, tienda, fabrica_usuario, fabrica_producto, autenticar):
    """Caso explicito del enunciado T1: Empleado cambiando precio por PUT -> 403."""
    producto = fabrica_producto(tienda, precio="50.00")
    _autenticar_como(fabrica_usuario, autenticar, tienda, Rol.EMPLEADO)

    respuesta = cliente.put(
        f"/api/productos/{producto.id}",
        json={"sku": producto.sku, "nombre": producto.nombre, "precio": "999.00"},
    )

    assert respuesta.status_code == 403


# --- 9.2 Productos: actualizar stock -------------------------------------


@pytest.mark.parametrize(
    "rol, ambito, status_esperado",
    [
        (Rol.ADMIN, "propia", 200),
        (Rol.ADMIN, "ajena", 200),
        (Rol.GERENTE, "propia", 200),
        (Rol.GERENTE, "ajena", 403),
        (Rol.EMPLEADO, "propia", 200),
        (Rol.EMPLEADO, "ajena", 403),
        (Rol.AUDITOR, "propia", 403),
        (Rol.AUDITOR, "ajena", 403),
    ],
)
def test_matriz_actualizar_stock(
    cliente, db, tienda, otra_tienda, fabrica_usuario, fabrica_producto, autenticar, rol, ambito, status_esperado
):
    tienda_producto = tienda if ambito == "propia" else otra_tienda
    producto = fabrica_producto(tienda_producto, stock=10)
    _autenticar_como(fabrica_usuario, autenticar, tienda, rol)

    respuesta = cliente.patch(f"/api/productos/{producto.id}/stock", json={"stock": 999})

    assert respuesta.status_code == status_esperado
    if status_esperado == 403:
        db.refresh(producto)
        assert producto.stock == 10


# --- 9.2 Productos: eliminacion ------------------------------------------


@pytest.mark.parametrize(
    "rol, ambito, status_esperado",
    [
        (Rol.ADMIN, "propia", 204),
        (Rol.ADMIN, "ajena", 204),
        (Rol.GERENTE, "propia", 204),
        (Rol.GERENTE, "ajena", 403),
        (Rol.EMPLEADO, "propia", 403),
        (Rol.EMPLEADO, "ajena", 403),
        (Rol.AUDITOR, "propia", 403),
        (Rol.AUDITOR, "ajena", 403),
    ],
)
def test_matriz_eliminar_producto(
    cliente, db, tienda, otra_tienda, fabrica_usuario, fabrica_producto, autenticar, rol, ambito, status_esperado
):
    tienda_producto = tienda if ambito == "propia" else otra_tienda
    producto = fabrica_producto(tienda_producto)
    _autenticar_como(fabrica_usuario, autenticar, tienda, rol)

    respuesta = cliente.delete(f"/api/productos/{producto.id}", headers={"Content-Type": "application/json"})

    assert respuesta.status_code == status_esperado
    if status_esperado == 403:
        from sqlalchemy import select

        from app.modelos import Producto

        assert db.scalar(select(Producto).where(Producto.id == producto.id)) is not None


def test_matriz_gerente_no_elimina_producto_de_otra_tienda(
    cliente, db, tienda, otra_tienda, fabrica_usuario, fabrica_producto, autenticar
):
    """Caso explicito del enunciado T1: Gerente eliminando de otra tienda -> 403."""
    producto = fabrica_producto(otra_tienda)
    _autenticar_como(fabrica_usuario, autenticar, tienda, Rol.GERENTE)

    respuesta = cliente.delete(f"/api/productos/{producto.id}", headers={"Content-Type": "application/json"})

    assert respuesta.status_code == 403


# --- 9.3 Reportes de inventario ------------------------------------------


@pytest.mark.parametrize(
    "rol, ambito, status_esperado",
    [
        (Rol.ADMIN, "propia", 200),
        (Rol.ADMIN, "ajena", 200),
        (Rol.ADMIN, "todas", 200),
        (Rol.AUDITOR, "propia", 200),
        (Rol.AUDITOR, "ajena", 200),
        (Rol.AUDITOR, "todas", 200),
        (Rol.GERENTE, "propia", 200),
        (Rol.GERENTE, "ajena", 403),
        (Rol.GERENTE, "todas", 200),  # sin parametro -> por defecto, la suya
        (Rol.EMPLEADO, "propia", 403),
        (Rol.EMPLEADO, "ajena", 403),
        (Rol.EMPLEADO, "todas", 403),
    ],
)
def test_matriz_reporte_inventario(
    cliente, db, tienda, otra_tienda, fabrica_usuario, autenticar, rol, ambito, status_esperado
):
    _autenticar_como(fabrica_usuario, autenticar, tienda, rol)

    if ambito == "propia":
        parametros = {"tienda_id": tienda.id}
    elif ambito == "ajena":
        parametros = {"tienda_id": otra_tienda.id}
    else:
        parametros = {}

    respuesta = cliente.get("/api/reportes/inventario", params=parametros)

    assert respuesta.status_code == status_esperado


# --- 9.3 Bitacora de auditoria --------------------------------------------


@pytest.mark.parametrize(
    "rol, status_esperado",
    [(Rol.ADMIN, 200), (Rol.AUDITOR, 200), (Rol.GERENTE, 403), (Rol.EMPLEADO, 403)],
)
def test_matriz_auditoria(cliente, db, tienda, fabrica_usuario, autenticar, rol, status_esperado):
    _autenticar_como(fabrica_usuario, autenticar, tienda, rol)

    assert cliente.get("/api/auditoria").status_code == status_esperado


# --- 9.4 Administracion: solo ADMIN ---------------------------------------


ACCIONES_ADMIN = [
    "listar_usuarios",
    "patch_usuario",
    "desbloquear",
    "restablecer_mfa",
    "crear_tienda",
    "editar_tienda",
]


@pytest.mark.parametrize("accion", ACCIONES_ADMIN)
@pytest.mark.parametrize("rol", ROLES)
def test_matriz_administracion_solo_admin(cliente, db, tienda, fabrica_usuario, autenticar, rol, accion):
    objetivo = fabrica_usuario(tienda, Rol.EMPLEADO, email=f"obj-{accion}-{rol.value}@test.pe")
    actor = fabrica_usuario(tienda, rol, email=f"act-{accion}-{rol.value}@test.pe")
    autenticar(actor)

    if accion == "listar_usuarios":
        respuesta = cliente.get("/api/usuarios")
    elif accion == "patch_usuario":
        respuesta = cliente.patch(f"/api/usuarios/{objetivo.id}", json={"estado": "DESACTIVADO"})
    elif accion == "desbloquear":
        respuesta = cliente.post(f"/api/usuarios/{objetivo.id}/desbloquear", json={})
    elif accion == "restablecer_mfa":
        respuesta = cliente.post(f"/api/usuarios/{objetivo.id}/mfa/restablecer", json={})
    elif accion == "crear_tienda":
        respuesta = cliente.post("/api/tiendas", json={"nombre": f"Tienda {accion}-{rol.value}", "ciudad": "X"})
    else:  # editar_tienda
        respuesta = cliente.put(f"/api/tiendas/{tienda.id}", json={"nombre": tienda.nombre, "ciudad": tienda.ciudad})

    if rol == Rol.ADMIN:
        assert respuesta.status_code in (200, 201)
    else:
        assert respuesta.status_code == 403, f"{accion} con rol {rol.value} debio devolver 403"


def test_matriz_auditor_escribiendo_es_siempre_403(cliente, db, tienda, fabrica_usuario, fabrica_producto, autenticar):
    """Caso explicito del enunciado T1: Auditor escribiendo -> 403 (en cualquier endpoint de escritura)."""
    producto = fabrica_producto(tienda)
    auditor = _autenticar_como(fabrica_usuario, autenticar, tienda, Rol.AUDITOR)

    respuestas = [
        cliente.post(
            "/api/productos",
            json={"tienda_id": tienda.id, "sku": "AUD-ESCRIBE", "nombre": "X", "precio": "1.00", "stock": 1},
        ),
        cliente.put(f"/api/productos/{producto.id}", json={"sku": producto.sku, "nombre": "X", "precio": "1.00"}),
        cliente.patch(f"/api/productos/{producto.id}/stock", json={"stock": 1}),
        cliente.delete(f"/api/productos/{producto.id}", headers={"Content-Type": "application/json"}),
        cliente.post("/api/tiendas", json={"nombre": "Tienda Auditor", "ciudad": "X"}),
    ]

    assert all(r.status_code == 403 for r in respuestas)
    assert auditor.rol == Rol.AUDITOR


# --- Usuario pendiente con JWT forjado: 401 en cualquier endpoint -------


@pytest.mark.parametrize(
    "metodo, ruta",
    [
        ("GET", "/api/productos"),
        ("GET", "/api/reportes/inventario"),
        ("GET", "/api/auditoria"),
        ("GET", "/api/usuarios"),
    ],
)
def test_matriz_usuario_pendiente_con_jwt_forjado_devuelve_401(cliente, db, tienda, metodo, ruta):
    usuario = Usuario(
        email=f"forjado-{ruta.strip('/').replace('/', '-')}@test.pe",
        nombre_completo="Forjado",
        password_hash=hash_contrasena("Demo1234!"),
        tienda_id=tienda.id,
        rol=None,
        estado=Estado.PENDIENTE,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    token = crear_token(usuario.id, usuario.token_version, datetime.now(timezone.utc))
    cliente.cookies.set("techstore_token", token)

    respuesta = cliente.request(metodo, ruta)

    assert respuesta.status_code == 401
