import logging
from typing import Optional
from datetime import datetime

from domain.proceso_pago import EventoProcesoPago
from application.proceso_pago_service import ProcesoPagoService
from application.obligacion_service import ObligacionService
from application.config_service import ConfiguracionClubService
from adapters.gemini_vision import gemini_vision
from services.supabase_client import supabase

logger = logging.getLogger("boy.whatsapp.app")


class WhatsAppAppService:
    """Servicio de aplicacion para el flujo de WhatsApp.
    
    Coordina:
    - Busqueda de club y deportista
    - Proceso de pago conversacional
    - Analisis de comprobantes
    - Registro de pagos
    
    REGLAS:
    - El router NUNCA accede directamente a Supabase
    - Toda logica de negocio pasa por este servicio
    - Si Gemini falla, el proceso se mantiene activo
    """

    def __init__(self):
        self.proceso_service = ProcesoPagoService()
        self.obligacion_service = ObligacionService()
        self.config_service = ConfiguracionClubService()

    def buscar_club(self, numero_whatsapp: str) -> Optional[dict]:
        """Busca un club por su numero de WhatsApp."""
        resultado = supabase.table("clubs")\
            .select("*")\
            .eq("whatsapp_number", numero_whatsapp)\
            .eq("activo", True)\
            .single()\
            .execute()
        return resultado.data

    def buscar_deportista(self, club_id: str, telefono: str) -> Optional[dict]:
        """Busca un deportista por telefono en un club."""
        telefono_limpio = telefono.replace("whatsapp:+57", "").replace("whatsapp:+", "")
        resultado = supabase.table("deportistas")\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("telefono", telefono_limpio)\
            .execute()
        
        if resultado.data:
            return resultado.data[0]
        return None

    def obtener_obligacion_pendiente(self, club_id: str, 
                                      deportista_id: str) -> Optional[dict]:
        """Obtiene la obligacion pendiente de mensualidad de un deportista."""
        # Buscar concepto Mensualidad
        concepto = supabase.table("conceptos")\
            .select("id")\
            .eq("club_id", club_id)\
            .eq("nombre", "Mensualidad")\
            .eq("activo", True)\
            .single()\
            .execute()
        
        if not concepto.data:
            return None

        # Buscar obligacion pendiente
        obligacion = supabase.table("obligaciones")\
            .select("id, monto_total, periodo, fecha_limite")\
            .eq("club_id", club_id)\
            .eq("deportista_id", deportista_id)\
            .eq("concepto_id", concepto.data["id"])\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if obligacion.data:
            return obligacion.data[0]
        return None

    def procesar_imagen_pago(self, club_id: str, deportista_id: str,
                              deportista_nombre: str, imagen_url: str) -> dict:
        """Procesa una imagen de comprobante de pago.
        
        Flujo:
        1. Buscar obligacion pendiente
        2. Iniciar/procesar ProcesoPago
        3. Analizar comprobante con Gemini Vision
        4. Registrar resultado
        5. Retornar respuesta para el usuario
        """
        # 1. Buscar obligacion pendiente
        obligacion = self.obtener_obligacion_pendiente(club_id, deportista_id)
        
        if not obligacion:
            return {
                "exito": False,
                "mensaje": ("No encontré una mensualidad pendiente. "
                           "Si crees que es un error, escribe *10* para hablar con Ivonn."),
            }

        monto_esperado = float(obligacion["monto_total"])
        obligacion_id = obligacion["id"]

        # 2. Iniciar proceso de pago
        proceso = self.proceso_service.iniciar_proceso(
            club_id=club_id,
            deportista_id=deportista_id,
            obligacion_id=obligacion_id,
        )

        # 3. Registrar comprobante recibido
        self.proceso_service.registrar_comprobante_recibido(
            proceso["id"], imagen_url
        )

        # 4. Analizar con Gemini Vision
        analisis = gemini_vision.analizar_comprobante(imagen_url, monto_esperado)

        if not analisis.success:
            # Gemini fallo - proceso se mantiene activo para reintentar
            self.proceso_service.registrar_analisis_gemini(
                proceso["id"], exito=False, 
                error_type=analisis.error_type
            )
            return {
                "exito": False,
                "mensaje": ("En este momento estoy teniendo un problema temporal al analizar el comprobante. "
                           "Intentalo nuevamente en unos minutos."),
                "proceso_id": proceso["id"],
                "error_type": analisis.error_type,
            }

        # 5. Verificar si es comprobante valido
        analysis = analisis.data
        if not analysis.es_comprobante:
            self.proceso_service.registrar_analisis_gemini(
                proceso["id"], exito=True,
                analisis=analysis.to_dict()
            )
            return {
                "exito": False,
                "mensaje": ("La imagen no parece ser un comprobante de pago válido. "
                           "Por favor envía una captura clara de tu pago por Nequi, "
                           "Daviplata o transferencia bancaria."),
                "proceso_id": proceso["id"],
            }

        # 6. Verificar monto
        config = self.config_service.obtener_por_club(club_id)
        tolerancia = config.tolerancia_monto if config else 5000
        
        if analysis.monto_detectado and abs(analysis.monto_detectado - monto_esperado) > tolerancia:
            self.proceso_service.registrar_analisis_gemini(
                proceso["id"], exito=True,
                analisis=analysis.to_dict()
            )
            return {
                "exito": False,
                "mensaje": (f"El monto detectado (${analysis.monto_detectado:,.0f}) no coincide "
                           f"con tu mensualidad (${monto_esperado:,.0f}).\n"
                           f"¿Tienes alguna duda? Escribe *10* para hablar con Ivonn."),
                "proceso_id": proceso["id"],
            }

        # 7. Registrar analisis exitoso
        self.proceso_service.registrar_analisis_gemini(
            proceso["id"], exito=True,
            analisis=analysis.to_dict()
        )

        # 8. Registrar pago pendiente
        mes_anio = obligacion.get("periodo") or datetime.now().strftime("%Y-%m")
        
        pago = supabase.table("pagos").insert({
            "club_id": club_id,
            "deportista_id": deportista_id,
            "concepto_id": supabase.table("conceptos")\
                .select("id")\
                .eq("club_id", club_id)\
                .eq("nombre", "Mensualidad")\
                .eq("activo", True)\
                .single()\
                .execute().data["id"],
            "monto": monto_esperado,
            "monto_detectado": analysis.monto_detectado,
            "referencia_detectada": analysis.referencia,
            "fecha_detectada": analysis.fecha,
            "tipo_pago": analysis.plataforma or "desconocido",
            "tipo": "mensualidad",
            "mes_anio": mes_anio,
            "imagen_url": imagen_url,
            "estado": "pendiente_verificacion",
            "wompi_data": {
                "analisis_gemini": analysis.texto_completo,
                "proceso_pago_id": proceso["id"],
            }
        }).execute()

        if pago.data:
            self.proceso_service.registrar_pago_creado(
                proceso["id"], pago.data[0]["id"]
            )

        return {
            "exito": True,
            "mensaje": (f"Comprobante recibido, {deportista_nombre}.\n"
                       f"Monto: ${monto_esperado:,.0f} | Mes: {mes_anio}\n"
                       f"Tu pago está en verificación. Te confirmamos en breve."),
            "proceso_id": proceso["id"],
            "pago_id": pago.data[0]["id"] if pago.data else None,
        }

    def resumen_estado(self, club_id: str, deportista_id: str) -> dict:
        """Obtiene el resumen financiero de un deportista."""
        return self.obligacion_service.resumen_estado(club_id, deportista_id)
