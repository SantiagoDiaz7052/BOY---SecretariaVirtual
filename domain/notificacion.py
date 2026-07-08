from dataclasses import dataclass
from typing import Optional


@dataclass
class Notificacion:
    club_id: str
    tipo: str
    icono: str
    texto: str
    referencia_id: Optional[str] = None
    leida: bool = False
    id: Optional[str] = None
    created_at: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "Notificacion":
        return Notificacion(
            id=data.get("id"),
            club_id=data.get("club_id", ""),
            tipo=data.get("tipo", ""),
            icono=data.get("icono", ""),
            texto=data.get("texto", ""),
            referencia_id=data.get("referencia_id"),
            leida=data.get("leida", False),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "tipo": self.tipo,
            "icono": self.icono,
            "texto": self.texto,
            "referencia_id": self.referencia_id,
            "leida": self.leida,
            "created_at": self.created_at,
        }
