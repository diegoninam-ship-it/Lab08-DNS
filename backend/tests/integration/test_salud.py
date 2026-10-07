from fastapi.testclient import TestClient


def test_salud_responde_ok(app):
    cliente = TestClient(app)

    respuesta = cliente.get("/api/salud")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}
