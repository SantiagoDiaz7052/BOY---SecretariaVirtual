from typing import Optional, List
from services.supabase_client import supabase
from domain.solicitud_ingreso import SolicitudIngreso, EstadoSolicitud


class SolicitudIngresoRepository:
    """Repositorio para solicitudes de ingreso en Supabase."""

    TABLE = "solicitudes_ingreso"

    def obtener_por_id(self, solicitud_id: str) -> Optional[SolicitudIngreso]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("id", solicitud_id)\
            .single()\
            .execute()
        if not resultado.data:
            return None
        return SolicitudIngreso.from_dict(resultado.data)

    def buscar_por_documento(self, club_id: str, documento: str) -> Optional[SolicitudIngreso]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("documento", documento)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        if not resultado.data:
            return None
        return SolicitudIngreso.from_dict(resultado.data[0])

    def obtener_activa_por_documento(self, club_id: str, 
                                     documento: str) -> Optional[SolicitudIngreso]:
        """Obtiene la solicitud activa (no completada ni cancelada) de un documento."""
        estados_activos = [
            EstadoSolicitud.PENDIENTE_EVALUACION.value,
            EstadoSolicitud.EVALUADO.value,
            EstadoSolicitud.PENDIENTE_MATRICULA.value,
            EstadoSolicitud.MATRICULA_PAGADA.value,
            EstadoSolicitud.PENDIENTE_ACTIVACION.value,
        ]
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("documento", documento)\
            .in_("estado", estados_activos)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        if not resultado.data:
            return None
        return SolicitudIngreso.from_dict(resultado.data[0])

    def listar_por_estado(self, club_id: str, 
                          estado: Optional[str] = None) -> List[SolicitudIngreso]:
        query = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)
        if estado:
            query = query.eq("estado", estado)
        resultado = query.order("created_at", desc=True).execute()
        return [SolicitudIngreso.from_dict(s) for s in (resultado.data or [])]

    def listar_por_whatsapp(self, club_id: str, 
                            numero_whatsapp: str) -> List[SolicitudIngreso]:
        """Busca solicitudes por WhatsApp del responsable."""
        telefono_limpio = numero_whatsapp.replace("whatsapp:+57", "").replace("whatsapp:+", "")
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .or_(f"telefono.eq.{telefono_limpio},responsable_whatsapp.eq.{telefono_limpio}")\
            .order("created_at", desc=True)\
            .execute()
        return [SolicitudIngreso.from_dict(s) for s in (resultado.data or [])]

    def crear(self, datos: dict) -> SolicitudIngreso:
        resultado = supabase.table(self.TABLE)\
            .insert(datos)\
            .execute()
        return SolicitudIngreso.from_dict(resultado.data[0])

    def actualizar_estado(self, solicitud_id: str, 
                          estado: str, **kwargs) -> SolicitudIngreso:
        datos = {"estado": estado}
        datos.update(kwargs)
        resultado = supabase.table(self.TABLE)\
            .update(datos)\
            .eq("id", solicitud_id)\
            .execute()
        return SolicitudIngreso.from_dict(resultado.data[0])

    def asignar_nivel(self, solicitud_id: str, nivel: str) -> SolicitudIngreso:
        from datetime import date
        return self.actualizar_estado(
            solicitud_id,
            EstadoSolicitud.EVALUADO.value,
            nivel=nivel,
            fecha_evaluacion=date.today().isoformat(),
        )
