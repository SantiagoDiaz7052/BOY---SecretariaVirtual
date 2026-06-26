import logging
import hashlib
from typing import Optional
from datetime import datetime

from domain.proceso_pago import EventoProcesoPago
from application.proceso_pago_service import ProcesoPagoService
from application.obligacion_service import ObligacionService
from application.config_service import ConfiguracionClubService
from application.deportista_service import DeportistaService
from application.contexto_service import ContextoConversacionalService
from application.temporada_service import TemporadaService
from adapters.gemini_vision import gemini_vision
from services.supabase_client import supabase

logger = logging.getLogger("boy.whatsapp.app")


class WhatsAppAppService:
    """Servicio de aplicacion para el flujo de WhatsApp.
    
    Coordina:
    - Busqueda de club y deportista
    - Contexto conversacional
    - Multi-hijos
    - Proceso de pago conversacional
    - Analisis de comprobantes
    - Registro de pagos
    - Deteccion de duplicados multi-capa
    
    REGLAS:
    - El router NUNCA accede directamente a Supabase
    - Toda logica de negocio pasa por este servicio
    - Si Gemini falla, el proceso se mantiene activo
    - Un numero puede tener varios deportistas (multi-hijo)
    """

    def __init__(self):
        self.proceso_service = ProcesoPagoService()
        self.obligacion_service = ObligacionService()
        self.config_service = ConfiguracionClubService()
        self.deportista_service = DeportistaService()
        self.contexto_service = ContextoConversacionalService()
        self.temporada_service = TemporadaService()

    def buscar_club(self, numero_whatsapp: str) -> Optional[dict]:
        """Busca un club por su numero de WhatsApp."""
        resultado = supabase.table("clubs")\
            .select("*")\
            .eq("whatsapp_number", numero_whatsapp)\
            .eq("activo", True)\
            .single()\
            .execute()
        return resultado.data

    def buscar_deportistas_por_whatsapp(self, club_id: str, 
                                        numero_whatsapp: str) -> list:
        """Busca todos los deportistas asociados a un numero de WhatsApp.
        
        Soporta multi-hijo: un mismo numero puede tener varios deportistas.
        """
        return self.deportista_service.listar_por_whatsapp(club_id, numero_whatsapp)

    def obtener_o_crear_contexto(self, club_id: str, 
                                 numero_whatsapp: str) -> dict:
        """Obtiene o crea el contexto conversacional."""
        contexto = self.contexto_service.obtener_o_crear(club_id, numero_whatsapp)
        return contexto.to_dict()

    def actualizar_contexto(self, contexto_id: str, **kwargs) -> dict:
        """Actualiza el contexto conversacional."""
        contexto = self.contexto_service.repo.actualizar(contexto_id, kwargs)
        return contexto.to_dict()

    def procesar_imagen_pago(self, club_id: str, deportista_id: str,
                              deportista_nombre: str, imagen_url: str,
                              contexto_id: Optional[str] = None,
                              preinscripcion_id: Optional[str] = None) -> dict:
        """Procesa una imagen de comprobante de pago.
        
        Flujo:
        1. Buscar obligacion pendiente
        2. Iniciar/procesar ProcesoPago
        3. Analizar comprobante con Gemini Vision
        4. Verificar duplicados multi-capa
        5. Registrar resultado
        6. Retornar respuesta para el usuario
        """
        # 1. Buscar obligacion pendiente
        obligaciones = self.obligacion_service.listar_por_deportista(
            club_id, deportista_id, solo_pendientes=True
        )
        
        if not obligaciones:
            return {
                "exito": False,
                "mensaje": ("No encontré una mensualidad pendiente. "
                           "Si crees que es un error, escribe *10* para hablar con Ivonn."),
            }

        obligacion = obligaciones[0]
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
        analisis = gemini_vision.analizar_imagen(imagen_url, monto_sugerido=monto_esperado)

        if not analisis.success:
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

        # 5. Verificar duplicados multi-capa
        analysis = analisis.data
        duplicado = self._verificar_duplicado(
            club_id=club_id,
            deportista_id=deportista_id,
            imagen_url=imagen_url,
            monto_detectado=analysis.monto_detectado,
            fecha_detectada=analysis.fecha_detectada,
            referencia_detectada=analysis.referencia_detectada,
            plataforma_detectada=analysis.plataforma_detectada,
        )
        
        if duplicado == "DUPLICADO":
            self.proceso_service.registrar_analisis_gemini(
                proceso["id"], exito=True,
                analisis=analysis.to_dict()
            )
            return {
                "exito": False,
                "mensaje": ("Este comprobante ya fue registrado anteriormente. "
                           "Si crees que es un error, escribe *10* para hablar con Ivonn."),
                "proceso_id": proceso["id"],
            }
        
        if duplicado == "EN_REVISION":
            self.proceso_service.registrar_analisis_gemini(
                proceso["id"], exito=True,
                analisis=analysis.to_dict()
            )
            return {
                "exito": False,
                "mensaje": ("Se detectó un posible comprobante similar. "
                           "Tu pago está en revisión manual. Te confirmamos pronto."),
                "proceso_id": proceso["id"],
            }

        # 6. Verificar si es comprobante valido
        if not analysis.es_valido:
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

        # 7. Verificar monto con tolerancia
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

        # 8. Registrar analisis exitoso
        self.proceso_service.registrar_analisis_gemini(
            proceso["id"], exito=True,
            analisis=analysis.to_dict()
        )

        # 9. Registrar pago pendiente
        mes_anio = obligacion.get("periodo") or datetime.now().strftime("%Y-%m")
        
        # Calcular hash de la imagen
        hash_comprobante = self._calcular_hash_imagen(imagen_url)
        
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
            "referencia_detectada": analysis.referencia_detectada,
            "fecha_detectada": analysis.fecha_detectada,
            "plataforma_detectada": analysis.plataforma_detectada,
            "tipo_pago": analysis.plataforma_detectada or "desconocido",
            "tipo": "mensualidad",
            "mes_anio": mes_anio,
            "imagen_url": imagen_url,
            "hash_comprobante": hash_comprobante,
            "estado": "pendiente_verificacion",
            "wompi_data": {
                "analisis_gemini": analysis.metadata,
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

    def _calcular_hash_imagen(self, imagen_url: str) -> Optional[str]:
        """Calcula SHA-256 de una imagen desde URL."""
        try:
            import httpx
            from services.supabase_client import supabase
            import os
            
            # Obtener credenciales de Twilio
            twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
            twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
            
            response = httpx.get(
                imagen_url,
                auth=(twilio_sid, twilio_token),
                timeout=15,
            )
            response.raise_for_status()
            
            return hashlib.sha256(response.content).hexdigest()
        except Exception as e:
            logger.warning(f"[HASH] No se pudo calcular hash: {e}")
            return None

    def _verificar_duplicado(self, club_id: str, deportista_id: str,
                             imagen_url: str, monto_detectado: float,
                             fecha_detectada: Optional[str],
                             referencia_detectada: Optional[str],
                             plataforma_detectada: Optional[str]) -> str:
        """Verifica si un comprobante es duplicado (multi-capa).
        
        Retorna:
        - "APROBADO": sin evidencia de duplicado
        - "DUPLICADO": misma imagen o misma transaccion
        - "EN_REVISION": posible duplicado, requiere revision manual
        """
        # Capa 1: Hash de imagen
        hash_nuevo = self._calcular_hash_imagen(imagen_url)
        if hash_nuevo:
            existente = supabase.table("pagos")\
                .select("id")\
                .eq("club_id", club_id)\
                .eq("hash_comprobante", hash_nuevo)\
                .limit(1)\
                .execute()
            
            if existente.data:
                return "DUPLICADO"

        # Capa 2: Referencia de transaccion
        if referencia_detectada:
            existente = supabase.table("pagos")\
                .select("id")\
                .eq("club_id", club_id)\
                .eq("referencia_detectada", referencia_detectada)\
                .limit(1)\
                .execute()
            
            if existente.data:
                return "DUPLICADO"

        # Capa 3: Combinacion de datos
        if deportista_id and monto_detectado and fecha_detectada:
            existente = supabase.table("pagos")\
                .select("id")\
                .eq("club_id", club_id)\
                .eq("deportista_id", deportista_id)\
                .eq("monto_detectado", monto_detectado)\
                .eq("fecha_detectada", fecha_detectada)\
                .limit(1)\
                .execute()
            
            if existente.data:
                return "EN_REVISION"

        return "APROBADO"
