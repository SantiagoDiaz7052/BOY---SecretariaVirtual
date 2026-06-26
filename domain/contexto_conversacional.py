from dataclasses import dataclass
from typing import Optional


@dataclass
class ContextoConversacional:
    """Entidad de dominio ContextoConversacional.
    
    Representa la memoria activa del usuario en una conversacion.
    
    REGLAS:
    - Una sola sesion activa por (club_id, numero_whatsapp)
    - Almacena: deportista_actual, proceso_pago_actual, obligacion_actual
    - Permite que BOY entienda respuestas cortas como "ya pagué", "listo"
    - Se actualiza automaticamente segun la interaccion
    """
    club_id: str
    numero_whatsapp: str
    estado: str = "activa"
    deportista_actual_id: Optional[str] = None
    proceso_pago_actual_id: Optional[str] = None
    obligacion_actual_id: Optional[str] = None
    ultima_intencion: Optional[str] = None
    ultimo_comprobante_url: Optional[str] = None
    id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "ContextoConversacional":
        return ContextoConversacional(
            id=data.get("id"),
            club_id=data["club_id"],
            numero_whatsapp=data["numero_whatsapp"],
            estado=data.get("estado", "activa"),
            deportista_actual_id=data.get("deportista_actual_id"),
            proceso_pago_actual_id=data.get("proceso_pago_actual_id"),
            obligacion_actual_id=data.get("obligacion_actual_id"),
            ultima_intencion=data.get("ultima_intencion"),
            ultimo_comprobante_url=data.get("ultimo_comprobante_url"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "numero_whatsapp": self.numero_whatsapp,
            "estado": self.estado,
            "deportista_actual_id": self.deportista_actual_id,
            "proceso_pago_actual_id": self.proceso_pago_actual_id,
            "obligacion_actual_id": self.obligacion_actual_id,
            "ultima_intencion": self.ultima_intencion,
            "ultimo_comprobante_url": self.ultimo_comprobante_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @property
    def esta_activa(self) -> bool:
        return self.estado == "activa"

    def tiene_deportista(self) -> bool:
        return self.deportista_actual_id is not None

    def tiene_proceso_pago(self) -> bool:
        return self.proceso_pago_actual_id is not None

    def limpiar(self) -> None:
        """Limpia el contexto manteniendo la sesion."""
        self.deportista_actual_id = None
        self.proceso_pago_actual_id = None
        self.obligacion_actual_id = None
        self.ultima_intencion = None
        self.ultimo_comprobante_url = None
