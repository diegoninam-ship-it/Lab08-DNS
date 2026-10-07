from fastapi import FastAPI

from app.config import obtener_configuracion
from app.routers import auth, oauth, productos, salud, tiendas
from app.seguridad.csrf import ExigirContentTypeJsonMiddleware


def create_app() -> FastAPI:
    obtener_configuracion()

    app = FastAPI(title="TechStore")
    app.add_middleware(ExigirContentTypeJsonMiddleware)

    app.include_router(salud.router, prefix="/api")
    app.include_router(tiendas.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(oauth.router, prefix="/api")
    app.include_router(productos.router, prefix="/api")

    return app


app = create_app()
