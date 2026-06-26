from dataclasses import dataclass, field
from typing import Optional, Any, Dict
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
    """DTO resultado del analisis de un comprobante de pago.
    
    Campos:
    - es_valido: True si Gemini determino que es un comprobante legitimo
    - monto_detectado: Monto en COP detectado en la imagen
    - referencia_detectada: Numero de referencia o transaccion
    - fecha_detectada: Fecha del comprobante (YYYY-MM-DD)
    - plataforma_detectada: Nequi, Daviplata, transferencia, etc.
    - confianza: Nivel de confianza del analisis (0.0 a 1.0)
    - razon: Explicacion de por que es valido o no
    - metadata: JSON con el analisis completo de Gemini
    
    Este DTO NO conoce Obligaciones, Pagos, Clubes ni reglas de negocio.
    Solo contiene datos extraidos de la imagen.
    """
    es_valido: bool = False
    monto_detectado: Optional[float] = None
    referencia_detectada: Optional[str] = None
    fecha_detectada: Optional[str] = None
    plataforma_detectada: Optional[str] = None
    confianza: float = 0.0
    razon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_text(cls, texto: str) -> "VisionAnalysisResult":
        """Parsea la respuesta de Gemini y construye el DTO."""
        resultado = cls()
        metadata = {
            "texto_completo": texto,
            "campos_parseados": {},
        }
        
        for linea in texto.strip().split("\n"):
            if "MONTO:" in linea:
                try:
                    monto_str = linea.split("MONTO:")[1].strip().replace(".", "").replace(",", "")
                    resultado.monto_detectado = float(monto_str)
                    metadata["campos_parseados"]["monto"] = True
                except (ValueError, IndexError):
                    metadata["campos_parseados"]["monto"] = False
            elif "FECHA:" in linea:
                resultado.fecha_detectada = linea.split("FECHA:")[1].strip()
                metadata["campos_parseados"]["fecha"] = True
            elif "REFERENCIA:" in linea:
                resultado.referencia_detectada = linea.split("REFERENCIA:")[1].strip()
                metadata["campos_parseados"]["referencia"] = True
            elif "ES_COMPROBANTE:" in linea:
                es_valido = "SI" in linea.upper()
                resultado.es_valido = es_valido
                resultado.razon = "Comprobante valido" if es_valido else "No es un comprobante valido"
                metadata["campos_parseados"]["es_comprobante"] = True
            elif "PLATAFORMA:" in linea:
                resultado.plataforma_detectada = linea.split("PLATAFORMA:")[1].strip()
                metadata["campos_parseados"]["plataforma"] = True
        
        # Calcular confianza basado en campos parseados exitosamente
        campos_parseados = metadata["campos_parseados"]
        total_campos = 5  # monto, fecha, referencia, es_comprobante, plataforma
        campos_ok = sum(1 for v in campos_parseados.values() if v)
        resultado.confianza = round(campos_ok / total_campos, 2)
        
        resultado.metadata = metadata
        return resultado

    def to_dict(self) -> dict:
        return {
            "es_valido": self.es_valido,
            "monto_detectado": self.monto_detectado,
            "referencia_detectada": self.referencia_detectada,
            "fecha_detectada": self.fecha_detectada,
            "plataforma_detectada": self.plataforma_detectada,
            "confianza": self.confianza,
            "razon": self.razon,
            "metadata": self.metadata,
        }
