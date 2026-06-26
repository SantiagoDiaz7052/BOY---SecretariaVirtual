from typing import Optional, List
from services.supabase_client import supabase
from domain.temporada import Temporada, EstadoTemporada


class TemporadaRepository:
    """Repositorio para temporadas en Supabase."""

    TABLE = "temporadas"

    def obtener_por_id(self, temporada_id: str) -> Optional[Temporada]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("id", temporada_id)\
            .single()\
            .execute()
        if not resultado.data:
            return None
        return Temporada.from_dict(resultado.data)

    def obtener_activa(self, club_id: str) -> Optional[Temporada]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("estado", EstadoTemporada.ACTIVA.value)\
            .single()\
            .execute()
        if not resultado.data:
            return None
        return Temporada.from_dict(resultado.data)

    def listar_por_club(self, club_id: str) -> List[Temporada]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .order("fecha_inicio", desc=True)\
            .execute()
        return [Temporada.from_dict(t) for t in (resultado.data or [])]

    def crear(self, datos: dict) -> Temporada:
        resultado = supabase.table(self.TABLE)\
            .insert(datos)\
            .execute()
        return Temporada.from_dict(resultado.data[0])

    def actualizar(self, temporada_id: str, datos: dict) -> Temporada:
        resultado = supabase.table(self.TABLE)\
            .update(datos)\
            .eq("id", temporada_id)\
            .execute()
        return Temporada.from_dict(resultado.data[0])

    def cerrar(self, temporada_id: str) -> Temporada:
        return self.actualizar(temporada_id, {
            "estado": EstadoTemporada.CERRADA.value,
        })
