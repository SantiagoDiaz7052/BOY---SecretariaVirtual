import logging
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from application.whatsapp_app_service import WhatsAppAppService
from application.mensajes_app_service import mensajes_service

logger = logging.getLogger("boy.webhook")

router = APIRouter()

# Instancia del servicio de aplicacion para pagos
_app_service = WhatsAppAppService()


@router.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request):
    try:
        form = await request.form()

        numero_usuario = form.get("From", "")
        numero_club    = form.get("To", "")
        mensaje        = form.get("Body", "").strip()
        nombre         = form.get("ProfileName", "")
        num_media      = int(form.get("NumMedia", "0"))
        media_url      = form.get("MediaUrl0", "")
        media_type     = form.get("MediaContentType0", "")

        # Si envió una imagen, verificar si es comprobante de pago
        if num_media > 0 and media_url and "image" in media_type:
            respuesta = _procesar_imagen_pago(
                numero_usuario, numero_club, nombre, media_url
            )
        else:
            respuesta = _procesar_mensaje(
                numero_usuario, numero_club, nombre, mensaje
            )

    except Exception as e:
        logger.error(f"[WEBHOOK] Error inesperado: {e}", exc_info=True)
        respuesta = "Ocurrió un error inesperado. Por favor intenta de nuevo."

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{respuesta}</Message>
</Response>"""

    return PlainTextResponse(content=twiml, media_type="application/xml")


def _procesar_mensaje(numero_usuario: str, numero_club: str,
                       nombre: str, mensaje: str) -> str:
    """Procesa un mensaje de texto via capa de aplicacion.
    
    Flujo:
    1. Buscar club
    2. Obtener/crear conversacion
    3. Gemini procesa (puede llamar funciones)
    4. Guardar conversacion
    5. Retornar respuesta
    """
    return mensajes_service.procesar_mensaje(
        numero_usuario, numero_club, nombre, mensaje
    )


def _procesar_imagen_pago(numero_usuario: str, numero_club: str,
                           nombre: str, imagen_url: str) -> str:
    """Procesa una imagen de comprobante de pago.
    
    Flujo completo via capa de aplicacion:
    1. Buscar club
    2. Buscar deportista
    3. Analizar comprobante con Gemini Vision
    4. Validar (logica de negocio)
    5. Registrar pago
    6. Retornar respuesta
    """
    # 1. Buscar club
    club = _app_service.buscar_club(numero_club)
    if not club:
        return "Lo siento, servicio no disponible."

    club_id = club["id"]

    # 2. Buscar deportista
    deportista = _app_service.buscar_deportista(club_id, numero_usuario)
    if not deportista:
        return ("No encontré tu registro en el club. "
                "¿Ya estás inscrito? Si no, escribe *1* para inscribirte.")

    # 3. Procesar comprobante (Gemini Vision + logica de negocio + registro)
    resultado = _app_service.procesar_imagen_pago(
        club_id=club_id,
        deportista_id=deportista["id"],
        deportista_nombre=deportista["nombre"],
        imagen_url=imagen_url,
    )

    return resultado["mensaje"]
