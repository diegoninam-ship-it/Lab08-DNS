from fastapi import APIRouter

from app.esquemas.salud import SaludSalida

router = APIRouter(tags=["salud"])


@router.get("/salud", response_model=SaludSalida)
def obtener_salud() -> SaludSalida:
    return SaludSalida(estado="ok")
