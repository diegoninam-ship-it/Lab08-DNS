from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

METODOS_QUE_MODIFICAN = {"POST", "PUT", "PATCH", "DELETE"}


class ExigirContentTypeJsonMiddleware(BaseHTTPMiddleware):
    """Defensa CSRF adicional: toda peticion que modifica datos exige
    Content-Type: application/json; si no, 415."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if request.method in METODOS_QUE_MODIFICAN:
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                return JSONResponse(
                    status_code=415,
                    content={"detail": "Content-Type debe ser application/json"},
                )
        return await call_next(request)
