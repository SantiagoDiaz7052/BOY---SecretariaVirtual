from typing import Optional
from services.supabase_client import supabase
from domain.contexto_conversacional import ContextoConversacional


class ContextoConversacionalRepository:
    """Repositorio para contextos conversacionales en Supabase."""

    TABLE = "contextos_conversacionales"

    def obtener_por_id(self, contexto_id: str) -> Optional[ContextoConversacional]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("id", contexto_id)\
            .single()\
            .execute()
        if not resultado.data:
            return None
        return ContextoConversacional.from_dict(resultado.data)

    def obtener_activo(self, club_id: str, 
                       numero_whatsapp: str) -> Optional[ContextoConversacional]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("numero_whatsapp", numero_whatsapp)\
            .eq("estado", "activa")\
            .single()\
            .execute()
        if not resultado.data:
            return None
        return ContextoConversacional.from_dict(resultado.data)

    def crear(self, datos: dict) -> ContextoConversacional:
        resultado = supabase.table(self.TABLE)\
            .insert(datos)\
            .execute()
        return ContextoConversacional.from_dict(resultado.data[0])

    def actualizar(self, contexto_id: str, datos: dict) -> ContextoConversacional:
        resultado = supabase.table(self.TABLE)\
            .update(datos)\
            .eq("id", contexto_id)\
            .execute()
        return ContextoConversacional.from_dict(resultado.data[0])

    def desactivar(self, contexto_id: str) -> None:
        supabase.table(self.TABLE)\
            .update({"estado": "inactiva"})\
            .eq("id", contexto_id)\
            .execute()
