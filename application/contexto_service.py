from typing import Optional
from domain.contexto_conversacional import ContextoConversacional
from repositories.contexto_repo import ContextoConversacionalRepository


class ContextoConversacionalService:
    """Servicio de aplicacion para contexto conversacional.
    
    Gestiona la memoria activa del usuario en una conversacion.
    
    REGLAS:
    - Una sola sesion activa por (club_id, numero_whatsapp)
    - Almacena: deportista_actual, proceso_pago_actual, obligacion_actual
    - Permite que BOY entienda respuestas cortas
    - Se actualiza automaticamente segun la interaccion
    """

    def __init__(self):
        self.repo = ContextoConversacionalRepository()

    def obtener_o_crear(self, club_id: str, 
                        numero_whatsapp: str) -> ContextoConversacional:
        """Obtiene el contexto activo o crea uno nuevo."""
        contexto = self.repo.obtener_activo(club_id, numero_whatsapp)
        if contexto:
            return contexto

        datos = {
            "club_id": club_id,
            "numero_whatsapp": numero_whatsapp,
            "estado": "activa",
        }
        return self.repo.crear(datos)

    def obtener_activo(self, club_id: str, 
                       numero_whatsapp: str) -> Optional[ContextoConversacional]:
        return self.repo.obtener_activo(club_id, numero_whatsapp)

    def actualizar_deportista_actual(self, contexto_id: str, 
                                     deportista_id: Optional[str]) -> ContextoConversacional:
        return self.repo.actualizar(contexto_id, {
            "deportista_actual_id": deportista_id,
        })

    def actualizar_proceso_pago(self, contexto_id: str, 
                                proceso_id: Optional[str]) -> ContextoConversacional:
        return self.repo.actualizar(contexto_id, {
            "proceso_pago_actual_id": proceso_id,
        })

    def actualizar_obligacion(self, contexto_id: str, 
                              obligacion_id: Optional[str]) -> ContextoConversacional:
        return self.repo.actualizar(contexto_id, {
            "obligacion_actual_id": obligacion_id,
        })

    def registrar_intencion(self, contexto_id: str, 
                            intencion: str) -> ContextoConversacional:
        return self.repo.actualizar(contexto_id, {
            "ultima_intencion": intencion,
        })

    def registrar_comprobante(self, contexto_id: str, 
                              imagen_url: str) -> ContextoConversacional:
        return self.repo.actualizar(contexto_id, {
            "ultimo_comprobante_url": imagen_url,
        })

    def limpiar(self, contexto_id: str) -> ContextoConversacional:
        """Limpia el contexto manteniendo la sesion."""
        contexto = self.repo.obtener_por_id(contexto_id)
        if contexto:
            contexto.limpiar()
            return self.repo.actualizar(contexto_id, {
                "deportista_actual_id": None,
                "proceso_pago_actual_id": None,
                "obligacion_actual_id": None,
                "ultima_intencion": None,
                "ultimo_comprobante_url": None,
            })
        return contexto
