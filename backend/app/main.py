from fastapi import FastAPI

from app.config import obtener_configuracion
from app.routers import salud, tiendas


def create_app() -> FastAPI:
    obtener_configuracion()

    app = FastAPI(title="TechStore")

    app.include_router(salud.router, prefix="/api")
    app.include_router(tiendas.router, prefix="/api")

    return app


app = create_app()
