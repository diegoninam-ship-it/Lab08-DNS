from datetime import datetime, timezone


class Reloj:
    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)


def obtener_reloj() -> Reloj:
    return Reloj()
