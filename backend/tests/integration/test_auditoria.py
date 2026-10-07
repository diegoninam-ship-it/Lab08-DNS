from app.modelos import Auditoria, Rol


def test_admin_puede_listar_auditoria(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)
    db.add(Auditoria(accion="LOGIN_OK", usuario_id=admin.id))
    db.commit()

    respuesta = cliente.get("/api/auditoria")

    assert respuesta.status_code == 200
    assert respuesta.json()["total"] >= 1


def test_auditor_puede_listar_auditoria(cliente, db, tienda, fabrica_usuario, autenticar):
    auditor = fabrica_usuario(tienda, Rol.AUDITOR)
    autenticar(auditor)

    respuesta = cliente.get("/api/auditoria")

    assert respuesta.status_code == 200


def test_gerente_y_empleado_no_pueden_ver_auditoria(cliente, db, tienda, fabrica_usuario, autenticar):
    for rol in (Rol.GERENTE, Rol.EMPLEADO):
        usuario = fabrica_usuario(tienda, rol)
        autenticar(usuario)

        respuesta = cliente.get("/api/auditoria")

        assert respuesta.status_code == 403


def test_auditoria_se_filtra_por_accion_y_usuario(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    otro = fabrica_usuario(tienda, Rol.EMPLEADO)
    db.add_all(
        [
            Auditoria(accion="LOGIN_OK", usuario_id=admin.id),
            Auditoria(accion="LOGIN_FALLIDO", usuario_id=otro.id),
        ]
    )
    db.commit()
    autenticar(admin)

    respuesta = cliente.get("/api/auditoria", params={"accion": "LOGIN_OK", "usuario_id": admin.id})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 1
    assert cuerpo["items"][0]["accion"] == "LOGIN_OK"


def test_auditoria_se_ordena_descendente(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    primero = Auditoria(accion="REGISTRO", usuario_id=admin.id)
    db.add(primero)
    db.commit()
    segundo = Auditoria(accion="LOGIN_OK", usuario_id=admin.id)
    db.add(segundo)
    db.commit()
    autenticar(admin)

    respuesta = cliente.get("/api/auditoria")

    assert respuesta.status_code == 200
    ids = [item["id"] for item in respuesta.json()["items"]]
    assert ids == sorted(ids, reverse=True)


def test_acceso_denegado_de_otros_endpoints_tambien_aparece_en_auditoria(cliente, db, tienda, fabrica_usuario, fabrica_producto, autenticar):
    producto = fabrica_producto(tienda)
    empleado = fabrica_usuario(tienda, Rol.EMPLEADO)
    autenticar(empleado)
    cliente.delete(f"/api/productos/{producto.id}", headers={"Content-Type": "application/json"})

    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)
    respuesta = cliente.get("/api/auditoria", params={"accion": "ACCESO_DENEGADO"})

    assert respuesta.status_code == 200
    assert respuesta.json()["total"] >= 1
