from typing import Optional, List
from services.supabase_client import supabase
from domain.tarea import Tarea


class TareaRepository:
    """Repositorio para tareas en Supabase.
    
    Las tareas son una proyeccion derivada del estado del dominio.
    No gobiernan el negocio, solo reflejan acciones pendientes.
    """

    TABLE = "tareas"

    def obtener_por_id(self, tarea_id: str) -> Optional[Tarea]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("id", tarea_id)\
            .single()\
            .execute()
        if not resultado.data:
            return None
        return Tarea.from_dict(resultado.data)

    def listar_pendientes(self, club_id: str) -> List[Tarea]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("estado", "pendiente")\
            .order("created_at", asc=True)\
            .execute()
        return [Tarea.from_dict(t) for t in (resultado.data or [])]

    def listar_por_tipo(self, club_id: str, tipo: str) -> List[Tarea]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("tipo", tipo)\
            .eq("estado", "pendiente")\
            .order("created_at", asc=True)\
            .execute()
        return [Tarea.from_dict(t) for t in (resultado.data or [])]

    def contar_pendientes(self, club_id: str) -> dict:
        """Retorna el conteo de tareas pendientes agrupadas por tipo.
        
        Ej: {"evaluacion_pendiente": 5, "comprobante_revisar": 3}
        """
        resultado = supabase.table(self.TABLE)\
            .select("tipo")\
            .eq("club_id", club_id)\
            .eq("estado", "pendiente")\
            .execute()
        conteo = {}
        for t in (resultado.data or []):
            tipo = t["tipo"]
            conteo[tipo] = conteo.get(tipo, 0) + 1
        return conteo

    def crear(self, datos: dict) -> Tarea:
        resultado = supabase.table(self.TABLE)\
            .insert(datos)\
            .execute()
        return Tarea.from_dict(resultado.data[0])

    def completar(self, tarea_id: str) -> Tarea:
        from datetime import datetime
        resultado = supabase.table(self.TABLE)\
            .update({
                "estado": "completada",
                "completed_at": datetime.now().isoformat(),
            })\
            .eq("id", tarea_id)\
            .execute()
        return Tarea.from_dict(resultado.data[0])

    def completar_por_referencia(self, referencia_id: str) -> None:
        """Completa todas las tareas pendientes asociadas a una referencia."""
        from datetime import datetime
        supabase.table(self.TABLE)\
            .update({
                "estado": "completada",
                "completed_at": datetime.now().isoformat(),
            })\
            .eq("referencia_id", referencia_id)\
            .eq("estado", "pendiente")\
            .execute()
