from dataclasses import dataclass
from enum import Enum
from typing import Optional


class NivelDeportista(Enum):
    INICIACION = "iniciacion"
    INTERMEDIO = "intermedio"
    AVANZADO = "avanzado"


class EstadoDeportista(Enum):
    INACTIVO = "inactivo"    # No pago mensualidad del mes actual
    ACTIVO = "activo"        # Pago y tiene derecho a entrenar


@dataclass
class Deportista:
    """Entidad de dominio Deportista.
    
    Representa a un deportista registrado en el club.
    El estado indica si tiene derecho a entrenar ese mes.
    
    REGLAS:
    - Un deportista INACTIVO no puede entrenar
    - El nivel se asigna en matricula, admin puede modificar
    - Preparado para padres con varios hijos (responsable)
    - Asociado a una temporada
    """
    club_id: str
    temporada_id: str
    nombre: str
    documento: str
    nivel: str = NivelDeportista.INICIACION.value
    estado: str = EstadoDeportista.INACTIVO.value
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    responsable_nombre: Optional[str] = None
    responsable_documento: Optional[str] = None
    responsable_whatsapp: Optional[str] = None
    id: Optional[str] = None
    created_at: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "Deportista":
        return Deportista(
            id=data.get("id"),
            club_id=data["club_id"],
            temporada_id=data.get("temporada_id", ""),
            nombre=data["nombre"],
            documento=data["documento"],
            nivel=data.get("nivel", NivelDeportista.INICIACION.value),
            estado=data.get("estado", EstadoDeportista.INACTIVO.value),
            telefono=data.get("telefono"),
            fecha_nacimiento=data.get("fecha_nacimiento"),
            responsable_nombre=data.get("responsable_nombre"),
            responsable_documento=data.get("responsable_documento"),
            responsable_whatsapp=data.get("responsable_whatsapp"),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "temporada_id": self.temporada_id,
            "nombre": self.nombre,
            "documento": self.documento,
            "nivel": self.nivel,
            "estado": self.estado,
            "telefono": self.telefono,
            "fecha_nacimiento": self.fecha_nacimiento,
            "responsable_nombre": self.responsable_nombre,
            "responsable_documento": self.responsable_documento,
            "responsable_whatsapp": self.responsable_whatsapp,
            "created_at": self.created_at,
        }

    @property
    def esta_activo(self) -> bool:
        return self.estado == EstadoDeportista.ACTIVO.value

    def activar(self) -> None:
        self.estado = EstadoDeportista.ACTIVO.value

    def desactivar(self) -> None:
        self.estado = EstadoDeportista.INACTIVO.value

    @property
    def telefono_whatsapp(self) -> str:
        """Retorna el telefono para WhatsApp (puede ser del responsable)."""
        return self.responsable_whatsapp or self.telefono or ""
