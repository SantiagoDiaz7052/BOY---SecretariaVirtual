from typing import Optional, List
from repositories.tarea_repo import TareaRepository
from domain.tarea import Tarea


class TareaService:
    """Servicio de aplicacion para la Bandeja de Tareas.
    
    Proyeccion derivada del dominio. No gobierna reglas de negocio.
    Se crea automaticamente por cambios en SolicitudIngreso, Pago, etc.
    """

    def __init__(self):
        self.repo = TareaRepository()

    def crear_tarea(self, club_id: str, tipo: str, 
                    referencia_id: str, descripcion: str) -> Tarea:
        """Crea una nueva tarea pendiente."""
        return self.repo.crear({
            "club_id": club_id,
            "tipo": tipo,
            "referencia_id": referencia_id,
            "descripcion": descripcion,
            "estado": "pendiente",
        })

    def completar_tarea(self, tarea_id: str) -> Tarea:
        return self.repo.completar(tarea_id)

    def completar_por_referencia(self, referencia_id: str) -> None:
        self.repo.completar_por_referencia(referencia_id)

    def listar_pendientes(self, club_id: str) -> List[Tarea]:
        return self.repo.listar_pendientes(club_id)

    def contar_pendientes(self, club_id: str) -> dict:
        return self.repo.contar_pendientes(club_id)

    def tareas_evaluacion_pendiente(self, club_id: str) -> List[Tarea]:
        return self.repo.listar_por_tipo(club_id, "evaluacion_pendiente")

    def crear_tarea_evaluacion(self, solicitud_id: str, 
                               club_id: str, nombre: str) -> Tarea:
        """Crea tarea cuando llega una nueva solicitud de ingreso."""
        return self.crear_tarea(
            club_id=club_id,
            tipo="evaluacion_pendiente",
            referencia_id=solicitud_id,
            descripcion=f"Evaluar solicitud de ingreso de {nombre}",
        )

    def crear_tarea_comprobante(self, solicitud_id: str,
                                 club_id: str, nombre: str) -> Tarea:
        """Crea tarea cuando se reporta pago de matricula."""
        return self.crear_tarea(
            club_id=club_id,
            tipo="comprobante_revisar",
            referencia_id=solicitud_id,
            descripcion=f"Revisar comprobante de matricula de {nombre}",
        )
