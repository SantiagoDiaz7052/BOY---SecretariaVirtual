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


def iniciar_proceso_pago(documento: str, club_id: str) -> dict:
    """Funcion que Gemini llama via function calling.
    
    Responde a "quiero pagar", "pagar mensualidad", "enviar comprobante".
    
    Flujo:
    1. Buscar deportista por documento
    2. Buscar obligacion pendiente
    3. Iniciar ProcesoPago
    4. Retornar instrucciones de pago
    
    Args:
        documento: Numero de documento del deportista
        club_id: ID del club (proporcionado por el contexto)
    
    Returns:
        dict con instrucciones de pago
    """
    try:
        service = _get_app_service()
        
        # Buscar deportista por documento
        from services.supabase_client import supabase
        deportista = supabase.table("deportistas")\
            .select("id, nombre, categoria, telefono")\
            .eq("club_id", club_id)\
            .eq("documento", documento)\
            .single()\
            .execute()
        
        if not deportista.data:
            return {
                "exito": False,
                "mensaje": "No se encontró ningún deportista con ese documento.",
            }
        
        d = deportista.data
        
        # Buscar obligacion pendiente
        obligacion = service.obtener_obligacion_pendiente(club_id, d["id"])
        
        if not obligacion:
            return {
                "exito": False,
                "mensaje": (f"{d['nombre']}, no tienes mensualidades pendientes. "
                           "Si crees que es un error, escribe *10* para hablar con Ivonn."),
            }
        
        monto = float(obligacion["monto_total"])
        periodo = obligacion.get("periodo", "actual")
        
        # Iniciar proceso de pago
        proceso = service.proceso_service.iniciar_proceso(
            club_id=club_id,
            deportista_id=d["id"],
            obligacion_id=obligacion["id"],
        )
        
        # Obtener llave Bre-B del club
        config = service.config_service.obtener_por_club(club_id)
        llave_bre = config.llave_bre_b if config and config.llave_bre_b else "No configurada"
        
        # Formatear instrucciones
        instrucciones = (
            f"Perfecto {d['nombre']}, encontre tu mensualidad pendiente:\n\n"
            f"Monto: ${monto:,.0f} COP\n"
            f"Periodo: {periodo}\n\n"
            f"Datos de pago:\n"
            f"Llave Bre-B: {llave_bre}\n\n"
            f"Una vez realices el pago, envia el comprobante por imagen "
            f"y lo verificaremos automaticamente."
        )
        
        return {
            "exito": True,
            "mensaje": instrucciones,
            "proceso_id": proceso["id"],
            "monto": monto,
            "periodo": periodo,
        }
        
    except Exception as e:
        logger.error(f"[GEMINI_PAYMENTS] Error iniciar_proceso_pago: {e}", exc_info=True)
        return {
            "exito": False,
            "mensaje": "Hubo un error al iniciar el proceso de pago. Intenta de nuevo.",
        }
