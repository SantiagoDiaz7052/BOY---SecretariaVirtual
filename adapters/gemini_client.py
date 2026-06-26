import logging
import time
import traceback
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError
from dotenv import load_dotenv
import os

from adapters.gemini_models import GeminiResult

load_dotenv()

logger = logging.getLogger("boy.gemini")


class GeminiClient:
    """Cliente resiliente para Gemini.
    
    Caracteristicas:
    - Reintentos con backoff exponencial para 503
    - Manejo de timeouts y errores de red
    - Logging completo de errores
    - Nunca lanza excepciones al caller
    """
    
    MAX_RETRIES = 5
    BASE_DELAY = 2  # segundos
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self) -> genai.Client:
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY no configurada")
            self._client = genai.Client(api_key=api_key)
        return self._client
    
    def _delay_for_retry(self, attempt: int) -> float:
        """Calcula el delay exponencial: 1s, 2s, 4s."""
        return self.BASE_DELAY * (2 ** attempt)
    
    def _classify_error(self, exception: Exception) -> str:
        """Clasifica el tipo de error para el caller."""
        if isinstance(exception, ServerError):
            if "503" in str(exception) or "UNAVAILABLE" in str(exception):
                return "SERVICE_UNAVAILABLE"
            elif "429" in str(exception) or "RESOURCE_EXHAUSTED" in str(exception):
                return "RATE_LIMITED"
            return "SERVER_ERROR"
        elif isinstance(exception, ClientError):
            if "429" in str(exception) or "RESOURCE_EXHAUSTED" in str(exception):
                return "RATE_LIMITED"
            return "CLIENT_ERROR"
        elif isinstance(exception, TimeoutError):
            return "TIMEOUT"
        elif isinstance(exception, ConnectionError):
            return "CONNECTION_ERROR"
        else:
            return "UNKNOWN_ERROR"
    
    def _log_error(self, exception: Exception, error_type: str, 
                   context: str, attempt: int) -> None:
        """Registra el error completo en logs."""
        logger.error(
            f"[GEMINI_ERROR] context={context} | "
            f"error_type={error_type} | "
            f"attempt={attempt + 1}/{self.MAX_RETRIES} | "
            f"exception={type(exception).__name__} | "
            f"message={str(exception)}"
        )
        logger.debug(
            f"[GEMINI_STACKTRACE] {traceback.format_exc()}"
        )
    
    def generate_content(self, model: str, contents: list, 
                         config: Optional[types.GenerateContentConfig] = None,
                         context: str = "general") -> GeminiResult:
        """Genera contenido con reintentos y manejo de errores.
        
        Args:
            model: Modelo de Gemini a usar
            contents: Lista de Content objects
            config: Configuracion generativa
            context: Contexto para logs (ej: "vision", "chat")
        
        Returns:
            GeminiResult con success=True o success=False
        """
        last_exception = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                
                # Verificar que la respuesta tenga candidates
                if not response.candidates:
                    return GeminiResult.fail(
                        error_type="EMPTY_RESPONSE",
                        message="Gemini devolvio respuesta vacia",
                        retries_used=attempt,
                    )
                
                return GeminiResult.ok(
                    data=response,
                    raw_response=response.text if response.text else None,
                    retries_used=attempt,
                )
                
            except ServerError as e:
                last_exception = e
                error_type = self._classify_error(e)
                self._log_error(e, error_type, context, attempt)
                
                # Reintentar solo en 503 y 429
                if error_type in ("SERVICE_UNAVAILABLE", "RATE_LIMITED"):
                    if attempt < self.MAX_RETRIES - 1:
                        delay = self._delay_for_retry(attempt)
                        logger.info(
                            f"[GEMINI_RETRY] Reintentando en {delay}s "
                            f"(intento {attempt + 2}/{self.MAX_RETRIES})"
                        )
                        time.sleep(delay)
                        continue
                
                # Otros errores del servidor no se reintentan
                return GeminiResult.fail(
                    error_type=error_type,
                    message=f"Error del servidor Gemini: {str(e)} Vuelve a enviar tu mensaje 😉",
                    retries_used=attempt,
                )
                
            except ClientError as e:
                last_exception = e
                error_type = self._classify_error(e)
                self._log_error(e, error_type, context, attempt)
                
                # Rate limits se reintentan
                if error_type == "RATE_LIMITED" and attempt < self.MAX_RETRIES - 1:
                    delay = self._delay_for_retry(attempt)
                    logger.info(
                        f"[GEMINI_RETRY] Rate limit, reintentando en {delay}s"
                    )
                    time.sleep(delay)
                    continue
                
                return GeminiResult.fail(
                    error_type=error_type,
                    message=f"Error de cliente Gemini: {str(e)}",
                    retries_used=attempt,
                )
                
            except TimeoutError as e:
                last_exception = e
                self._log_error(e, "TIMEOUT", context, attempt)
                
                if attempt < self.MAX_RETRIES - 1:
                    delay = self._delay_for_retry(attempt)
                    logger.info(
                        f"[GEMINI_RETRY] Timeout, reintentando en {delay}s"
                    )
                    time.sleep(delay)
                    continue
                
                return GeminiResult.fail(
                    error_type="TIMEOUT",
                    message="Gemini no responde (timeout)",
                    retries_used=attempt,
                )
                
            except ConnectionError as e:
                last_exception = e
                self._log_error(e, "CONNECTION_ERROR", context, attempt)
                
                if attempt < self.MAX_RETRIES - 1:
                    delay = self._delay_for_retry(attempt)
                    logger.info(
                        f"[GEMINI_RETRY] Error de red, reintentando en {delay}s"
                    )
                    time.sleep(delay)
                    continue
                
                return GeminiResult.fail(
                    error_type="CONNECTION_ERROR",
                    message="No se pudo conectar con Gemini",
                    retries_used=attempt,
                )
                
            except Exception as e:
                last_exception = e
                self._log_error(e, "UNKNOWN_ERROR", context, attempt)
                return GeminiResult.fail(
                    error_type="UNKNOWN_ERROR",
                    message=f"Error inesperado: {str(e)}",
                    retries_used=attempt,
                )
        
        # No deberia llegar aqui, pero por seguridad
        return GeminiResult.fail(
            error_type="MAX_RETRIES_EXCEEDED",
            message="Se agotaron los reintentos",
            retries_used=self.MAX_RETRIES,
        )


# Instancia global del cliente resiliente
gemini_client = GeminiClient()
