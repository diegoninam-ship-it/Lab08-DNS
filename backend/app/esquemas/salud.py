from pydantic import BaseModel


class SaludSalida(BaseModel):
    estado: str
