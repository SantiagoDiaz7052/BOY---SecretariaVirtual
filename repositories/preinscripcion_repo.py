from typing import Optional, List
from services.supabase_client import supabase
from domain.preinscripcion import Preinscripcion, EstadoPreinscripcion


class PreinscripcionRepository:
    """Repositorio para preinscripciones en Supabase."""

    TABLE = "preinscripciones"

    def obtener_por_id(self, preinscripcion_id: str) -> Optional[Preinscripcion]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("id", preinscripcion_id)\
            .single()\
            .execute()
        if not resultado.data:
            return None
        return Preinscripcion.from_dict(resultado.data)

    def buscar_por_documento(self, club_id: str, documento: str) -> Optional[Preinscripcion]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("documento", documento)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        if not resultado.data:
            return None
        return Preinscripcion.from_dict(resultado.data[0])

    def obtener_pendiente(self, club_id: str, documento: str) -> Optional[Preinscripcion]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("documento", documento)\
            .eq("estado", EstadoPreinscripcion.PENDIENTE_PAGO.value)\
            .single()\
            .execute()
        if not resultado.data:
            return None
        return Preinscripcion.from_dict(resultado.data)

    def listar_por_club(self, club_id: str, 
                        estado: Optional[str] = None,
                        temporada_id: Optional[str] = None) -> List[Preinscripcion]:
        query = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)
        if estado:
            query = query.eq("estado", estado)
        if temporada_id:
            query = query.eq("temporada_id", temporada_id)
        resultado = query.order("created_at", desc=True).execute()
        return [Preinscripcion.from_dict(p) for p in (resultado.data or [])]

    def crear(self, datos: dict) -> Preinscripcion:
        resultado = supabase.table(self.TABLE)\
            .insert(datos)\
            .execute()
        return Preinscripcion.from_dict(resultado.data[0])

    def actualizar(self, preinscripcion_id: str, datos: dict) -> Preinscripcion:
        resultado = supabase.table(self.TABLE)\
            .update(datos)\
            .eq("id", preinscripcion_id)\
            .execute()
        return Preinscripcion.from_dict(resultado.data[0])
