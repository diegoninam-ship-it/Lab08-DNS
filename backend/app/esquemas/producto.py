from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.esquemas.tienda import TiendaSalida


class ProductoCrearEntrada(BaseModel):
    tienda_id: int | None = None
    sku: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = None
    precio: Decimal
    stock: int = Field(ge=0)

    @field_validator("precio")
    @classmethod
    def _validar_precio(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("El precio no puede ser negativo")
        return v


class ProductoEditarEntrada(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = None
    precio: Decimal

    @field_validator("precio")
    @classmethod
    def _validar_precio(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("El precio no puede ser negativo")
        return v


class StockActualizarEntrada(BaseModel):
    stock: int = Field(ge=0)


class ProductoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    nombre: str
    descripcion: str | None
    precio: Decimal
    stock: int
    tienda: TiendaSalida
    actualizado_por: int | None
    creado_en: datetime
    actualizado_en: datetime

    @field_serializer("precio")
    def _serializar_precio(self, valor: Decimal) -> str:
        return f"{valor:.2f}"


class ListadoProductosSalida(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[ProductoSalida]
