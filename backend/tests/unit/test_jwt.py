from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest

from app.seguridad.jwt import crear_token, decodificar_token


def test_crear_y_decodificar_token():
    ahora = datetime.now(timezone.utc)

    token = crear_token(usuario_id=7, token_version=2, ahora=ahora)
    payload = decodificar_token(token)

    assert payload["sub"] == "7"
    assert payload["ver"] == 2


def test_token_expirado_falla_al_decodificar():
    ahora = datetime.now(timezone.utc) - timedelta(days=1)

    token = crear_token(usuario_id=1, token_version=0, ahora=ahora)

    with pytest.raises(pyjwt.ExpiredSignatureError):
        decodificar_token(token)
