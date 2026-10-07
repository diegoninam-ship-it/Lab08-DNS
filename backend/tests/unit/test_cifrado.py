from app.seguridad.cifrado import cifrar, descifrar


def test_cifrar_y_descifrar_devuelve_el_valor_original():
    secreto = "ABCDEFGHIJKLMNOP"

    cifrado = cifrar(secreto)

    assert cifrado != secreto
    assert descifrar(cifrado) == secreto
