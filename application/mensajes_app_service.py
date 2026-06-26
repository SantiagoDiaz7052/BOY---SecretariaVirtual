import logging
from typing import Optional

from adapters.gemini_chat import gemini_chat
from services.supabase_client import supabase

logger = logging.getLogger("boy.whatsapp.mensajes")


class MensajesAppService:
    """Servicio de aplicacion para mensajes de texto.
    
    Mueve la logica de services/mensajes.py a la capa de aplicacion.
    
    REGLAS:
    - El router NUNCA accede directamente a Supabase
    - Este servicio coordina: club, conversacion, Gemini
    - Gemini puede llamar funciones (inscribir, consultar, estado_pago)
    """

    def buscar_club(self, numero_whatsapp: str) -> Optional[dict]:
        """Busca un club por su numero de WhatsApp."""
        resultado = supabase.table("clubs")\
            .select("*")\
            .eq("whatsapp_number", numero_whatsapp)\
            .eq("activo", True)\
            .single()\
            .execute()
        return resultado.data

    def obtener_o_crear_conversacion(self, club_id: str, 
                                      numero_usuario: str,
                                      nombre: str) -> list:
        """Obtiene el historial de conversacion o crea uno nuevo."""
        conv_res = supabase.table("conversaciones")\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("numero_usuario", numero_usuario)\
            .execute()

        if conv_res.data:
            return conv_res.data[0]["historial"]

        # Crear conversacion nueva
        supabase.table("conversaciones").insert({
            "club_id": club_id,
            "numero_usuario": numero_usuario,
            "nombre_usuario": nombre,
            "historial": []
        }).execute()
        return []

    def guardar_conversacion(self, club_id: str, numero_usuario: str,
                              nombre: str, historial: list) -> None:
        """Guarda el historial de conversacion actualizado."""
        supabase.table("conversaciones")\
            .update({"historial": historial, "nombre_usuario": nombre})\
            .eq("club_id", club_id)\
            .eq("numero_usuario", numero_usuario)\
            .execute()

    def procesar_mensaje(self, numero_usuario: str, numero_club: str,
                          nombre: str, mensaje: str) -> str:
        """Procesa un mensaje de texto y retorna la respuesta.
        
        Flujo:
        1. Buscar club
        2. Obtener/crear conversacion
        3. Llamar a Gemini con historial
        4. Guardar conversacion actualizada
        5. Retornar respuesta
        """
        logger.info(f"[MSG] De: {numero_usuario} | Para: {numero_club} | Texto: {mensaje}")

        # 1. Buscar club
        club = self.buscar_club(numero_club)
        if not club:
            logger.error(f"[MSG] Club no encontrado: {numero_club}")
            return "Lo siento, este servicio no está disponible."

        club_id = club["id"]
        system_prompt = club["system_prompt"]
        logger.info(f"[MSG] Club encontrado: {club['nombre']}")

        # 2. Obtener/crear conversacion
        historial = self.obtener_o_crear_conversacion(
            club_id, numero_usuario, nombre
        )
        logger.info(f"[MSG] Historial: {len(historial)} mensajes")

        # 3. Llamar a Gemini (puede ejecutar funciones: inscribir, consultar, estado_pago)
        respuesta = gemini_chat.get_respuesta(
            system_prompt=system_prompt,
            historial=historial,
            mensaje_nuevo=mensaje,
            club_id=club_id,
        )

        # Si Gemini fallo, get_respuesta retorna string de error
        if isinstance(respuesta, str):
            respuesta_texto = respuesta
        else:
            # GeminiResult - no deberia pasar aqui con el adaptador actual
            respuesta_texto = str(respuesta)

        logger.info(f"[MSG] Respuesta: {respuesta_texto[:80]}...")

        # 4. Guardar conversacion
        historial.append({"role": "user", "content": mensaje})
        historial.append({"role": "assistant", "content": respuesta_texto})
        historial = historial[-10:]  # Mantener ultimos 10 mensajes

        self.guardar_conversacion(club_id, numero_usuario, nombre, historial)

        return respuesta_texto


# Instancia global
mensajes_service = MensajesAppService()
