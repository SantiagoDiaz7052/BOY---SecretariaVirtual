from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime


@dataclass
class GeminiResult:
    """Resultado controlado de una llamada a Gemini.
    
    Nunca lanza excepciones. Si Gemini falla, success=False
    y el dominio decide que hacer.
    """
    success: bool
    data: Optional[Any] = None
    error_type: Optional[str] = None
    message: Optional[str] = None
    raw_response: Optional[str] = None
    timestamp: Optional[datetime] = None
    retries_used: int = 0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @classmethod
    def ok(cls, data: Any, raw_response: Optional[str] = None, 
           retries_used: int = 0) -> "GeminiResult":
        return cls(
            success=True,
            data=data,
            raw_response=raw_response,
            retries_used=retries_used,
        )

    @classmethod
    def fail(cls, error_type: str, message: str, 
             retries_used: int = 0) -> "GeminiResult":
        return cls(
            success=False,
            error_type=error_type,
            message=message,
            retries_used=retries_used,
        )


@dataclass
class VisionAnalysisResult:
    """Resultado del analisis de un comprobante de pago."""
    es_comprobante: bool = False
    monto_detectado: Optional[float] = None
    referencia: Optional[str] = None
    fecha: Optional[str] = None
    plataforma: Optional[str] = None
    texto_completo: Optional[str] = None

    @classmethod
    def from_text(cls, texto: str) -> "VisionAnalysisResult":
        resultado = cls(texto_completo=texto)
        
        for linea in texto.strip().split("\n"):
            if "MONTO:" in linea:
                try:
                    monto_str = linea.split("MONTO:")[1].strip().replace(".", "").replace(",", "")
                    resultado.monto_detectado = float(monto_str)
                except (ValueError, IndexError):
                    pass
            elif "FECHA:" in linea:
                resultado.fecha = linea.split("FECHA:")[1].strip()
            elif "REFERENCIA:" in linea:
                resultado.referencia = linea.split("REFERENCIA:")[1].strip()
            elif "ES_COMPROBANTE:" in linea:
                resultado.es_comprobante = "SI" in linea.upper()
            elif "PLATAFORMA:" in linea:
                resultado.plataforma = linea.split("PLATAFORMA:")[1].strip()
        
        return resultado

    def to_dict(self) -> dict:
        return {
            "es_comprobante": self.es_comprobante,
            "monto_detectado": self.monto_detectado,
            "referencia": self.referencia,
            "fecha": self.fecha,
            "plataforma": self.plataforma,
            "texto_completo": self.texto_completo,
        }
