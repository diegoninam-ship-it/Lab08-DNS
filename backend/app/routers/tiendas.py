from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import obtener_db
from app.esquemas.tienda import TiendaSalida
from app.modelos import Tienda

router = APIRouter(tags=["tiendas"])


@router.get("/tiendas", response_model=list[TiendaSalida])
def listar_tiendas(db: Session = Depends(obtener_db)) -> list[Tienda]:
    return list(db.scalars(select(Tienda).order_by(Tienda.nombre)))
