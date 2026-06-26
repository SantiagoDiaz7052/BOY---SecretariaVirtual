import logging
from typing import Optional
from application.deportista_service import DeportistaService
from application.obligacion_service import ObligacionService
from application.proceso_pago_service import ProcesoPagoService
from application.config_service import ConfiguracionClubService
from application.temporada_service import TemporadaService

logger = logging.getLogger("boy.gemini.payments")


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
        deportista_service = DeportistaService()
        obligacion_service = ObligacionService()
        
        # Buscar deportista por documento
        deportista = deportista_service.buscar_por_documento(club_id, documento)
        
        if not deportista:
            return {
                "encontrado": False,
                "mensaje": "No se encontro ningun deportista con ese documento.",
            }
        
        # Obtener resumen financiero
        resumen = obligacion_service.resumen_estado(club_id, deportista.id)
        
        # Formatear respuesta para Gemini
        partes = []
        partes.append(f"Deportista: {deportista.nombre} ({deportista.nivel})")
        partes.append(f"Estado: {deportista.estado.upper()}")
        
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
            partes.append(f"\nPagado este anio: ${resumen['total_pagado']:,.0f} COP")
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
        deportista_service = DeportistaService()
        obligacion_service = ObligacionService()
        proceso_service = ProcesoPagoService()
        config_service = ConfiguracionClubService()
        temporada_service = TemporadaService()
        
        # Buscar deportista por documento
        deportista = deportista_service.buscar_por_documento(club_id, documento)
        
        if not deportista:
            return {
                "exito": False,
                "mensaje": "No se encontro ningun deportista con ese documento.",
            }
        
        # Obtener temporada activa
        temporada = temporada_service.obtener_activa(club_id)
        if not temporada:
            return {
                "exito": False,
                "mensaje": "No hay temporada activa. Contacta al administrador.",
            }
        
        # Buscar obligacion pendiente
        obligaciones = obligacion_service.listar_por_deportista(
            club_id, deportista.id, solo_pendientes=True
        )
        
        if not obligaciones:
            return {
                "exito": False,
                "mensaje": (
                    f"{deportista.nombre}, no tienes mensualidades pendientes. "
                    "Si crees que es un error, escribe *10* para hablar con Ivonn."
                ),
            }
        
        # Usar la primera obligacion pendiente
        obligacion = obligaciones[0]
        monto = float(obligacion["monto_total"])
        periodo = obligacion.get("periodo", "actual")
        
        # Iniciar proceso de pago
        proceso = proceso_service.iniciar_proceso(
            club_id=club_id,
            temporada_id=temporada.id,
            deportista_id=deportista.id,
            obligacion_id=obligacion["id"],
        )
        
        # Obtener llave Bre-B del club
        config = config_service.obtener_por_club(club_id)
        llave_bre = config.llave_bre_b if config and config.llave_bre_b else "No configurada"
        
        # Formatear instrucciones
        instrucciones = (
            f"Perfecto {deportista.nombre}, encontre tu mensualidad pendiente:\n\n"
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
