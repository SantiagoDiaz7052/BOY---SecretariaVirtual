from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EstadoSolicitud(Enum):
    PENDIENTE_EVALUACION = "pendiente_evaluacion"
    EVALUADO = "evaluado"
    PENDIENTE_MATRICULA = "pendiente_matricula"
    MATRICULA_PAGADA = "matricula_pagada"
    PENDIENTE_ACTIVACION = "pendiente_activacion"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"


class ExperienciaReportada(Enum):
    SI = "si"
    NO = "no"
    NO_SABE = "no_sabe"


@dataclass
class SolicitudIngreso:
    """Entidad de dominio Solicitud de Ingreso.
    
    Representa el proceso completo de admision de un nuevo deportista,
    desde que el padre muestra interes hasta que el deportista esta activo.
    
    REGLAS:
    - NO conoce pagos, obligaciones ni procesos (solo su estado)
    - El nivel lo asigna la secretaria en EVALUADO
    - La experiencia reportada es solo referencia (no determina nivel)
    - Un documento solo puede tener una solicitud activa
    """
    club_id: str
    temporada_id: str
    nombre: str
    documento: str
    telefono: str
    fecha_nacimiento: Optional[str] = None
    experiencia_reportada: Optional[str] = None
    responsable_nombre: Optional[str] = None
    responsable_documento: Optional[str] = None
    responsable_whatsapp: Optional[str] = None
    nivel: Optional[str] = None
    fecha_evaluacion: Optional[str] = None
    estado: str = EstadoSolicitud.PENDIENTE_EVALUACION.value
    id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "SolicitudIngreso":
        return SolicitudIngreso(
            id=data.get("id"),
            club_id=data["club_id"],
            temporada_id=data.get("temporada_id", ""),
            nombre=data["nombre"],
            documento=data["documento"],
            telefono=data.get("telefono", ""),
            fecha_nacimiento=data.get("fecha_nacimiento"),
            experiencia_reportada=data.get("experiencia_reportada"),
            responsable_nombre=data.get("responsable_nombre"),
            responsable_documento=data.get("responsable_documento"),
            responsable_whatsapp=data.get("responsable_whatsapp"),
            nivel=data.get("nivel"),
            fecha_evaluacion=data.get("fecha_evaluacion"),
            estado=data.get("estado", EstadoSolicitud.PENDIENTE_EVALUACION.value),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "temporada_id": self.temporada_id,
            "nombre": self.nombre,
            "documento": self.documento,
            "telefono": self.telefono,
            "fecha_nacimiento": self.fecha_nacimiento,
            "experiencia_reportada": self.experiencia_reportada,
            "responsable_nombre": self.responsable_nombre,
            "responsable_documento": self.responsable_documento,
            "responsable_whatsapp": self.responsable_whatsapp,
            "nivel": self.nivel,
            "fecha_evaluacion": self.fecha_evaluacion,
            "estado": self.estado,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @property
    def esta_pendiente_evaluacion(self) -> bool:
        return self.estado == EstadoSolicitud.PENDIENTE_EVALUACION.value

    @property
    def esta_evaluado(self) -> bool:
        return self.estado == EstadoSolicitud.EVALUADO.value

    @property
    def esta_pendiente_matricula(self) -> bool:
        return self.estado == EstadoSolicitud.PENDIENTE_MATRICULA.value

    @property
    def esta_matricula_pagada(self) -> bool:
        return self.estado == EstadoSolicitud.MATRICULA_PAGADA.value

    @property
    def esta_completado(self) -> bool:
        return self.estado == EstadoSolicitud.COMPLETADO.value

    def puede_transicionar_a(self, nuevo_estado: str) -> bool:
        """Valida si la transicion de estado es permitida."""
        transiciones = {
            EstadoSolicitud.PENDIENTE_EVALUACION.value: [
                EstadoSolicitud.EVALUADO.value,
                EstadoSolicitud.CANCELADO.value,
            ],
            EstadoSolicitud.EVALUADO.value: [
                EstadoSolicitud.PENDIENTE_MATRICULA.value,
                EstadoSolicitud.CANCELADO.value,
            ],
            EstadoSolicitud.PENDIENTE_MATRICULA.value: [
                EstadoSolicitud.MATRICULA_PAGADA.value,
                EstadoSolicitud.CANCELADO.value,
            ],
            EstadoSolicitud.MATRICULA_PAGADA.value: [
                EstadoSolicitud.PENDIENTE_ACTIVACION.value,
                EstadoSolicitud.CANCELADO.value,
            ],
            EstadoSolicitud.PENDIENTE_ACTIVACION.value: [
                EstadoSolicitud.COMPLETADO.value,
                EstadoSolicitud.CANCELADO.value,
            ],
            EstadoSolicitud.COMPLETADO.value: [],
            EstadoSolicitud.CANCELADO.value: [],
        }
        return nuevo_estado in transiciones.get(self.estado, [])
