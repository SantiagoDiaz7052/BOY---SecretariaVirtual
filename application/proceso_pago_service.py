import logging
from typing import Optional
from datetime import datetime

from domain.proceso_pago import (
    ProcesoPago, EstadoProcesoPago, EventoProcesoPago
)
from domain.configuracion_club import ConfiguracionClub
from repositories.proceso_pago_repo import ProcesoPagoRepository
from repositories.obligacion_repo import ObligacionRepository
from repositories.config_repo import ConfiguracionClubRepository

logger = logging.getLogger("boy.proceso_pago")


class ProcesoPagoService:
    """Servicio de aplicacion para procesos de pago.
    
    Coordina la CONVERSACION sobre pagos (no la entidad financiera).
    
    REGLAS:
    - Solo puede haber un proceso activo por deportista
    - El proceso sigue la conversacion, no el dinero
    - Si Gemini falla, el proceso se mantiene activo para reintentar
    - Los eventos se registran en el historial, no como estados
    """

    def __init__(self):
        self.repo = ProcesoPagoRepository()
        self.obligacion_repo = ObligacionRepository()
        self.config_repo = ConfiguracionClubRepository()

    def obtener_proceso_activo(self, club_id: str, 
                                deportista_id: str) -> Optional[dict]:
        """Obtiene el proceso de pago activo de un deportista."""
        proceso = self.repo.obtener_activo_por_deportista(club_id, deportista_id)
        if not proceso:
            return None
        return proceso.to_dict()

    def iniciar_proceso(self, club_id: str, deportista_id: str,
                        obligacion_id: Optional[str] = None) -> dict:
        """Inicia un nuevo proceso de pago.
        
        Si ya hay un proceso activo, retorna ese proceso.
        Si no hay obligacion pendiente, se puede iniciar sin ella
        (el bot determinara la obligacion despues).
        """
        # Verificar si ya hay un proceso activo
        proceso_activo = self.repo.obtener_activo_por_deportista(
            club_id, deportista_id
        )
        if proceso_activo:
            logger.info(
                f"[PROCESO] Proceso ya existe: {proceso_activo.id} "
                f"para deportista {deportista_id}"
            )
            return proceso_activo.to_dict()

        # Obtener configuracion del club
        config = self.config_repo.obtener_por_club(club_id)
        llave_bre = config.llave_bre_b if config else None

        # Obtener monto de la obligacion si se especifica
        monto_informado = None
        if obligacion_id:
            obligacion = self.obligacion_repo.obtener_por_id(obligacion_id)
            if obligacion:
                monto_informado = obligacion.monto_total

        # Crear el proceso
        datos = {
            "club_id": club_id,
            "deportista_id": deportista_id,
            "obligacion_id": obligacion_id,
            "llave_bre_b": llave_bre,
            "monto_informado": monto_informado,
            "estado": EstadoProcesoPago.ACTIVO.value,
            "historial": [{
                "evento": EventoProcesoPago.INICIADO.value,
                "timestamp": datetime.now().isoformat(),
                "detalle": "Proceso de pago iniciado",
            }],
        }

        proceso = self.repo.crear(datos)
        logger.info(f"[PROCESO] Nuevo proceso: {proceso.id} para deportista {deportista_id}")
        return proceso.to_dict()

    def registrar_evento(self, proceso_id: str, evento: EventoProcesoPago,
                         detalle: Optional[str] = None,
                         metadata: Optional[dict] = None) -> dict:
        """Registra un evento en el proceso de pago."""
        proceso = self.repo.obtener_por_id(proceso_id)
        if not proceso:
            raise ValueError(f"Proceso {proceso_id} no encontrado")

        proceso.agregar_evento(evento, detalle, metadata)
        
        # Actualizar historial en DB
        self.repo.actualizar(proceso_id, {
            "historial": [e.to_dict() for e in proceso.historial],
        })

        return proceso.to_dict()

    def registrar_comprobante_recibido(self, proceso_id: str,
                                        imagen_url: str) -> dict:
        """Registra que el usuario envio un comprobante."""
        return self.registrar_evento(
            proceso_id,
            EventoProcesoPago.COMPROBANTE_RECIBIDO,
            detalle=f"Comprobante recibido: {imagen_url}",
            metadata={"imagen_url": imagen_url},
        )

    def registrar_analisis_gemini(self, proceso_id: str,
                                   exito: bool,
                                   error_type: Optional[str] = None,
                                   analisis: Optional[dict] = None) -> dict:
        """Registra el resultado del analisis de Gemini.
        
        Si Gemini fallo, el proceso se mantiene ACTIVO para reintentar.
        """
        if exito:
            return self.registrar_evento(
                proceso_id,
                EventoProcesoPago.COMPROBANTE_ANALIZADO,
                detalle="Analisis exitoso",
                metadata=analisis,
            )
        else:
            return self.registrar_evento(
                proceso_id,
                EventoProcesoPago.ERROR_GEMINI,
                detalle=f"Error Gemini: {error_type}",
                metadata={"error_type": error_type},
            )

    def registrar_pago_creado(self, proceso_id: str, pago_id: str) -> dict:
        """Registra que se creo un pago en la base de datos."""
        return self.registrar_evento(
            proceso_id,
            EventoProcesoPago.PAGO_REGISTRADO,
            detalle=f"Pago {pago_id} registrado",
            metadata={"pago_id": pago_id},
        )

    def finalizar_proceso(self, proceso_id: str) -> dict:
        """Finaliza el proceso de pago (pago aprobado)."""
        proceso = self.repo.obtener_por_id(proceso_id)
        if not proceso:
            raise ValueError(f"Proceso {proceso_id} no encontrado")

        proceso.finalizar()
        proceso.agregar_evento(EventoProcesoPago.PAGO_APROBADO)
        
        self.repo.actualizar(proceso_id, {
            "estado": EstadoProcesoPago.FINALIZADO.value,
            "historial": [e.to_dict() for e in proceso.historial],
        })

        return proceso.to_dict()

    def cancelar_proceso(self, proceso_id: str, 
                          motivo: str = "usuario") -> dict:
        """Cancela el proceso de pago."""
        proceso = self.repo.obtener_por_id(proceso_id)
        if not proceso:
            raise ValueError(f"Proceso {proceso_id} no encontrado")

        proceso.cancelar(motivo)
        
        self.repo.actualizar(proceso_id, {
            "estado": EstadoProcesoPago.CANCELADO.value,
            "historial": [e.to_dict() for e in proceso.historial],
        })

        return proceso.to_dict()

    def limpiar_procesos_inactivos(self, horas_limite: int = 24) -> int:
        """Cancela procesos abandonados. Util para cron job."""
        return self.repo.cancelar_inactivos(horas_limite)
