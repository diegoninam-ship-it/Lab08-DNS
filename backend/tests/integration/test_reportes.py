from app.modelos import Rol


def test_admin_ve_reporte_de_todas_las_tiendas_sin_filtro(cliente, db, tienda, otra_tienda, fabrica_usuario, fabrica_producto, autenticar):
    fabrica_producto(tienda, precio="10.00", stock=4)
    fabrica_producto(otra_tienda, precio="20.00", stock=3)
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    respuesta = cliente.get("/api/reportes/inventario")

    assert respuesta.status_code == 200
    tiendas_en_reporte = {item["tienda"]["id"] for item in respuesta.json()}
    assert tiendas_en_reporte == {tienda.id, otra_tienda.id}


def test_reporte_calcula_totales_y_stock_bajo(cliente, db, tienda, fabrica_usuario, fabrica_producto, autenticar):
    fabrica_producto(tienda, sku="A", precio="10.00", stock=2)
    fabrica_producto(tienda, sku="B", precio="5.50", stock=20)
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    respuesta = cliente.get("/api/reportes/inventario", params={"tienda_id": tienda.id})

    assert respuesta.status_code == 200
    reporte = respuesta.json()[0]
    assert reporte["total_productos"] == 2
    assert reporte["total_unidades"] == 22
    assert reporte["valor_inventario"] == "130.00"
    assert [p["sku"] for p in reporte["stock_bajo"]] == ["A"]


def test_gerente_ve_solo_su_tienda_sin_parametro(cliente, db, tienda, otra_tienda, fabrica_usuario, fabrica_producto, autenticar):
    fabrica_producto(tienda)
    fabrica_producto(otra_tienda)
    gerente = fabrica_usuario(tienda, Rol.GERENTE)
    autenticar(gerente)

    respuesta = cliente.get("/api/reportes/inventario")

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["tienda"]["id"] == tienda.id


def test_gerente_no_puede_ver_reporte_de_otra_tienda(cliente, db, tienda, otra_tienda, fabrica_usuario, autenticar):
    gerente = fabrica_usuario(tienda, Rol.GERENTE)
    autenticar(gerente)

    respuesta = cliente.get("/api/reportes/inventario", params={"tienda_id": otra_tienda.id})

    assert respuesta.status_code == 403


def test_empleado_no_puede_ver_reportes(cliente, db, tienda, fabrica_usuario, autenticar):
    empleado = fabrica_usuario(tienda, Rol.EMPLEADO)
    autenticar(empleado)

    respuesta = cliente.get("/api/reportes/inventario")

    assert respuesta.status_code == 403


def test_auditor_puede_ver_reporte_de_todas_las_tiendas(cliente, db, tienda, otra_tienda, fabrica_usuario, fabrica_producto, autenticar):
    fabrica_producto(tienda)
    fabrica_producto(otra_tienda)
    auditor = fabrica_usuario(tienda, Rol.AUDITOR)
    autenticar(auditor)

    respuesta = cliente.get("/api/reportes/inventario")

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 2
