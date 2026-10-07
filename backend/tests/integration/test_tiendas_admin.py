from app.modelos import Rol, Tienda


def test_admin_crea_tienda(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    respuesta = cliente.post(
        "/api/tiendas",
        json={"nombre": "Cusco Centro", "ciudad": "Cusco"},
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["nombre"] == "Cusco Centro"


def test_no_admin_no_puede_crear_tienda(cliente, db, tienda, fabrica_usuario, autenticar):
    gerente = fabrica_usuario(tienda, Rol.GERENTE)
    autenticar(gerente)

    respuesta = cliente.post(
        "/api/tiendas",
        json={"nombre": "Otra Mas", "ciudad": "Ica"},
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 403


def test_crear_tienda_con_nombre_duplicado_devuelve_409(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    respuesta = cliente.post(
        "/api/tiendas",
        json={"nombre": tienda.nombre, "ciudad": "Otra ciudad"},
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 409


def test_admin_edita_tienda(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    respuesta = cliente.put(
        f"/api/tiendas/{tienda.id}",
        json={"nombre": "Nombre Editado", "ciudad": "Ciudad Editada"},
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Nombre Editado"


def test_editar_tienda_inexistente_devuelve_404(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    respuesta = cliente.put(
        "/api/tiendas/9999",
        json={"nombre": "X", "ciudad": "Y"},
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 404
