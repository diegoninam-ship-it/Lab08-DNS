from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.modelos.enums import Estado, Rol


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "estado = 'PENDIENTE' OR rol IS NOT NULL",
            name="ck_usuarios_rol_si_no_pendiente",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    tienda_id: Mapped[int] = mapped_column(ForeignKey("tiendas.id"), nullable=False)
    rol: Mapped[Rol | None] = mapped_column(Enum(Rol, name="rol_usuario"), nullable=True)
    estado: Mapped[Estado] = mapped_column(
        Enum(Estado, name="estado_usuario"), nullable=False, server_default=Estado.PENDIENTE.value
    )
    intentos_fallidos: Mapped[int] = mapped_column(nullable=False, server_default="0")
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mfa_secreto_cifrado: Mapped[str | None] = mapped_column(nullable=True)
    mfa_activo: Mapped[bool] = mapped_column(nullable=False, server_default="false")
    mfa_ultimo_contador: Mapped[int | None] = mapped_column(nullable=True)
    token_version: Mapped[int] = mapped_column(nullable=False, server_default="0")
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tienda: Mapped["Tienda"] = relationship(back_populates="usuarios")
    identidades_sociales: Mapped[list["IdentidadSocial"]] = relationship(back_populates="usuario")
