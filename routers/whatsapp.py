import logging
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from services.mensajes import procesar_mensaje
from application.whatsapp_app_service import WhatsAppAppService

logger = logging.getLogger("boy.webhook")

router = APIRouter()

# Instancia del servicio de aplicacion
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
            respuesta = await _procesar_imagen_pago(
                numero_usuario, numero_club, nombre, media_url
            )
        else:
            respuesta = _procesar_mensaje(numero_usuario, numero_club, nombre, mensaje)

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
    """Procesa un mensaje de texto usando el servicio de mensajes."""
    return procesar_mensaje(numero_usuario, numero_club, nombre, mensaje)


async def _procesar_imagen_pago(numero_usuario: str, numero_club: str,
                                 nombre: str, imagen_url: str) -> str:
    """Procesa una imagen de comprobante de pago.
    
    FLUJO COMPLETO (sin acceder directamente a Supabase):
    1. Buscar club via servicio de aplicacion
    2. Buscar deportista via servicio de aplicacion
    3. Procesar comprobante via servicio de aplicacion
    4. Retornar respuesta
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

    # 3. Procesar comprobante
    resultado = _app_service.procesar_imagen_pago(
        club_id=club_id,
        deportista_id=deportista["id"],
        deportista_nombre=deportista["nombre"],
        imagen_url=imagen_url,
    )

    return resultado["mensaje"]
