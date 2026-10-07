import enum


class Rol(str, enum.Enum):
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    EMPLEADO = "EMPLEADO"
    AUDITOR = "AUDITOR"


class Estado(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    ACTIVO = "ACTIVO"
    DESACTIVADO = "DESACTIVADO"


class Proveedor(str, enum.Enum):
    GOOGLE = "google"
    GITHUB = "github"
