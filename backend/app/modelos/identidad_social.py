from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.modelos.enums import Proveedor


class IdentidadSocial(Base):
    __tablename__ = "identidades_sociales"
    __table_args__ = (
        UniqueConstraint("proveedor", "proveedor_uid", name="uq_identidad_social_proveedor_uid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    proveedor: Mapped[Proveedor] = mapped_column(Enum(Proveedor, name="proveedor_social"), nullable=False)
    proveedor_uid: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="identidades_sociales")
