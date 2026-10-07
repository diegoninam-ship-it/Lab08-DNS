from fastapi.testclient import TestClient

from app.modelos import Tienda


def test_listar_tiendas_vacio(app):
    cliente = TestClient(app)

    respuesta = cliente.get("/api/tiendas")

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_listar_tiendas_devuelve_las_creadas_ordenadas_por_nombre(app, db):
    db.add_all(
        [
            Tienda(nombre="Trujillo Plaza", ciudad="Trujillo"),
            Tienda(nombre="Arequipa Mall", ciudad="Arequipa"),
        ]
    )
    db.commit()

    cliente = TestClient(app)
    respuesta = cliente.get("/api/tiendas")

    assert respuesta.status_code == 200
    nombres = [tienda["nombre"] for tienda in respuesta.json()]
    assert nombres == ["Arequipa Mall", "Trujillo Plaza"]
