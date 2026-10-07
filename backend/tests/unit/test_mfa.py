from datetime import datetime, timedelta, timezone

import pyotp

from app.seguridad.mfa import generar_secreto, verificar_codigo

AHORA = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_codigo_valido_sin_uso_previo_se_acepta():
    secreto = generar_secreto()
    codigo = pyotp.TOTP(secreto).at(AHORA.timestamp())

    contador = verificar_codigo(secreto, codigo, None, AHORA)

    assert contador is not None


def test_codigo_invalido_se_rechaza():
    secreto = generar_secreto()

    contador = verificar_codigo(secreto, "000000", None, AHORA)

    assert contador is None


def test_codigo_ya_usado_no_se_puede_reutilizar():
    secreto = generar_secreto()
    codigo = pyotp.TOTP(secreto).at(AHORA.timestamp())
    contador_usado = verificar_codigo(secreto, codigo, None, AHORA)

    contador_repetido = verificar_codigo(secreto, codigo, contador_usado, AHORA)

    assert contador_repetido is None


def test_codigo_dentro_de_la_ventana_de_30_segundos_se_acepta():
    secreto = generar_secreto()
    momento_anterior = AHORA - timedelta(seconds=25)
    codigo = pyotp.TOTP(secreto).at(momento_anterior.timestamp())

    contador = verificar_codigo(secreto, codigo, None, AHORA)

    assert contador is not None
