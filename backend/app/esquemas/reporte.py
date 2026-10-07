from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer

from app.esquemas.producto import ProductoSalida
from app.esquemas.tienda import TiendaSalida


class ReporteInventarioTienda(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tienda: TiendaSalida
    total_productos: int
    total_unidades: int
    valor_inventario: Decimal
    stock_bajo: list[ProductoSalida]

    @field_serializer("valor_inventario")
    def _serializar_valor(self, valor: Decimal) -> str:
        return f"{valor:.2f}"
