import pytest

from app.seguridad.contrasenas import (
    ContrasenaDemasiadoLargaError,
    PoliticaContrasenaError,
    hash_contrasena,
    validar_politica_contrasena,
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


def test_politica_acepta_contrasena_valida():
    validar_politica_contrasena("Demo1234!")


@pytest.mark.parametrize(
    "contrasena",
    [
        "Cort1!",
        "sinmayuscula1!",
        "SINMINUSCULANIUMERO!",
        "SINNUMERO!",
        "SinEspecial1",
    ],
)
def test_politica_rechaza_contrasenas_que_incumplen_alguna_regla(contrasena):
    with pytest.raises(PoliticaContrasenaError):
        validar_politica_contrasena(contrasena)


def test_politica_rechaza_contrasena_mayor_a_72_bytes():
    contrasena_larga = "Aa1!" + "x" * 70

    with pytest.raises(PoliticaContrasenaError):
        validar_politica_contrasena(contrasena_larga)
