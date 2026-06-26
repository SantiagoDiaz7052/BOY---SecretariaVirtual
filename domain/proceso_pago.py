from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class EstadoProcesoPago(str, Enum):
    """Estados simplificados del proceso de pago.
    
    Los estados excesivos generan bugs.
    Solo 3 estados: ACTIVO, FINALIZADO, CANCELADO.
    Los detalles se registran como eventos.
    """
    ACTIVO = "activo"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"


class EventoProcesoPago(str, Enum):
    """Eventos que ocurren durante el proceso de pago.
    
    Se registran en el historial, no como estados.
    """
    INICIADO = "iniciado"
    INSTRUCCIONES_ENVIADAS = "instrucciones_enviadas"
    COMPROBANTE_RECIBIDO = "comprobante_recibido"
    COMPROBANTE_ANALIZADO = "comprobante_analizado"
    PAGO_REGISTRADO = "pago_registrado"
    PAGO_APROBADO = "pago_aprobado"
    PAGO_RECHAZADO = "pago_rechazado"
    ERROR_GEMINI = "error_gemini"
    CANCELADO_USUARIO = "cancelado_usuario"
    CANCELADO_TIMEOUT = "cancelado_timeout"


@dataclass
class EventoHistorial:
    """Un evento en el historial del proceso de pago."""
    evento: EventoProcesoPago
    timestamp: datetime
    detalle: Optional[str] = None
    metadata: Optional[dict] = None

    @classmethod
    def from_dict(cls, data: dict) -> "EventoHistorial":
        return cls(
            evento=EventoProcesoPago(data["evento"]),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
            detalle=data.get("detalle"),
            metadata=data.get("metadata"),
        )

    def to_dict(self) -> dict:
        return {
            "evento": self.evento.value,
            "timestamp": self.timestamp.isoformat(),
            "detalle": self.detalle,
            "metadata": self.metadata,
        }


@dataclass
class ProcesoPago:
    """Contexto conversacional de un intento de pago.
    
    NO es una entidad financiera.
    Representa la CONVERSACION entre el usuario y el bot
    sobre un pago.
    
    Flujo:
    1. Usuario dice "quiero pagar" → ProcesoPago(estado=ACTIVO)
    2. Bot envía instrucciones → evento INSTRUCCIONES_ENVIADAS
    3. Usuario envía comprobante → evento COMPROBANTE_RECIBIDO
    4. Gemini analiza → evento COMPROBANTE_ANALIZADO o ERROR_GEMINI
    5. Se registra pago → evento PAGO_REGISTRADO
    6. Admin aprueba → evento PAGO_APROBADO → estado=FINALIZADO
    
    Si Gemini falla en paso 4:
    - Se registra evento ERROR_GEMINI
    - Se mantiene estado=ACTIVO para reintentar
    - El usuario puede enviar otro comprobante
    """
    
    id: str
    club_id: str
    deportista_id: str
    obligacion_id: Optional[str] = None
    llave_bre_b: Optional[str] = None
    monto_informado: Optional[float] = None
    estado: EstadoProcesoPago = EstadoProcesoPago.ACTIVO
    historial: List[EventoHistorial] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "ProcesoPago":
        historial_raw = data.get("historial", [])
        historial = [EventoHistorial.from_dict(e) for e in historial_raw]
        
        return cls(
            id=data["id"],
            club_id=data["club_id"],
            deportista_id=data["deportista_id"],
            obligacion_id=data.get("obligacion_id"),
            llave_bre_b=data.get("llave_bre_b"),
            monto_informado=float(data["monto_informado"]) if data.get("monto_informado") else None,
            estado=EstadoProcesoPago(data.get("estado", "activo")),
            historial=historial,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "deportista_id": self.deportista_id,
            "obligacion_id": self.obligacion_id,
            "llave_bre_b": self.llave_bre_b,
            "monto_informado": self.monto_informado,
            "estado": self.estado.value,
            "historial": [e.to_dict() for e in self.historial],
        }

    def agregar_evento(self, evento: EventoProcesoPago, 
                       detalle: Optional[str] = None,
                       metadata: Optional[dict] = None) -> None:
        """Registra un evento en el historial."""
        self.historial.append(EventoHistorial(
            evento=evento,
            timestamp=datetime.now(),
            detalle=detalle,
            metadata=metadata,
        ))

    def esta_activo(self) -> bool:
        return self.estado == EstadoProcesoPago.ACTIVO

    def finalizar(self) -> None:
        """Finaliza el proceso de pago."""
        self.estado = EstadoProcesoPago.FINALIZADO

    def cancelar(self, motivo: str = "usuario") -> None:
        """Cancela el proceso de pago."""
        self.estado = EstadoProcesoPago.CANCELADO
        self.agregar_evento(
            EventoProcesoPago.CANCELADO_USUARIO if motivo == "usuario" 
            else EventoProcesoPago.CANCELADO_TIMEOUT,
            detalle=motivo,
        )
