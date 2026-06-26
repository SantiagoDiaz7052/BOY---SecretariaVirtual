from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class OrigenObligacion(str, Enum):
    """Origen de la obligacion: quien creo la deuda."""
    AUTOMATICO = "automatico"
    MANUAL = "manual"
    IMPORTADO = "importado"


class EstadoObligacion(str, Enum):
    """Estados calculados (no almacenados, se derivan al vuelo)."""
    PENDIENTE = "pendiente"
    PAGADA = "pagada"
    VENCIDA = "vencida"


@dataclass
class Obligacion:
    """Cargo concreto que un deportista debe pagar.
    
    REGLAS:
    - El monto_total se copia del concepto al momento de crearse
    - El saldo_pendiente se calcula: monto_total - SUM(pagos_aprobados)
    - El estado se calcula: pagada/vencida/pendiente
    - El concepto NUNCA se modifica despues de crear la obligacion
    - El origen indica quien creo la deuda (automatico, manual, importado)
    """
    
    id: str
    club_id: str
    deportista_id: str
    concepto_id: str
    monto_total: float
    origen: OrigenObligacion = OrigenObligacion.AUTOMATICO
    fecha_creacion: Optional[date] = None
    fecha_limite: Optional[date] = None
    periodo: Optional[str] = None  # "2025-01", null si no es recurrente
    referencia: Optional[str] = None  # "Licra Talla M", "Copa Star 2025", etc.
    nota: Optional[str] = None
    created_at: Optional[datetime] = None

    # Campos calculados (no almacenados en DB)
    monto_pagado: float = field(default=0, init=False)
    saldo_pendiente: float = field(default=0, init=False)
    estado: EstadoObligacion = field(default=EstadoObligacion.PENDIENTE, init=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Obligacion":
        obligacion = cls(
            id=data["id"],
            club_id=data["club_id"],
            deportista_id=data["deportista_id"],
            concepto_id=data["concepto_id"],
            monto_total=float(data["monto_total"]),
            origen=OrigenObligacion(data.get("origen", "automatico")),
            fecha_creacion=data.get("fecha_creacion"),
            fecha_limite=data.get("fecha_limite"),
            periodo=data.get("periodo"),
            referencia=data.get("referencia"),
            nota=data.get("nota"),
            created_at=data.get("created_at"),
        )
        # Los campos calculados se establecen despues con calcular_estado()
        return obligacion

    def calcular_estado(self, monto_pagado: float) -> None:
        """Calcula el estado y saldo basado en pagos aprobados.
        
        Este metodo se llama DESPUES de consultar los pagos aprobados.
        No almacena nada en la base de datos.
        """
        self.monto_pagado = monto_pagado
        self.saldo_pendiente = self.monto_total - monto_pagado
        
        if self.saldo_pendiente <= 0:
            self.estado = EstadoObligacion.PAGADA
        elif self.fecha_limite and self.fecha_limite < date.today():
            self.estado = EstadoObligacion.VENCIDA
        else:
            self.estado = EstadoObligacion.PENDIENTE

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "deportista_id": self.deportista_id,
            "concepto_id": self.concepto_id,
            "monto_total": self.monto_total,
            "origen": self.origen.value,
            "fecha_creacion": str(self.fecha_creacion) if self.fecha_creacion else None,
            "fecha_limite": str(self.fecha_limite) if self.fecha_limite else None,
            "periodo": self.periodo,
            "referencia": self.referencia,
            "nota": self.nota,
            "monto_pagado": self.monto_pagado,
            "saldo_pendiente": self.saldo_pendiente,
            "estado": self.estado.value,
        }

    @property
    def esta_cancelada(self) -> bool:
        """Verifica si la obligacion esta completamente pagada."""
        return self.estado == EstadoObligacion.PAGADA

    @property
    def esta_vencida(self) -> bool:
        """Verifica si la obligacion esta vencida."""
        return self.estado == EstadoObligacion.VENCIDA

    @property
    def es_recurrente(self) -> bool:
        """Verifica si la obligacion es recurrente (tiene periodo)."""
        return self.periodo is not None
