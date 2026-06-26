import logging
from typing import Optional
from application.whatsapp_app_service import WhatsAppAppService

logger = logging.getLogger("boy.gemini.payments")

# Instancia del servicio (se inicia una vez)
_app_service: Optional[WhatsAppAppService] = None


def _get_app_service() -> WhatsAppAppService:
    global _app_service
    if _app_service is None:
        _app_service = WhatsAppAppService()
    return _app_service


def consultar_estado_pago(documento: str, club_id: str) -> dict:
    """Funcion que Gemini llama via function calling.
    
    Responde a "¿cuánto debo?" y "¿qué he pagado?".
    
    Args:
        documento: Numero de documento del deportista
        club_id: ID del club (proporcionado por el contexto)
    
    Returns:
        dict con el resumen financiero
    """
    try:
        service = _get_app_service()
        
        # Buscar deportista por documento
        from services.supabase_client import supabase
        deportista = supabase.table("deportistas")\
            .select("id, nombre, categoria")\
            .eq("club_id", club_id)\
            .eq("documento", documento)\
            .single()\
            .execute()
        
        if not deportista.data:
            return {
                "encontrado": False,
                "mensaje": "No se encontró ningún deportista con ese documento.",
            }
        
        d = deportista.data
        
        # Obtener resumen financiero
        resumen = service.resumen_estado(club_id, d["id"])
        
        # Formatear respuesta para Gemini
        partes = []
        partes.append(f"Deportista: {d['nombre']} ({d['categoria']})")
        
        if resumen["cantidad_pendientes"] > 0:
            partes.append(f"\nDebes: ${resumen['total_debe']:,.0f} COP")
            partes.append(f"({resumen['cantidad_pendientes']} obligacion(es) pendiente(s))")
            
            # Detalle de pendientes
            for ob in resumen["obligaciones_pendientes"][:3]:
                periodo = ob.get("periodo", "sin periodo")
                saldo = ob.get("saldo_pendiente", 0)
                partes.append(f"  - {periodo}: ${saldo:,.0f}")
        else:
            partes.append("\nNo tienes obligaciones pendientes.")
        
        if resumen["cantidad_pagadas"] > 0:
            partes.append(f"\nPagado este año: ${resumen['total_pagado']:,.0f} COP")
            partes.append(f"({resumen['cantidad_pagadas']} pago(s) confirmado(s))")
        
        return {
            "encontrado": True,
            "mensaje": "\n".join(partes),
        }
        
    except Exception as e:
        logger.error(f"[GEMINI_PAYMENTS] Error: {e}", exc_info=True)
        return {
            "encontrado": False,
            "mensaje": "Hubo un error al consultar tu estado. Intenta de nuevo.",
        }
