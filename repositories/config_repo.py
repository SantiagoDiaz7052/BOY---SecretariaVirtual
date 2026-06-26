from typing import Optional
from services.supabase_client import supabase
from domain.configuracion_club import ConfiguracionClub


class ConfiguracionClubRepository:
    """Repositorio para configuracion de club en Supabase."""

    TABLE = "configuracion_club"

    def obtener_por_club(self, club_id: str) -> Optional[ConfiguracionClub]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .single()\
            .execute()
        
        if not resultado.data:
            return None
        return ConfiguracionClub.from_dict(resultado.data)

    def crear(self, club_id: str) -> ConfiguracionClub:
        """Crea configuracion por defecto para un club."""
        resultado = supabase.table(self.TABLE)\
            .insert({"club_id": club_id})\
            .execute()
        return ConfiguracionClub.from_dict(resultado.data[0])

    def actualizar(self, club_id: str, datos: dict) -> ConfiguracionClub:
        resultado = supabase.table(self.TABLE)\
            .update(datos)\
            .eq("club_id", club_id)\
            .execute()
        return ConfiguracionClub.from_dict(resultado.data[0])

    def obtener_o_crear(self, club_id: str) -> ConfiguracionClub:
        """Obtiene la configuracion o la crea si no existe."""
        config = self.obtener_por_club(club_id)
        if config is None:
            config = self.crear(club_id)
        return config
