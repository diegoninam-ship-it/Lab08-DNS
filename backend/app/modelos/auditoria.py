from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    email_intentado: Mapped[str | None] = mapped_column(String(254), nullable=True)
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    recurso: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recurso_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detalle: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
