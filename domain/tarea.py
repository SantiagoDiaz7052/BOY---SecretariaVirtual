from dataclasses import dataclass
from typing import Optional


@dataclass
class Tarea:
    """Entidad de dominio Tarea (Bandeja de trabajo).
    
    Proyeccion derivada del estado del dominio.
    Refleja acciones pendientes para la secretaria.
    
    REGLAS:
    - No gobierna el negocio (solo refleja estado)
    - Se crea automaticamente por cambios en SolicitudIngreso, Pago, etc.
    - Se completa cuando la accion es realizada
    - Efectimera: se resuelve y no tiene impacto en logica del dominio
    """
    club_id: str
    tipo: str
    referencia_id: str
    descripcion: str
    estado: str = "pendiente"
    id: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "Tarea":
        return Tarea(
            id=data.get("id"),
            club_id=data["club_id"],
            tipo=data["tipo"],
            referencia_id=data["referencia_id"],
            descripcion=data["descripcion"],
            estado=data.get("estado", "pendiente"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "tipo": self.tipo,
            "referencia_id": self.referencia_id,
            "descripcion": self.descripcion,
            "estado": self.estado,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @property
    def esta_pendiente(self) -> bool:
        return self.estado == "pendiente"
