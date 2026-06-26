from typing import Optional, List
from services.supabase_client import supabase
from domain.deportista import Deportista, EstadoDeportista


class DeportistaRepository:
    """Repositorio para deportistas en Supabase."""

    TABLE = "deportistas"

    def obtener_por_id(self, deportista_id: str) -> Optional[Deportista]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("id", deportista_id)\
            .single()\
            .execute()
        if not resultado.data:
            return None
        return Deportista.from_dict(resultado.data)

    def buscar_por_documento(self, club_id: str, documento: str) -> Optional[Deportista]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("documento", documento)\
            .limit(1)\
            .execute()
        if not resultado.data:
            return None
        return Deportista.from_dict(resultado.data[0])

    def listar_por_club(self, club_id: str, 
                        estado: Optional[str] = None,
                        temporada_id: Optional[str] = None) -> List[Deportista]:
        query = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)
        if estado:
            query = query.eq("estado", estado)
        if temporada_id:
            query = query.eq("temporada_id", temporada_id)
        resultado = query.order("nombre").execute()
        return [Deportista.from_dict(d) for d in (resultado.data or [])]

    def listar_por_whatsapp(self, club_id: str, 
                            numero_whatsapp: str) -> List[Deportista]:
        """Busca deportistas por numero de WhatsApp (del responsable)."""
        telefono_limpio = numero_whatsapp.replace("whatsapp:+57", "").replace("whatsapp:+", "")
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .or_(f"telefono.eq.{telefono_limpio},responsable_whatsapp.eq.{telefono_limpio}")\
            .execute()
        return [Deportista.from_dict(d) for d in (resultado.data or [])]

    def crear(self, datos: dict) -> Deportista:
        resultado = supabase.table(self.TABLE)\
            .insert(datos)\
            .execute()
        return Deportista.from_dict(resultado.data[0])

    def actualizar(self, deportista_id: str, datos: dict) -> Deportista:
        resultado = supabase.table(self.TABLE)\
            .update(datos)\
            .eq("id", deportista_id)\
            .execute()
        return Deportista.from_dict(resultado.data[0])

    def activar(self, deportista_id: str) -> Deportista:
        return self.actualizar(deportista_id, {
            "estado": EstadoDeportista.ACTIVO.value,
        })

    def desactivar(self, deportista_id: str) -> Deportista:
        return self.actualizar(deportista_id, {
            "estado": EstadoDeportista.INACTIVO.value,
        })

    def desactivar_todos(self, club_id: str, temporada_id: str) -> int:
        """Desactiva todos los deportistas de un club en una temporada."""
        resultado = supabase.table(self.TABLE)\
            .update({"estado": EstadoDeportista.INACTIVO.value})\
            .eq("club_id", club_id)\
            .eq("temporada_id", temporada_id)\
            .eq("estado", EstadoDeportista.ACTIVO.value)\
            .execute()
        return len(resultado.data or [])
