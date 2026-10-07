import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.config import Configuracion


def _kwargs_validos(**sobreescrituras):
    base = {
        "database_url": "postgresql+psycopg://user:pass@localhost:5434/techstore",
        "jwt_secret": "x" * 32,
        "mfa_clave_cifrado": Fernet.generate_key().decode(),
    }
    base.update(sobreescrituras)
    return base


def test_configuracion_valida_se_construye():
    configuracion = Configuracion(**_kwargs_validos())

    assert configuracion.jwt_expira_minutos == 30
    assert configuracion.mfa_emisor == "TechStore"


def test_database_url_sin_driver_psycopg_falla():
    with pytest.raises(ValidationError):
        Configuracion(**_kwargs_validos(database_url="postgresql://user:pass@localhost/techstore"))


def test_test_database_url_sin_sufijo_test_falla():
    with pytest.raises(ValidationError):
        Configuracion(
            **_kwargs_validos(
                test_database_url="postgresql+psycopg://user:pass@localhost/techstore_otra"
            )
        )


def test_jwt_secret_corto_falla():
    with pytest.raises(ValidationError):
        Configuracion(**_kwargs_validos(jwt_secret="corto"))


def test_jwt_expira_minutos_fuera_de_rango_falla():
    with pytest.raises(ValidationError):
        Configuracion(**_kwargs_validos(jwt_expira_minutos=4))


def test_mfa_clave_cifrado_invalida_falla():
    with pytest.raises(ValidationError):
        Configuracion(**_kwargs_validos(mfa_clave_cifrado="no-es-una-clave-fernet"))


def test_stock_bajo_umbral_no_positivo_falla():
    with pytest.raises(ValidationError):
        Configuracion(**_kwargs_validos(stock_bajo_umbral=0))
