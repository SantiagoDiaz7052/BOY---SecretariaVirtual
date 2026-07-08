from datetime import datetime
from typing import Optional
from repositories.notificacion_repo import NotificacionRepository


class EventService:
    """Centraliza la publicacion de eventos: notificaciones y (futuro) historial persistente."""

    def __init__(self):
        self._notificacion_repo = NotificacionRepository()

    def publicar(self, club_id: str, tipo: str, icono: str, texto: str,
                 referencia_id: Optional[str] = None) -> None:
        """Publica un evento: crea notificacion y (futuro) historial + WebSocket."""
        self._notificacion_repo.crear(
            club_id=club_id,
            tipo=tipo,
            icono=icono,
            texto=texto,
            referencia_id=referencia_id,
        )

    def notificaciones_recientes(self, club_id: str, limite: int = 10) -> list[dict]:
        """Retorna notificaciones formateadas para la API JSON."""
        from application.view_models import NotificacionItem

        def _time_ago(dt: datetime) -> str:
            diff = datetime.now() - dt
            mins = int(diff.total_seconds() / 60)
            if mins < 60:
                return f"hace {mins} min" if mins > 1 else "ahora"
            hrs = int(mins / 60)
            if hrs < 24:
                return f"hace {hrs}h"
            days = int(hrs / 24)
            return f"hace {days}d"

        notis = self._notificacion_repo.listar_recientes(club_id, limite=limite)
        return [
            {
                "id": n.id or "",
                "icon": n.icono,
                "text": n.texto,
                "time": _time_ago(datetime.fromisoformat(n.created_at)) if n.created_at else "ahora",
            }
            for n in notis
        ]

    def contar_no_leidas(self, club_id: str) -> int:
        return self._notificacion_repo.contar_no_leidas(club_id)

    def historial(self, club_id: str, limite: int = 20) -> list[dict]:
        """Deriva historial desde notificaciones (futuro: desde tabla historial_eventos)."""
        notis = self._notificacion_repo.listar_recientes(club_id, limite=limite)
        result = []
        for n in notis:
            if not n.created_at:
                continue
            try:
                dt = datetime.fromisoformat(n.created_at)
                hora = dt.strftime("%H:%M")
            except Exception:
                hora = "--:--"
            color_map = {
                "solicitud": "primary",
                "pago": "warning",
                "activacion": "success",
                "sistema": "info",
                "vencida": "danger",
            }
            result.append({
                "hora": hora,
                "color": color_map.get(n.tipo, "info"),
                "icono": n.icono,
                "texto": n.texto,
                "usuario": None,
                "tipo": n.tipo,
            })
        return result


# Instancia global (singleton ligero)
event_service = EventService()
