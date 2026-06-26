from typing import Optional
from domain.temporada import Temporada, EstadoTemporada
from repositories.temporada_repo import TemporadaRepository


class TemporadaService:
    """Servicio de aplicacion para temporadas.
    
    Coordina la gestion de temporadas deportivas.
    
    REGLAS:
    - Una sola temporada activa por club
    - Permite consultar inscritos por anio
    - Facilita historial y estadisticas
    """

    def __init__(self):
        self.repo = TemporadaRepository()

    def obtener_activa(self, club_id: str) -> Optional[Temporada]:
        """Obtiene la temporada activa de un club."""
        return self.repo.obtener_activa(club_id)

    def obtener_por_id(self, temporada_id: str) -> Optional[Temporada]:
        return self.repo.obtener_por_id(temporada_id)

    def crear_temporada(self, club_id: str, nombre: str,
                        fecha_inicio: str, fecha_fin: str) -> Temporada:
        """Crea una nueva temporada.
        
        Si ya existe una activa, la cierra primero.
        """
        # Cerrar temporada activa existente
        activa = self.repo.obtener_activa(club_id)
        if activa:
            self.repo.cerrar(activa.id)

        datos = {
            "club_id": club_id,
            "nombre": nombre,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "estado": EstadoTemporada.ACTIVA.value,
        }
        return self.repo.crear(datos)

    def cerrar_temporada(self, temporada_id: str) -> Temporada:
        return self.repo.cerrar(temporada_id)

    def listar_por_club(self, club_id: str):
        return self.repo.listar_por_club(club_id)
