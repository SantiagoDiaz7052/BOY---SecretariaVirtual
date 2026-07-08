from typing import List, Optional
from datetime import datetime, timedelta
from domain.notificacion import Notificacion


class NotificacionRepository:
    """Repositorio de notificaciones.

    Intenta Supabase primero. Fallback a datos en memoria.
    """

    TABLE = "notificaciones"

    def __init__(self):
        self._supabase = None
        self._mock_notificaciones: List[Notificacion] = []
        try:
            from services.supabase_client import supabase
            self._supabase = supabase
        except Exception:
            pass

    def crear(self, club_id: str, tipo: str, icono: str,
              texto: str, referencia_id: Optional[str] = None) -> Notificacion:
        datos = {
            "club_id": club_id,
            "tipo": tipo,
            "icono": icono,
            "texto": texto,
            "referencia_id": referencia_id,
        }
        if self._supabase:
            try:
                resultado = self._supabase.table(self.TABLE).insert(datos).execute()
                if resultado.data:
                    return Notificacion.from_dict(resultado.data[0])
            except Exception:
                pass
        n = Notificacion(
            id=f"mock_{len(self._mock_notificaciones) + 1}",
            created_at=datetime.now().isoformat(),
            **datos,
        )
        self._mock_notificaciones.insert(0, n)
        return n

    def listar_recientes(self, club_id: str, limite: int = 10) -> List[Notificacion]:
        if self._supabase:
            try:
                resultado = self._supabase.table(self.TABLE)\
                    .select("*")\
                    .eq("club_id", club_id)\
                    .order("created_at", desc=True)\
                    .limit(limite)\
                    .execute()
                if resultado.data:
                    return [Notificacion.from_dict(n) for n in resultado.data]
            except Exception:
                pass
        return self._mock_notificaciones[:limite]

    def contar_no_leidas(self, club_id: str) -> int:
        if self._supabase:
            try:
                resultado = self._supabase.table(self.TABLE)\
                    .select("id", count="exact")\
                    .eq("club_id", club_id)\
                    .eq("leida", False)\
                    .execute()
                if resultado.count is not None:
                    return resultado.count
            except Exception:
                pass
        return sum(1 for n in self._mock_notificaciones if not n.leida)

    def marcar_leida(self, notificacion_id: str) -> None:
        if self._supabase:
            try:
                self._supabase.table(self.TABLE)\
                    .update({"leida": True})\
                    .eq("id", notificacion_id)\
                    .execute()
                return
            except Exception:
                pass
        for n in self._mock_notificaciones:
            if n.id == notificacion_id:
                n.leida = True
                break
