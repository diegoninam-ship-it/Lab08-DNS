from pydantic import BaseModel, ConfigDict, Field


class TiendaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    ciudad: str


class TiendaCrearEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    ciudad: str = Field(min_length=1, max_length=120)


class TiendaEditarEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    ciudad: str = Field(min_length=1, max_length=120)
