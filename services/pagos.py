import logging
from services.supabase_client import supabase
from adapters.gemini_vision import gemini_vision
from adapters.gemini_models import GeminiResult

logger = logging.getLogger("boy.pagos")


def analizar_comprobante(imagen_url: str, monto_esperado: float) -> dict:
    """Descarga la imagen y la analiza con Gemini Vision.
    
    Ahora usa el adaptador resiliente. Si Gemini falla,
    retorna un dict con error en lugar de lanzar excepcion.
    """
    resultado: GeminiResult = gemini_vision.analizar_comprobante(
        imagen_url, monto_esperado
    )
    
    if resultado.success:
        analysis = resultado.data
        return {
            "es_comprobante": analysis.es_comprobante,
            "monto_detectado": analysis.monto_detectado,
            "referencia": analysis.referencia,
            "fecha": analysis.fecha,
            "plataforma": analysis.plataforma,
            "texto_completo": analysis.texto_completo,
            "error": None,
            "gemini_retries": resultado.retries_used,
        }
    else:
        # Gemini fallo - retornar error controlado
        logger.warning(
            f"[PAGOS] Gemini Vision fallo: "
            f"error_type={resultado.error_type} | "
            f"message={resultado.message} | "
            f"retries={resultado.retries_used}"
        )
        return {
            "es_comprobante": False,
            "monto_detectado": None,
            "referencia": None,
            "fecha": None,
            "plataforma": None,
            "texto_completo": None,
            "error": resultado.message,
            "error_type": resultado.error_type,
            "gemini_retries": resultado.retries_used,
        }


def registrar_pago_pendiente(club_id: str, deportista_id: str, 
                              monto_esperado: float, mes_anio: str,
                              imagen_url: str, analisis: dict) -> dict:
    """Registra el pago en Supabase como pendiente de verificacion"""
    
    pago = supabase.table("pagos").insert({
        "club_id": club_id,
        "deportista_id": deportista_id,
        "monto": monto_esperado,
        "monto_detectado": analisis.get("monto_detectado"),
        "referencia_detectada": analisis.get("referencia"),
        "fecha_detectada": analisis.get("fecha"),
        "tipo_pago": analisis.get("plataforma", "desconocido"),
        "tipo": "mensualidad",
        "mes_anio": mes_anio,
        "imagen_url": imagen_url,
        "estado": "pendiente_verificacion",
        "wompi_data": {
            "analisis_gemini": analisis.get("texto_completo"),
            "error_gemini": analisis.get("error"),
            "error_type": analisis.get("error_type"),
            "gemini_retries": analisis.get("gemini_retries", 0),
        }
    }).execute()

    return pago.data[0] if pago.data else {}


def obtener_pagos_pendientes(club_id: str) -> list:
    """Para el panel de admin - lista pagos por verificar"""
    resultado = supabase.table("pagos")\
        .select("*, deportistas(nombre, documento)")\
        .eq("club_id", club_id)\
        .eq("estado", "pendiente_verificacion")\
        .order("created_at", desc=True)\
        .execute()
    return resultado.data or []


def aprobar_pago(pago_id: str, verificado_por: str = "admin") -> bool:
    """Admin aprueba el pago"""
    supabase.table("pagos").update({
        "estado": "aprobado",
        "verificado_por": verificado_por
    }).eq("id", pago_id).execute()

    # Actualizar mensualidad si existe
    pago = supabase.table("pagos").select("*").eq("id", pago_id).single().execute()
    if pago.data and pago.data.get("deportista_id") and pago.data.get("mes_anio"):
        supabase.table("mensualidades").update({
            "estado": "pagado",
            "pagado_at": "now()"
        }).eq("deportista_id", pago.data["deportista_id"])\
          .eq("mes_anio", pago.data["mes_anio"])\
          .execute()
    return True


def rechazar_pago(pago_id: str, motivo: str = "") -> bool:
    """Admin rechaza el pago"""
    supabase.table("pagos").update({
        "estado": "rechazado",
        "notas_verificacion": motivo
    }).eq("id", pago_id).execute()
    return True
