from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EstadoTemporada(Enum):
    ACTIVA = "activa"
    CERRADA = "cerrada"


@dataclass
class Temporada:
    """Entidad de dominio Temporada.
    
    Representa un periodo anual (2026, 2027, etc).
    Todas las obligaciones, preinscripciones y deportistas activos
    estan asociados a una temporada.
    
    REGLAS:
    - Una sola temporada activa por club
    - Permite consultar inscritos por anio
    - Facilita historial y estadisticas
    """
    club_id: str
    nombre: str
    fecha_inicio: str
    fecha_fin: str
    estado: str = EstadoTemporada.ACTIVA.value
    id: Optional[str] = None
    created_at: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "Temporada":
        return Temporada(
            id=data.get("id"),
            club_id=data["club_id"],
            nombre=data["nombre"],
            fecha_inicio=data["fecha_inicio"],
            fecha_fin=data["fecha_fin"],
            estado=data.get("estado", EstadoTemporada.ACTIVA.value),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "nombre": self.nombre,
            "fecha_inicio": self.fecha_inicio,
            "fecha_fin": self.fecha_fin,
            "estado": self.estado,
            "created_at": self.created_at,
        }

    @property
    def esta_activa(self) -> bool:
        return self.estado == EstadoTemporada.ACTIVA.value
