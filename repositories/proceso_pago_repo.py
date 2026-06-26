from typing import Optional, List
from services.supabase_client import supabase
from domain.proceso_pago import ProcesoPago, EstadoProcesoPago


class ProcesoPagoRepository:
    """Repositorio para procesos de pago en Supabase."""

    TABLE = "procesos_pago"

    def obtener_por_id(self, proceso_id: str) -> Optional[ProcesoPago]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("id", proceso_id)\
            .single()\
            .execute()
        
        if not resultado.data:
            return None
        return ProcesoPago.from_dict(resultado.data)

    def obtener_activo_por_deportista(self, club_id: str, 
                                       deportista_id: str) -> Optional[ProcesoPago]:
        """Obtiene el proceso de pago activo de un deportista.
        
        Solo puede haber un proceso activo por deportista a la vez.
        """
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("deportista_id", deportista_id)\
            .eq("estado", EstadoProcesoPago.ACTIVO.value)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if not resultado.data:
            return None
        return ProcesoPago.from_dict(resultado.data[0])

    def listar_por_club(self, club_id: str, 
                         solo_activos: bool = False) -> List[ProcesoPago]:
        query = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)
        
        if solo_activos:
            query = query.eq("estado", EstadoProcesoPago.ACTIVO.value)
        
        resultado = query.order("created_at", desc=True).execute()
        return [ProcesoPago.from_dict(p) for p in (resultado.data or [])]

    def crear(self, proceso: dict) -> ProcesoPago:
        resultado = supabase.table(self.TABLE)\
            .insert(proceso)\
            .execute()
        return ProcesoPago.from_dict(resultado.data[0])

    def actualizar(self, proceso_id: str, datos: dict) -> ProcesoPago:
        resultado = supabase.table(self.TABLE)\
            .update(datos)\
            .eq("id", proceso_id)\
            .execute()
        return ProcesoPago.from_dict(resultado.data[0])

    def cancelar_inactivos(self, horas_limite: int = 24) -> int:
        """Cancela procesos activos mas antiguos que las horas limite.
        
        Util para limpiar procesos que el usuario abandono.
        Retorna la cantidad de procesos cancelados.
        """
        from datetime import datetime, timedelta
        
        limite = datetime.now() - timedelta(hours=horas_limite)
        
        resultado = supabase.table(self.TABLE)\
            .update({"estado": EstadoProcesoPago.CANCELADO.value})\
            .eq("estado", EstadoProcesoPago.ACTIVO.value)\
            .lt("created_at", limite.isoformat())\
            .execute()
        
        return len(resultado.data) if resultado.data else 0

    def expirar_inactivos(self, horas_limite: int = 48) -> int:
        """Expira procesos activos mas antiguos que las horas limite.
        
        Util para limpiar procesos que el usuario abandono.
        Retorna la cantidad de procesos expirados.
        """
        from datetime import datetime, timedelta
        
        limite = datetime.now() - timedelta(hours=horas_limite)
        
        resultado = supabase.table(self.TABLE)\
            .update({"estado": "expirado"})\
            .eq("estado", EstadoProcesoPago.ACTIVO.value)\
            .lt("created_at", limite.isoformat())\
            .execute()
        
        return len(resultado.data) if resultado.data else 0

    def obtener_activo_por_preinscripcion(self, club_id: str, 
                                          preinscripcion_id: str) -> Optional[ProcesoPago]:
        """Obtiene el proceso de pago activo de una preinscripcion."""
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("preinscripcion_id", preinscripcion_id)\
            .eq("estado", EstadoProcesoPago.ACTIVO.value)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if not resultado.data:
            return None
        return ProcesoPago.from_dict(resultado.data[0])
