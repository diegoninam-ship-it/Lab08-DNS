import pytest

from app.seguridad.contrasenas import (
    ContrasenaDemasiadoLargaError,
    hash_contrasena,
    verificar_contrasena,
)


def test_hash_y_verificar_contrasena_correcta():
    hash_valor = hash_contrasena("Demo1234!")

    assert verificar_contrasena("Demo1234!", hash_valor)


def test_verificar_contrasena_incorrecta():
    hash_valor = hash_contrasena("Demo1234!")

    assert not verificar_contrasena("OtraClave1!", hash_valor)


def test_contrasena_mayor_a_72_bytes_en_utf8_falla():
    contrasena_larga = "a" * 73

    with pytest.raises(ContrasenaDemasiadoLargaError):
        hash_contrasena(contrasena_larga)
