from typing import Optional, List
from repositories.solicitud_ingreso_repo import SolicitudIngresoRepository
from domain.solicitud_ingreso import SolicitudIngreso, EstadoSolicitud, ExperienciaReportada


class SolicitudIngresoService:
    """Servicio de aplicacion para Solicitud de Ingreso.
    
    REGLAS:
    - Sin referencias financieras (ni pagos, obligaciones, ni ProcesoPago)
    - Nivel se asigna por secretaria (NO por BOY)
    - Experiencia reportada es solo referencia (usar valores de ExperienciaReportada)
    - Un documento solo puede tener una solicitud activa
    """

    def __init__(self):
        self.repo = SolicitudIngresoRepository()

    def iniciar_solicitud(self, club_id: str, temporada_id: str, datos: dict) -> SolicitudIngreso:
        """Inicia una nueva solicitud de ingreso.
        
        Valida que no exista una solicitud activa para el mismo documento.
        """
        documento = datos.get("documento", "").strip()
        activa = self.repo.obtener_activa_por_documento(club_id, documento)
        if activa:
            raise ValueError(
                f"Ya existe una solicitud activa ({activa.estado}) "
                f"para el documento {documento}"
            )

        solicitud = self.repo.crear({
            "club_id": club_id,
            "temporada_id": temporada_id,
            "nombre": datos.get("nombre", "").strip(),
            "documento": documento,
            "telefono": datos.get("telefono", "").strip(),
            "fecha_nacimiento": datos.get("fecha_nacimiento"),
            "experiencia_reportada": datos.get("experiencia_reportada"),
            "responsable_nombre": datos.get("responsable_nombre"),
            "responsable_documento": datos.get("responsable_documento", "").strip(),
            "responsable_whatsapp": datos.get("responsable_whatsapp"),
            "estado": EstadoSolicitud.PENDIENTE_EVALUACION.value,
        })
        from application.event_service import event_service
        event_service.publicar(
            club_id=club_id,
            tipo="solicitud",
            icono="📝",
            texto=f"Nueva solicitud de ingreso de {solicitud.nombre}",
            referencia_id=solicitud.id,
        )
        return solicitud

    def evaluar_y_asignar_nivel(self, solicitud_id: str, nivel: str) -> SolicitudIngreso:
        """La secretaria evalua y asigna nivel."""
        solicitud = self.repo.obtener_por_id(solicitud_id)
        if not solicitud:
            raise ValueError("Solicitud no encontrada")
        if not solicitud.esta_pendiente_evaluacion:
            raise ValueError(
                f"No se puede evaluar: estado actual es {solicitud.estado}"
            )
        resultado = self.repo.asignar_nivel(solicitud_id, nivel)
        from application.event_service import event_service
        event_service.publicar(
            club_id=solicitud.club_id,
            tipo="solicitud",
            icono="📋",
            texto=f"{solicitud.nombre} fue evaluado y asignado a nivel {nivel}",
            referencia_id=solicitud_id,
        )
        return resultado

    def solicitar_matricula(self, solicitud_id: str) -> SolicitudIngreso:
        """Transiciona a pendiente_matricula tras la evaluacion exitosa."""
        solicitud = self.repo.obtener_por_id(solicitud_id)
        if not solicitud:
            raise ValueError("Solicitud no encontrada")
        if not solicitud.esta_evaluado:
            raise ValueError(
                f"No se puede solicitar matricula: estado actual es {solicitud.estado}"
            )
        if not solicitud.nivel:
            raise ValueError(
                "No se puede solicitar matricula sin nivel asignado"
            )
        return self.repo.actualizar_estado(
            solicitud_id,
            EstadoSolicitud.PENDIENTE_MATRICULA.value,
        )

    def confirmar_pago_matricula(self, solicitud_id: str) -> SolicitudIngreso:
        """Confirma que el pago de matricula fue realizado (externamente)."""
        solicitud = self.repo.obtener_por_id(solicitud_id)
        if not solicitud:
            raise ValueError("Solicitud no encontrada")
        if not solicitud.esta_pendiente_matricula:
            raise ValueError(
                f"No se puede confirmar pago: estado actual es {solicitud.estado}"
            )
        return self.repo.actualizar_estado(
            solicitud_id,
            EstadoSolicitud.MATRICULA_PAGADA.value,
        )

    def activar(self, solicitud_id: str) -> SolicitudIngreso:
        """Transiciona a pendiente_activacion tras pago de matricula."""
        solicitud = self.repo.obtener_por_id(solicitud_id)
        if not solicitud:
            raise ValueError("Solicitud no encontrada")
        if not solicitud.esta_matricula_pagada:
            raise ValueError(
                f"No se puede activar: estado actual es {solicitud.estado}"
            )
        return self.repo.actualizar_estado(
            solicitud_id,
            EstadoSolicitud.PENDIENTE_ACTIVACION.value,
        )

    def completar(self, solicitud_id: str) -> SolicitudIngreso:
        """Completa la solicitud. El deportista queda activo."""
        solicitud = self.repo.obtener_por_id(solicitud_id)
        if not solicitud:
            raise ValueError("Solicitud no encontrada")
        if not solicitud.esta_pendiente_activacion:
            raise ValueError(
                f"No se puede completar: estado actual es {solicitud.estado}"
            )
        resultado = self.repo.actualizar_estado(
            solicitud_id,
            EstadoSolicitud.COMPLETADO.value,
        )
        from application.event_service import event_service
        event_service.publicar(
            club_id=solicitud.club_id,
            tipo="activacion",
            icono="✅",
            texto=f"{solicitud.nombre} fue ACTIVADO correctamente",
            referencia_id=solicitud_id,
        )
        return resultado

    def cancelar(self, solicitud_id: str) -> SolicitudIngreso:
        """Cancela la solicitud."""
        solicitud = self.repo.obtener_por_id(solicitud_id)
        if not solicitud:
            raise ValueError("Solicitud no encontrada")
        if solicitud.esta_completado:
            raise ValueError("No se puede cancelar una solicitud completada")
        return self.repo.actualizar_estado(
            solicitud_id,
            EstadoSolicitud.CANCELADO.value,
        )

    def obtener_solicitud(self, solicitud_id: str) -> Optional[SolicitudIngreso]:
        return self.repo.obtener_por_id(solicitud_id)

    def obtener_activa(self, club_id: str, documento: str) -> Optional[SolicitudIngreso]:
        return self.repo.obtener_activa_por_documento(club_id, documento)

    def listar_por_estado(self, club_id: str, 
                          estado: Optional[str] = None) -> List[SolicitudIngreso]:
        return self.repo.listar_por_estado(club_id, estado)

    def listar_por_whatsapp(self, club_id: str, 
                            numero: str) -> List[SolicitudIngreso]:
        return self.repo.listar_por_whatsapp(club_id, numero)
