from pydantic import BaseModel, ConfigDict


class TiendaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    ciudad: str
