from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SesionLocal
from app.modelos import Estado, Producto, Rol, Tienda, Usuario
from app.seguridad.contrasenas import hash_contrasena

CONTRASENA_SEMILLA = "Demo1234!"

TIENDAS_SEMILLA = [
    {"nombre": "Lima Centro", "ciudad": "Lima"},
    {"nombre": "Arequipa Mall", "ciudad": "Arequipa"},
    {"nombre": "Trujillo Plaza", "ciudad": "Trujillo"},
]

USUARIOS_SEMILLA = [
    {"email": "admin@techstore.pe", "rol": Rol.ADMIN, "tienda": "Lima Centro", "estado": Estado.ACTIVO},
    {"email": "gerente.lima@techstore.pe", "rol": Rol.GERENTE, "tienda": "Lima Centro", "estado": Estado.ACTIVO},
    {
        "email": "gerente.arequipa@techstore.pe",
        "rol": Rol.GERENTE,
        "tienda": "Arequipa Mall",
        "estado": Estado.ACTIVO,
    },
    {
        "email": "empleado.lima@techstore.pe",
        "rol": Rol.EMPLEADO,
        "tienda": "Lima Centro",
        "estado": Estado.ACTIVO,
    },
    {
        "email": "empleado.arequipa@techstore.pe",
        "rol": Rol.EMPLEADO,
        "tienda": "Arequipa Mall",
        "estado": Estado.ACTIVO,
    },
    {"email": "auditor@techstore.pe", "rol": Rol.AUDITOR, "tienda": "Lima Centro", "estado": Estado.ACTIVO},
    {"email": "pendiente@techstore.pe", "rol": None, "tienda": "Trujillo Plaza", "estado": Estado.PENDIENTE},
]

NOMBRE_COMPLETO_POR_EMAIL = {
    "admin@techstore.pe": "Administradora TechStore",
    "gerente.lima@techstore.pe": "Gerente Lima Centro",
    "gerente.arequipa@techstore.pe": "Gerente Arequipa Mall",
    "empleado.lima@techstore.pe": "Empleado Lima Centro",
    "empleado.arequipa@techstore.pe": "Empleado Arequipa Mall",
    "auditor@techstore.pe": "Auditora TechStore",
    "pendiente@techstore.pe": "Usuario Pendiente",
}

# 4 productos por tienda, al menos 2 con stock bajo (<= STOCK_BAJO_UMBRAL por defecto: 5).
PRODUCTOS_SEMILLA_POR_TIENDA = [
    {"sku": "LAP-001", "nombre": "Laptop 14\"", "descripcion": "Laptop ultradelgada", "precio": "2999.00", "stock": 12},
    {"sku": "MOU-001", "nombre": "Mouse inalambrico", "descripcion": "Mouse optico", "precio": "59.90", "stock": 3},
    {"sku": "TEC-001", "nombre": "Teclado mecanico", "descripcion": "Teclado retroiluminado", "precio": "189.90", "stock": 2},
    {"sku": "MON-001", "nombre": "Monitor 24\"", "descripcion": "Monitor Full HD", "precio": "749.00", "stock": 8},
]


def sembrar_tiendas(db: Session) -> dict[str, Tienda]:
    tiendas_por_nombre: dict[str, Tienda] = {}
    for datos in TIENDAS_SEMILLA:
        tienda = db.scalar(select(Tienda).where(Tienda.nombre == datos["nombre"]))
        if tienda is None:
            tienda = Tienda(nombre=datos["nombre"], ciudad=datos["ciudad"])
            db.add(tienda)
            db.flush()
        tiendas_por_nombre[datos["nombre"]] = tienda
    return tiendas_por_nombre


def sembrar_usuarios(db: Session, tiendas_por_nombre: dict[str, Tienda]) -> None:
    for datos in USUARIOS_SEMILLA:
        usuario = db.scalar(select(Usuario).where(Usuario.email == datos["email"]))
        if usuario is not None:
            continue
        usuario = Usuario(
            email=datos["email"],
            nombre_completo=NOMBRE_COMPLETO_POR_EMAIL[datos["email"]],
            password_hash=hash_contrasena(CONTRASENA_SEMILLA),
            tienda_id=tiendas_por_nombre[datos["tienda"]].id,
            rol=datos["rol"],
            estado=datos["estado"],
        )
        db.add(usuario)


def sembrar_productos(db: Session, tiendas_por_nombre: dict[str, Tienda]) -> None:
    for tienda in tiendas_por_nombre.values():
        for datos in PRODUCTOS_SEMILLA_POR_TIENDA:
            producto = db.scalar(
                select(Producto).where(Producto.tienda_id == tienda.id, Producto.sku == datos["sku"])
            )
            if producto is not None:
                continue
            db.add(
                Producto(
                    tienda_id=tienda.id,
                    sku=datos["sku"],
                    nombre=datos["nombre"],
                    descripcion=datos["descripcion"],
                    precio=Decimal(datos["precio"]),
                    stock=datos["stock"],
                )
            )


def sembrar() -> None:
    db = SesionLocal()
    try:
        tiendas_por_nombre = sembrar_tiendas(db)
        sembrar_usuarios(db, tiendas_por_nombre)
        sembrar_productos(db, tiendas_por_nombre)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    sembrar()
