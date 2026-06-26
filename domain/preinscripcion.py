from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EstadoPreinscripcion(Enum):
    PENDIENTE_PAGO = "pendiente_pago"
    PAGO_RECIBIDO = "pago_recibido"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"


@dataclass
class Preinscripcion:
    """Entidad de dominio Preinscripcion.
    
    Representa un proceso de matricula antes de crear el Deportista.
    
    FLUJO:
    1. Usuario completa datos
    2. Se crea Preinscripcion (pendiente_pago)
    3. Se inicia ProcesoPago vinculado
    4. Se espera comprobante
    5. Comprobante aprobado → CONFIRMADA
    6. Se crea Deportista real (INACTIVO)
    
    REGLAS:
    - No existe Deportista hasta que Preinscripcion sea CONFIRMADA
    - ProcesoPago se vincula a Preinscripcion, no a Deportista
    - El nivel se asigna en este proceso
    - Preparado para padres con varios hijos (responsable)
    """
    club_id: str
    temporada_id: str
    nombre: str
    documento: str
    nivel: str
    estado: str = EstadoPreinscripcion.PENDIENTE_PAGO.value
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    responsable_nombre: Optional[str] = None
    responsable_documento: Optional[str] = None
    responsable_whatsapp: Optional[str] = None
    obligacion_id: Optional[str] = None
    proceso_pago_id: Optional[str] = None
    id: Optional[str] = None
    created_at: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "Preinscripcion":
        return Preinscripcion(
            id=data.get("id"),
            club_id=data["club_id"],
            temporada_id=data.get("temporada_id", ""),
            nombre=data["nombre"],
            documento=data["documento"],
            nivel=data.get("nivel", "iniciacion"),
            estado=data.get("estado", EstadoPreinscripcion.PENDIENTE_PAGO.value),
            telefono=data.get("telefono"),
            fecha_nacimiento=data.get("fecha_nacimiento"),
            responsable_nombre=data.get("responsable_nombre"),
            responsable_documento=data.get("responsable_documento"),
            responsable_whatsapp=data.get("responsable_whatsapp"),
            obligacion_id=data.get("obligacion_id"),
            proceso_pago_id=data.get("proceso_pago_id"),
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
            "obligacion_id": self.obligacion_id,
            "proceso_pago_id": self.proceso_pago_id,
            "created_at": self.created_at,
        }

    @property
    def esta_pendiente(self) -> bool:
        return self.estado == EstadoPreinscripcion.PENDIENTE_PAGO.value

    @property
    def esta_confirmada(self) -> bool:
        return self.estado == EstadoPreinscripcion.CONFIRMADA.value
