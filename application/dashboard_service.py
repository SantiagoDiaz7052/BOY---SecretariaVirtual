from datetime import datetime
from typing import Optional

from application.view_models import (
    DashboardViewModel, DashboardStats, ResumenPill,
    AccionCard, TimelineEntry, BandejaViewModel, BandejaGrupo,
    BandejaItem, DeportistasViewModel, DeportistaRow,
    FinanzasViewModel, FinanzasDatos, PagoRow, ConceptoRow,
    HistorialViewModel, HistorialEntry, SistemaViewModel,
)
from application.tarea_service import TareaService
from application.solicitud_ingreso_service import SolicitudIngresoService
from application.deportista_service import DeportistaService
from application.obligacion_service import ObligacionService
from application.concepto_service import ConceptoService
from application.temporada_service import TemporadaService
from application.event_service import EventService


def _saludo() -> str:
    h = datetime.now().hour
    if h < 12:
        return "buenos días"
    elif h < 18:
        return "buenas tardes"
    return "buenas noches"


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


class DashboardService:
    """Construye ViewModels para todas las pantallas del panel."""

    def __init__(
        self,
        tarea_service: Optional[TareaService] = None,
        solicitud_service: Optional[SolicitudIngresoService] = None,
        deportista_service: Optional[DeportistaService] = None,
        obligacion_service: Optional[ObligacionService] = None,
        concepto_service: Optional[ConceptoService] = None,
        temporada_service: Optional[TemporadaService] = None,
        event_service: Optional[EventService] = None,
    ):
        self._tareas = tarea_service or TareaService()
        self._solicitudes = solicitud_service or SolicitudIngresoService()
        self._deportistas_svc = deportista_service or DeportistaService()
        self._obligaciones = obligacion_service or ObligacionService()
        self._conceptos = concepto_service or ConceptoService()
        self._temporadas = temporada_service or TemporadaService()
        self._eventos = event_service or EventService()

    # ─── Dashboard ──────────────────────────────────

    def build_dashboard(self, club_id: str, nombre: str) -> DashboardViewModel:
        saludo = _saludo()

        # Resumen pills desde tareas pendientes
        try:
            conteos = self._tareas.contar_pendientes(club_id)
        except Exception:
            conteos = {}
        try:
            activos = len(self._deportistas_svc.listar_por_club(
                club_id, estado="ACTIVO", temporada_id=None
            ))
        except Exception:
            activos = 0
        try:
            total_deportistas = len(self._deportistas_svc.listar_por_club(
                club_id, estado=None, temporada_id=None
            ))
        except Exception:
            total_deportistas = 0

        resumen = []
        color_map = {"evaluacion_pendiente": "red", "comprobante_pendiente": "orange",
                     "activacion_pendiente": "blue", "vencida": "purple"}
        for tipo, count in conteos.items():
            label = tipo.replace("_pendiente", "").replace("_", " ")
            color = color_map.get(tipo, "gray")
            resumen.append(ResumenPill(color=color, texto=f"{count} {label} por revisar"))
        if activos > 0:
            resumen.append(ResumenPill(color="green", texto=f"{activos} deportistas activos"))

        # Acciones requeridas: top de la bandeja
        acciones = self._build_acciones(club_id, limite=4)

        # Timeline desde eventos recientes
        timeline = self._build_timeline(club_id, limite=6)

        # Stats
        stats = self._build_stats(club_id)

        return DashboardViewModel(
            saludo=saludo,
            nombre=nombre,
            resumen=resumen,
            acciones=acciones,
            timeline=timeline,
            stats=stats,
        )

    def _build_acciones(self, club_id: str, limite: int = 4) -> list[AccionCard]:
        acciones = []
        try:
            pendientes = self._tareas.listar_pendientes(club_id)
            for t in pendientes[:limite]:
                color_map = {
                    "evaluacion_pendiente": "#ef4444",
                    "comprobante_pendiente": "#f59e0b",
                    "activacion_pendiente": "#3b82f6",
                }
                acciones.append(AccionCard(
                    color=color_map.get(t.tipo, "#6b7280"),
                    texto=t.descripcion,
                    persona=t.tipo.replace("_pendiente", "").replace("_", " · "),
                ))
        except Exception:
            pass
        return acciones

    def _build_timeline(self, club_id: str, limite: int = 6) -> list[TimelineEntry]:
        entries = []
        try:
            notis = self._eventos.historial(club_id, limite=limite)
            for n in notis:
                dot_map = {
                    "success": "success",
                    "warning": "warning",
                    "primary": "primary",
                    "info": "info",
                    "danger": "danger",
                }
                entries.append(TimelineEntry(
                    hora=n["hora"],
                    dot_class=dot_map.get(n["color"], "info"),
                    icono=n["icono"],
                    texto=n["texto"],
                ))
        except Exception:
            pass
        return entries

    def _build_stats(self, club_id: str) -> DashboardStats:
        stats = DashboardStats()
        try:
            deportistas = self._deportistas_svc.listar_por_club(
                club_id, estado=None, temporada_id=None
            )
            stats.total_deportistas = len(deportistas)
            stats.activos = sum(1 for d in deportistas if d.estado == "ACTIVO")
        except Exception:
            pass
        try:
            vencidas = self._obligaciones.listar_por_deportista(
                club_id, deportista_id=None, solo_pendientes=False
            )
            stats.vencidas = sum(1 for o in vencidas if o.get("estado", "") == "VENCIDA")
        except Exception:
            pass
        return stats

    # ─── Bandeja ────────────────────────────────────

    def build_bandeja(self, club_id: str) -> BandejaViewModel:
        grupos_map = {
            "evaluacion": ("🔴 Evaluación pendiente", "#ef4444", "pendiente por evaluar"),
            "comprobante": ("🟡 Comprobante por revisar", "#f59e0b", "pendiente por revisar"),
            "activacion": ("🔵 Activación pendiente", "#3b82f6", "pendiente por activar"),
            "vencida": ("🟠 Mensualidad vencida", "#8b5cf6", "vencida"),
        }
        grupos = []
        total = 0

        try:
            pendientes = self._tareas.listar_pendientes(club_id)
            items_por_tipo = {}
            for t in pendientes:
                tipo_base = t.tipo.replace("_pendiente", "")
                if tipo_base not in items_por_tipo:
                    items_por_tipo[tipo_base] = []
                items_por_tipo[tipo_base].append(BandejaItem(
                    tipo=tipo_base,
                    color=grupos_map.get(tipo_base, ("", "#6b7280", ""))[1],
                    texto=t.descripcion,
                    persona=t.referencia_id or "—",
                    detalle=t.tipo.replace("_pendiente", "").replace("_", " · "),
                    hace="—",
                ))

            # Agregar vencidas desde obligaciones
            try:
                obligs = self._obligaciones.listar_por_deportista(
                    club_id, deportista_id=None, solo_pendientes=False
                )
                vencidas_list = []
                for o in obligs:
                    if o.get("estado", "") == "VENCIDA":
                        vencidas_list.append(BandejaItem(
                            tipo="vencida",
                            color="#8b5cf6",
                            texto="Mensualidad vencida",
                            persona=f"Obligación {o.get('id', '')}",
                            detalle=f"${o.monto_total:,.0f}" if hasattr(o, "monto_total") else "—",
                            hace="—",
                        ))
                if vencidas_list:
                    items_por_tipo["vencida"] = vencidas_list
            except Exception:
                pass

            for key, (titulo, color, _) in grupos_map.items():
                lista = items_por_tipo.get(key, [])
                grupos.append(BandejaGrupo(key=key, titulo=titulo, lista=lista))
                total += len(lista)

        except Exception:
            for key, (titulo, _, _) in grupos_map.items():
                grupos.append(BandejaGrupo(key=key, titulo=titulo, lista=[]))

        return BandejaViewModel(grupos=grupos, total=total)

    # ─── Deportistas ────────────────────────────────

    def build_deportistas(self, club_id: str) -> DeportistasViewModel:
        rows = []
        try:
            lista = self._deportistas_svc.listar_por_club(
                club_id, estado=None, temporada_id=None
            )
            for d in lista:
                activo = d.estado == "ACTIVO"
                rows.append(DeportistaRow(
                    id=d.id or "",
                    nombre=d.nombre,
                    documento=d.documento,
                    nivel=d.nivel,
                    estado="Activo" if activo else "Inactivo",
                    badge="success" if activo else "danger",
                    ultimo_pago=None,
                    telefono=d.telefono or "",
                ))
        except Exception:
            pass
        activos = sum(1 for r in rows if r.estado == "Activo")
        return DeportistasViewModel(deportistas=rows, total=len(rows), activos=activos)

    # ─── Finanzas ───────────────────────────────────

    def build_finanzas(self, club_id: str) -> FinanzasViewModel:
        datos = FinanzasDatos()

        try:
            conceptos = self._conceptos.listar_por_club(club_id, solo_activos=False)
            datos.conceptos = [
                ConceptoRow(
                    nombre=c.nombre,
                    monto=f"{c.monto_default:,.0f}",
                    activo=c.activo,
                )
                for c in conceptos
            ]
        except Exception:
            pass

        try:
            obligs = self._obligaciones.listar_por_deportista(
                club_id, deportista_id=None, solo_pendientes=False
            )
            total_mens = len(obligs)
            pagadas = sum(1 for o in obligs if o.get("estado", "") == "PAGADA")
            pendientes = sum(1 for o in obligs if o.get("estado", "") == "PENDIENTE")
            vencidas = sum(1 for o in obligs if o.get("estado", "") == "VENCIDA")
            datos.total_mensualidades = total_mens
            datos.pagadas = pagadas
            datos.pendientes = pendientes
            datos.vencidas = vencidas
            if total_mens > 0:
                datos.tasa_cobro = int(pagadas / total_mens * 100)
        except Exception:
            pass

        return FinanzasViewModel(datos=datos)

    # ─── Historial ──────────────────────────────────

    def build_historial(self, club_id: str) -> HistorialViewModel:
        try:
            entries = self._eventos.historial(club_id, limite=50)
            return HistorialViewModel(historial=[
                HistorialEntry(**e) for e in entries
            ])
        except Exception:
            return HistorialViewModel()

    # ─── Sistema ────────────────────────────────────

    @staticmethod
    def build_sistema(request) -> SistemaViewModel:
        import sys
        import fastapi
        import os
        import time
        vm = SistemaViewModel()
        vm.python_version = sys.version.split()[0]
        vm.fastapi_version = fastapi.__version__
        vm.entorno = "Producción" if os.getenv("RENDER") else "Desarrollo"
        try:
            from services.supabase_client import supabase
            supabase.table("_health").select("1").limit(1).execute()
            vm.supabase["online"] = True
        except Exception:
            vm.supabase["online"] = False
        try:
            from google import genai
            from google.genai import types
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                client = genai.Client(api_key=api_key)
                t0 = time.time()
                resp = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents="responde solo: ok",
                    config=types.GenerateContentConfig(max_output_tokens=5),
                )
                elapsed = int((time.time() - t0) * 1000)
                vm.gemini["online"] = resp and resp.text
                vm.gemini["tiempo_respuesta_ms"] = elapsed
        except Exception as e:
            vm.gemini["online"] = False
            vm.gemini["ultimo_error"] = str(e)[:120]
        vm.whatsapp["ultimo_mensaje"] = "—"
        vm.whatsapp["mensajes_hoy"] = 0
        vm.servidor["version"] = "2.1.0"
        return vm

    # ─── Búsqueda global ────────────────────────────

    def buscar(self, club_id: str, q: str) -> list[dict]:
        ql = q.lower()
        results = []
        try:
            deportistas = self._deportistas_svc.listar_por_club(
                club_id, estado=None, temporada_id=None
            )
            for d in deportistas:
                if ql in d.nombre.lower() or ql in d.documento or ql in (d.telefono or ""):
                    results.append({
                        "id": d.id or "",
                        "nombre": d.nombre,
                        "documento": d.documento,
                        "nivel": d.nivel,
                        "estado": "Activo" if d.estado == "ACTIVO" else "Inactivo",
                        "telefono": d.telefono or "",
                    })
        except Exception:
            pass
        return results[:8]


# Singleton global
dashboard_service = DashboardService()
