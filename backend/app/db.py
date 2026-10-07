from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import obtener_configuracion


class Base(DeclarativeBase):
    pass


def crear_engine():
    configuracion = obtener_configuracion()
    return create_engine(configuracion.database_url, pool_pre_ping=True)


engine = crear_engine()
SesionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def obtener_db() -> Generator[Session, None, None]:
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()
