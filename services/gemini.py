import logging
from adapters.gemini_chat import gemini_chat
from adapters.gemini_models import GeminiResult

logger = logging.getLogger("boy.gemini")


def get_respuesta(system_prompt: str, historial: list, mensaje_nuevo: str, 
                  club_id: str = None) -> str:
    """Obtiene respuesta de Gemini para un mensaje.
    
    Ahora usa el adaptador resiliente. Si Gemini falla,
    retorna un mensaje de error amigable en lugar de crash.
    """
    resultado: GeminiResult = gemini_chat.get_respuesta(
        system_prompt=system_prompt,
        historial=historial,
        mensaje_nuevo=mensaje_nuevo,
        club_id=club_id,
    )
    
    if resultado.success:
        return resultado.data
    else:
        # Gemini fallo - retornar mensaje amigable
        logger.warning(
            f"[GEMINI] Chat fallo: "
            f"error_type={resultado.error_type} | "
            f"message={resultado.message} | "
            f"retries={resultado.retries_used}"
        )
        
        # Mensajes amigables segun tipo de error
        if resultado.error_type == "SERVICE_UNAVAILABLE":
            return (
                "En este momento estoy teniendo un problema temporal. "
                "Intentalo de nuevo en unos minutos."
            )
        elif resultado.error_type == "RATE_LIMITED":
            return (
                "Estoy recibiendo muchas solicitudes. "
                "Un momento por favor e intentalo de nuevo."
            )
        elif resultado.error_type == "TIMEOUT":
            return (
                "La respuesta esta tardando mas de lo normal. "
                "Intentalo de nuevo en un momento."
            )
        else:
            return (
                "Tengo un problema temporal para procesar tu mensaje. "
                "Intentalo de nuevo en unos minutos."
            )
