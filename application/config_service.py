from typing import Optional
from domain.configuracion_club import ConfiguracionClub
from repositories.config_repo import ConfiguracionClubRepository


class ConfiguracionClubService:
    """Servicio de aplicacion para configuracion de club."""

    def __init__(self):
        self.repo = ConfiguracionClubRepository()

    def obtener_por_club(self, club_id: str) -> Optional[ConfiguracionClub]:
        return self.repo.obtener_por_club(club_id)

    def obtener_o_crear(self, club_id: str) -> ConfiguracionClub:
        return self.repo.obtener_o_crear(club_id)

    def actualizar(self, club_id: str, **kwargs) -> ConfiguracionClub:
        return self.repo.actualizar(club_id, kwargs)

    def configurar_llave_bre(self, club_id: str, llave: str) -> ConfiguracionClub:
        """Configura la llave Bre-B de un club."""
        return self.actualizar(club_id, llave_bre_b=llave)

    def configurar_tolerancia(self, club_id: str, tolerancia: float) -> ConfiguracionClub:
        """Configura la tolerancia de monto para comprobantes."""
        return self.actualizar(club_id, tolerancia_monto=tolerancia)

    def configurar_recargo(self, club_id: str, recargo: float) -> ConfiguracionClub:
        """Configura el recargo por defecto."""
        return self.actualizar(club_id, recargo_default=recargo)

    def configurar_recordatorios(self, club_id: str, dias: list) -> ConfiguracionClub:
        """Configura los dias de recordatorio antes del vencimiento."""
        return self.actualizar(club_id, recordatorio_dias=dias)

    def es_monto_aceptable(self, club_id: str, monto_detectado: float, 
                           monto_esperado: float) -> bool:
        """Verifica si un monto esta dentro de la tolerancia del club."""
        config = self.obtener_por_club(club_id)
        if not config:
            return abs(monto_detectado - monto_esperado) <= 5000
        return config.es_monto_aceptable(monto_detectado, monto_esperado)
