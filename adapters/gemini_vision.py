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
    - Descarga la imagen desde una URL
    - La envia a Gemini Vision para extraer datos
    - Retorna VisionAnalysisResult (DTO puro)
    - NO conoce Obligaciones, Pagos, Clubes ni reglas de negocio
    
    El adaptador SOLO extrae datos de la imagen.
    La logica de negocio (comparar montos, verificar obligaciones)
    permanece en los servicios del dominio.
    """
    
    def __init__(self):
        self._twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self._twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    def _descargar_imagen(self, imagen_url: str) -> GeminiResult:
        """Descarga la imagen desde la URL proporcionada."""
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
    
    def _construir_prompt(self, monto_sugerido: float = None) -> str:
        """Construye el prompt para analizar el comprobante.
        
        El prompt SOLO pide extraer datos visibles en la imagen.
        NO incluye logica de negocio ni comparaciones.
        """
        prompt = """Analiza esta imagen y determina si es un comprobante de pago colombiano.

Extrae la siguiente informacion SOLO si es visible en la imagen:

MONTO: (solo el numero, sin puntos ni comas, ejemplo: 90000. Si no se ve, escribe NO_VISIBLE)
FECHA: (formato YYYY-MM-DD, si no se ve claramente escribe NO_VISIBLE)
REFERENCIA: (numero de referencia o transaccion, si no hay escribe NO_VISIBLE)
ES_COMPROBANTE: (SI si parece una imagen legitima de pago, NO si no lo es)
PLATAFORMA: (Nequi, Daviplata, transferencia bancaria, o DESCONOCIDA)

Responde SOLO con el formato pedido, sin explicaciones adicionales."""

        if monto_sugerido:
            prompt += f"\n\nNota: Se esperaba un pago de aproximadamente ${monto_sugerido:,.0f} COP. Esto es solo como contexto, no como validacion."

        return prompt

    def analizar_imagen(self, imagen_url: str, 
                        monto_sugerido: float = None) -> GeminiResult:
        """Analiza una imagen y extrae datos de comprobante de pago.
        
        Args:
            imagen_url: URL de la imagen a analizar
            monto_sugerido: Monto esperado (opcional, solo para contexto del prompt)
        
        Returns:
            GeminiResult con VisionAnalysisResult como data
            
        Este metodo NO valida montos, NO verifica obligaciones.
        Solo extrae datos de la imagen.
        """
        # 1. Descargar imagen
        descarga = self._descargar_imagen(imagen_url)
        if not descarga.success:
            return descarga
        
        imagen_data = descarga.data
        
        # 2. Construir prompt (sin logica de negocio)
        prompt = self._construir_prompt(monto_sugerido)
        
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
        
        # 5. Parsear respuesta a DTO
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


# Importar types aqui para evitar circular imports
from google.genai import types

# Instancia global del adaptador de vision
gemini_vision = GeminiVisionAdapter()
