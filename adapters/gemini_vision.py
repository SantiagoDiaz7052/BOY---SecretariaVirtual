import logging
import httpx
import base64
import os
from dotenv import load_dotenv

from adapters.gemini_client import gemini_client
from adapters.gemini_models import GeminiResult, VisionAnalysisResult

load_dotenv()

logger = logging.getLogger("boy.gemini.vision")


class GeminiVisionAdapter:
    """Adaptador para analisis de imagenes con Gemini Vision.
    
    Aislamiento del dominio:
    - Descarga la imagen de Twilio
    - La envia a Gemini Vision
    - Retorna VisionAnalysisResult
    - Nunca lanza excepciones
    """
    
    def __init__(self):
        self._twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self._twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    def _descargar_imagen(self, imagen_url: str) -> GeminiResult:
        """Descarga la imagen desde Twilio."""
        try:
            response = httpx.get(
                imagen_url,
                auth=(self._twilio_sid, self._twilio_token),
                timeout=15,
            )
            response.raise_for_status()
            
            imagen_base64 = base64.b64encode(response.content).decode("utf-8")
            content_type = response.headers.get("content-type", "image/jpeg")
            
            return GeminiResult.ok(data={
                "imagen_base64": imagen_base64,
                "content_type": content_type,
            })
            
        except httpx.TimeoutException:
            logger.error(f"[VISION] Timeout descargando imagen: {imagen_url}")
            return GeminiResult.fail(
                error_type="IMAGE_DOWNLOAD_TIMEOUT",
                message="Timeout al descargar la imagen",
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"[VISION] HTTP error descargando imagen: {e.response.status_code}")
            return GeminiResult.fail(
                error_type="IMAGE_DOWNLOAD_ERROR",
                message=f"Error HTTP al descargar imagen: {e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"[VISION] Error inesperado descargando imagen: {e}")
            return GeminiResult.fail(
                error_type="IMAGE_DOWNLOAD_ERROR",
                message=f"Error al descargar imagen: {str(e)}",
            )
    
    def analizar_comprobante(self, imagen_url: str, 
                             monto_esperado: float) -> GeminiResult:
        """Analiza un comprobante de pago con Gemini Vision.
        
        Args:
            imagen_url: URL de la imagen en Twilio
            monto_esperado: Monto esperado en COP
        
        Returns:
            GeminiResult con VisionAnalysisResult como data
        """
        # 1. Descargar imagen
        descarga = self._descargar_imagen(imagen_url)
        if not descarga.success:
            return descarga
        
        imagen_data = descarga.data
        
        # 2. Construir prompt
        prompt = f"""Analiza este comprobante de pago colombiano.
Extrae la siguiente informacion en formato exacto:

MONTO: (solo el numero, sin puntos ni comas, ejemplo: 90000)
FECHA: (formato YYYY-MM-DD, si no se ve claramente escribe DESCONOCIDA)
REFERENCIA: (numero de referencia o transaccion, si no hay escribe NINGUNA)
ES_COMPROBANTE: (SI o NO, si parece una imagen legitima de pago)
PLATAFORMA: (Nequi, Daviplata, transferencia bancaria, o DESCONOCIDA)

Monto esperado: ${monto_esperado:,.0f} COP
El monto coincide aproximadamente? Responde solo con el formato pedido."""

        # 3. Construir contenido
        contents = [
            types.Content(parts=[
                types.Part(
                    inline_data=types.Blob(
                        mime_type=imagen_data["content_type"],
                        data=imagen_data["imagen_base64"],
                    )
                ),
                types.Part(text=prompt),
            ])
        ]
        
        # 4. Llamar a Gemini con reintentos
        resultado = gemini_client.generate_content(
            model="gemini-2.0-flash-lite",
            contents=contents,
            context="vision_comprobante",
        )
        
        if not resultado.success:
            return resultado
        
        # 5. Parsear respuesta
        try:
            texto = resultado.data.text
            analysis = VisionAnalysisResult.from_text(texto)
            return GeminiResult.ok(
                data=analysis,
                raw_response=texto,
                retries_used=resultado.retries_used,
            )
        except Exception as e:
            logger.error(f"[VISION] Error parseando respuesta: {e}")
            return GeminiResult.fail(
                error_type="PARSE_ERROR",
                message=f"Error al parsear respuesta de Gemini: {str(e)}",
                retries_used=resultado.retries_used,
            )


# Instancia global del adaptador de vision
gemini_vision = GeminiVisionAdapter()
