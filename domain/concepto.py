from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Concepto:
    """Define un tipo de cargo que un club puede cobrar.
    
    El concepto define el COMPORTAMIENTO del cargo:
    - Si es recurrente (mensualidad)
    - Si se auto-genera
    - Si aplica mora
    - Si requiere periodo
    - El monto por defecto
    - Recargo y dias limite (overrides de configuracion_club)
    
    IMPORTANTE: El concepto es un template. La obligacion COPIA el precio
    al momento de crearse. Modificar un concepto NO afecta obligaciones existentes.
    """
    
    id: str
    club_id: str
    nombre: str
    es_recurrente: bool = False
    genera_automaticamente: bool = False
    aplica_mora: bool = False
    requiere_periodo: bool = False
    monto_default: float = 0
    recargo_fijo: Optional[float] = None
    dias_limite_pago: Optional[int] = None
    version: int = 1
    activo: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Concepto":
        return cls(
            id=data["id"],
            club_id=data["club_id"],
            nombre=data["nombre"],
            es_recurrente=data.get("es_recurrente", False),
            genera_automaticamente=data.get("genera_automaticamente", False),
            aplica_mora=data.get("aplica_mora", False),
            requiere_periodo=data.get("requiere_periodo", False),
            monto_default=float(data.get("monto_default", 0)),
            recargo_fijo=float(data["recargo_fijo"]) if data.get("recargo_fijo") is not None else None,
            dias_limite_pago=data.get("dias_limite_pago"),
            version=data.get("version", 1),
            activo=data.get("activo", True),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "nombre": self.nombre,
            "es_recurrente": self.es_recurrente,
            "genera_automaticamente": self.genera_automaticamente,
            "aplica_mora": self.aplica_mora,
            "requiere_periodo": self.requiere_periodo,
            "monto_default": self.monto_default,
            "recargo_fijo": self.recargo_fijo,
            "dias_limite_pago": self.dias_limite_pago,
            "version": self.version,
            "activo": self.activo,
        }

    def obtener_monto_con_recargo(self, monto_base: float, recargo_global: float) -> float:
        """Calcula el monto con recargo aplicando overrides del concepto.
        
        Si el concepto tiene recargo_fijo, se usa ese.
        Si no, se usa el recargo_global de configuracion_club.
        """
        recargo = self.recargo_fijo if self.recargo_fijo is not None else recargo_global
        return monto_base + recargo

    def obtener_dias_limite(self, dias_global: int) -> int:
        """Obtiene los dias limite de pago.
        
        Si el concepto tiene dias_limite_pago, se usa ese.
        Si no, se usa el valor global de configuracion_club.
        """
        return self.dias_limite_pago if self.dias_limite_pago is not None else dias_global
