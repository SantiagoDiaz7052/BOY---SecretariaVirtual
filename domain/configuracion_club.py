from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class ConfiguracionClub:
    """Configuracion operacional de un club, separada de su identidad.
    
    Contiene:
    - Llave Bre-B para pagos
    - Tolerancia de monto para comprobantes
    - Recargo por defecto
    - Dias de recordatorio
    - Si notificar estados de pago
    
    Esta configuracion es independiente del concepto.
    Los conceptos pueden tener overrides que la sobreescriban.
    """
    
    id: str
    club_id: str
    llave_bre_b: Optional[str] = None
    tolerancia_monto: float = 5000
    recargo_default: float = 0
    recordatorio_dias: List[int] = None
    notificar_estado_pago: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.recordatorio_dias is None:
            self.recordatorio_dias = [3, 1, 0]

    @classmethod
    def from_dict(cls, data: dict) -> "ConfiguracionClub":
        return cls(
            id=data["id"],
            club_id=data["club_id"],
            llave_bre_b=data.get("llave_bre_b"),
            tolerancia_monto=float(data.get("tolerancia_monto", 5000)),
            recargo_default=float(data.get("recargo_default", 0)),
            recordatorio_dias=data.get("recordatorio_dias", [3, 1, 0]),
            notificar_estado_pago=data.get("notificar_estado_pago", True),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "llave_bre_b": self.llave_bre_b,
            "tolerancia_monto": self.tolerancia_monto,
            "recargo_default": self.recargo_default,
            "recordatorio_dias": self.recordatorio_dias,
            "notificar_estado_pago": self.notificar_estado_pago,
        }

    def es_monto_aceptable(self, monto_detectado: float, monto_esperado: float) -> bool:
        """Verifica si el monto detectado esta dentro de la tolerancia."""
        return abs(monto_detectado - monto_esperado) <= self.tolerancia_monto

    def obtener_recargo(self, recargo_concepto: Optional[float] = None) -> float:
        """Obtiene el recargo a aplicar.
        
        Si el concepto tiene recargo_fijo, se usa ese.
        Si no, se usa el recargo_default de la configuracion.
        """
        if recargo_concepto is not None:
            return recargo_concepto
        return self.recargo_default
