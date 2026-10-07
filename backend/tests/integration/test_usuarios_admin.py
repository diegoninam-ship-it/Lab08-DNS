from app.modelos import Estado, Rol


def test_admin_lista_usuarios_filtrando_por_estado(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    fabrica_usuario(tienda, None, estado=Estado.PENDIENTE, email="pendiente@test.pe")
    autenticar(admin)

    respuesta = cliente.get("/api/usuarios", params={"estado": "PENDIENTE"})

    assert respuesta.status_code == 200
    correos = [u["email"] for u in respuesta.json()]
    assert "pendiente@test.pe" in correos
    assert all(u["estado"] == "PENDIENTE" for u in respuesta.json())


def test_no_admin_no_puede_listar_usuarios(cliente, db, tienda, fabrica_usuario, autenticar):
    gerente = fabrica_usuario(tienda, Rol.GERENTE)
    autenticar(gerente)

    respuesta = cliente.get("/api/usuarios")

    assert respuesta.status_code == 403


def test_admin_activa_usuario_pendiente_asignando_rol(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    pendiente = fabrica_usuario(tienda, None, estado=Estado.PENDIENTE, email="activar@test.pe")
    autenticar(admin)

    respuesta = cliente.patch(
        f"/api/usuarios/{pendiente.id}",
        json={"estado": "ACTIVO", "rol": "EMPLEADO"},
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ACTIVO"
    assert respuesta.json()["rol"] == "EMPLEADO"


def test_activar_sin_rol_asignado_devuelve_422(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    pendiente = fabrica_usuario(tienda, None, estado=Estado.PENDIENTE, email="sinrol@test.pe")
    autenticar(admin)

    respuesta = cliente.patch(
        f"/api/usuarios/{pendiente.id}",
        json={"estado": "ACTIVO"},
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 422


def test_admin_no_puede_modificarse_a_si_mismo(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    respuesta = cliente.patch(
        f"/api/usuarios/{admin.id}",
        json={"estado": "DESACTIVADO"},
        headers={"Content-Type": "application/json"},
    )

    assert respuesta.status_code == 409


def test_desbloquear_usuario_limpia_bloqueo_e_intentos(cliente, db, tienda, fabrica_usuario, autenticar):
    from datetime import datetime, timedelta, timezone

    admin = fabrica_usuario(tienda, Rol.ADMIN)
    bloqueado = fabrica_usuario(tienda, Rol.EMPLEADO, email="bloqueado@test.pe")
    bloqueado.bloqueado_hasta = datetime.now(timezone.utc) + timedelta(minutes=15)
    bloqueado.intentos_fallidos = 5
    db.commit()
    autenticar(admin)

    respuesta = cliente.post(
        f"/api/usuarios/{bloqueado.id}/desbloquear", json={}, headers={"Content-Type": "application/json"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["bloqueado_hasta"] is None
    db.refresh(bloqueado)
    assert bloqueado.intentos_fallidos == 0


def test_restablecer_mfa_borra_secreto_y_sube_token_version(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    con_mfa = fabrica_usuario(tienda, Rol.EMPLEADO, email="con-mfa@test.pe")
    con_mfa.mfa_secreto_cifrado = "cualquier-cosa-cifrada"
    con_mfa.mfa_activo = True
    db.commit()
    version_anterior = con_mfa.token_version
    autenticar(admin)

    respuesta = cliente.post(
        f"/api/usuarios/{con_mfa.id}/mfa/restablecer", json={}, headers={"Content-Type": "application/json"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["mfa_activo"] is False
    db.refresh(con_mfa)
    assert con_mfa.mfa_secreto_cifrado is None
    assert con_mfa.token_version == version_anterior + 1


def test_no_admin_no_puede_desbloquear_ni_restablecer_mfa(cliente, db, tienda, fabrica_usuario, autenticar):
    gerente = fabrica_usuario(tienda, Rol.GERENTE)
    objetivo = fabrica_usuario(tienda, Rol.EMPLEADO, email="objetivo@test.pe")
    autenticar(gerente)

    respuesta_desbloqueo = cliente.post(
        f"/api/usuarios/{objetivo.id}/desbloquear", json={}, headers={"Content-Type": "application/json"}
    )
    respuesta_mfa = cliente.post(
        f"/api/usuarios/{objetivo.id}/mfa/restablecer", json={}, headers={"Content-Type": "application/json"}
    )

    assert respuesta_desbloqueo.status_code == 403
    assert respuesta_mfa.status_code == 403


def test_actualizar_usuario_inexistente_devuelve_404(cliente, db, tienda, fabrica_usuario, autenticar):
    admin = fabrica_usuario(tienda, Rol.ADMIN)
    autenticar(admin)

    respuesta = cliente.patch(
        "/api/usuarios/9999", json={"estado": "DESACTIVADO"}, headers={"Content-Type": "application/json"}
    )

    assert respuesta.status_code == 404
