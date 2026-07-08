from datetime import datetime
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from routers.auth import usuario_autenticado
from application.dashboard_service import DashboardService
from application.event_service import EventService
from application.config_service import ConfiguracionClubService

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")


def _context_processor(request: Request) -> dict:
    return {"session": dict(request.session)}


templates.context_processors.insert(0, _context_processor)

dashboard_svc = DashboardService()
event_svc = EventService()
config_svc = ConfiguracionClubService()


def _auth(request: Request):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


def _club_id(request: Request) -> str:
    return request.session.get("club_id", "default")


# ──────────────────────────────────────────────
# Pages
# ──────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    auth_resp = _auth(request)
    if auth_resp:
        return auth_resp
    club_id = _club_id(request)
    nombre = request.session.get("nombre", "Ivonn")
    vm = dashboard_svc.build_dashboard(club_id, nombre)
    return templates.TemplateResponse(
        request, "admin/dashboard.html", {
            "saludo": vm.saludo,
            "nombre": vm.nombre,
            "ultima_sincronizacion": vm.ultima_sincronizacion,
            "resumen": [{"color": p.color, "texto": p.texto} for p in vm.resumen],
            "acciones": [{"color": a.color, "texto": a.texto, "persona": a.persona} for a in vm.acciones],
            "timeline": [{"hora": t.hora, "dot_class": t.dot_class, "icono": t.icono, "texto": t.texto} for t in vm.timeline],
            "stats": {
                "ingresos_hoy": vm.stats.ingresos_hoy,
                "activos": vm.stats.activos,
                "total_deportistas": vm.stats.total_deportistas,
                "vencidas": vm.stats.vencidas,
                "mora_acumulada": vm.stats.mora_acumulada,
                "tasa_cobro": vm.stats.tasa_cobro,
            },
        }
    )


@router.get("/bandeja", response_class=HTMLResponse)
async def bandeja(request: Request):
    auth_resp = _auth(request)
    if auth_resp:
        return auth_resp
    vm = dashboard_svc.build_bandeja(_club_id(request))
    return templates.TemplateResponse(
        request, "admin/bandeja.html", {
            "grupos": [
                {
                    "key": g.key,
                    "titulo": g.titulo,
                    "lista": [
                        {"tipo": i.tipo, "color": i.color, "texto": i.texto,
                         "persona": i.persona, "detalle": i.detalle, "hace": i.hace}
                        for i in g.lista
                    ],
                }
                for g in vm.grupos
            ],
            "total": vm.total,
        }
    )


@router.get("/deportistas", response_class=HTMLResponse)
async def deportistas(request: Request):
    auth_resp = _auth(request)
    if auth_resp:
        return auth_resp
    vm = dashboard_svc.build_deportistas(_club_id(request))
    return templates.TemplateResponse(
        request, "admin/deportistas.html", {
            "deportistas": [
                {
                    "id": d.id, "nombre": d.nombre, "documento": d.documento,
                    "nivel": d.nivel, "estado": d.estado, "badge": d.badge,
                    "ultimo_pago": d.ultimo_pago, "telefono": d.telefono,
                }
                for d in vm.deportistas
            ],
            "total": vm.total,
            "activos": vm.activos,
        }
    )


@router.get("/finanzas", response_class=HTMLResponse)
async def finanzas(request: Request):
    auth_resp = _auth(request)
    if auth_resp:
        return auth_resp
    vm = dashboard_svc.build_finanzas(_club_id(request))
    return templates.TemplateResponse(
        request, "admin/finanzas.html", {"datos": {
            "ingresos_hoy": vm.datos.ingresos_hoy,
            "pagos_hoy": vm.datos.pagos_hoy,
            "ingresos_mes": vm.datos.ingresos_mes,
            "pagos_mes": vm.datos.pagos_mes,
            "pagadas": vm.datos.pagadas,
            "total_mensualidades": vm.datos.total_mensualidades,
            "pendientes": vm.datos.pendientes,
            "monto_pendiente": vm.datos.monto_pendiente,
            "mora_acumulada": vm.datos.mora_acumulada,
            "vencidas": vm.datos.vencidas,
            "tasa_cobro": vm.datos.tasa_cobro,
            "ultimos_pagos": [
                {"deportista": p.deportista, "concepto": p.concepto,
                 "monto": p.monto, "estado": p.estado, "badge": p.badge}
                for p in vm.datos.ultimos_pagos
            ],
            "conceptos": [
                {"nombre": c.nombre, "monto": c.monto, "activo": c.activo}
                for c in vm.datos.conceptos
            ],
        }}
    )


@router.get("/configuracion", response_class=HTMLResponse)
async def configuracion(request: Request):
    auth_resp = _auth(request)
    if auth_resp:
        return auth_resp
    try:
        cfg = config_svc.obtener_por_club(_club_id(request))
        config = {
            "llave_breb": cfg.llave_bre_b or "—",
            "monto_matricula": cfg.tolerancia_monto,
            "recargo_mora": cfg.recargo_default,
            "dias_recordatorio": cfg.recordatorio_dias[0] if cfg.recordatorio_dias else 3,
            "tolerancia_pago": cfg.tolerancia_monto,
        }
    except Exception:
        config = {
            "llave_breb": "—",
            "monto_matricula": 50000,
            "recargo_mora": 5000,
            "dias_recordatorio": 3,
            "tolerancia_pago": 5000,
        }
    return templates.TemplateResponse(
        request, "admin/configuracion.html", {"config": config}
    )


@router.get("/historial", response_class=HTMLResponse)
async def historial(request: Request):
    auth_resp = _auth(request)
    if auth_resp:
        return auth_resp
    vm = dashboard_svc.build_historial(_club_id(request))
    return templates.TemplateResponse(
        request, "admin/historial.html", {
            "historial": [
                {"hora": h.hora, "color": h.color, "icono": h.icono,
                 "texto": h.texto, "usuario": h.usuario, "tipo": h.tipo}
                for h in vm.historial
            ],
        }
    )


@router.get("/sistema", response_class=HTMLResponse)
async def sistema(request: Request):
    auth_resp = _auth(request)
    if auth_resp:
        return auth_resp
    ctx = DashboardService.build_sistema(request)
    return templates.TemplateResponse(
        request, "admin/sistema.html", {"sistema": {
            "version": ctx.version,
            "entorno": ctx.entorno,
            "python_version": ctx.python_version,
            "fastapi_version": ctx.fastapi_version,
            "ultimo_deploy": ctx.ultimo_deploy,
            "servidor": ctx.servidor,
            "gemini": ctx.gemini,
            "supabase": ctx.supabase,
            "whatsapp": ctx.whatsapp,
        }}
    )


# ──────────────────────────────────────────────
# API endpoints (para JS)
# ──────────────────────────────────────────────

@router.get("/api/notificaciones")
async def api_notificaciones(request: Request):
    auth_resp = _auth(request)
    if auth_resp:
        return JSONResponse([])
    return event_svc.notificaciones_recientes(_club_id(request), limite=10)


@router.get("/api/buscar")
async def api_buscar(request: Request, q: str = Query(min_length=2)):
    auth_resp = _auth(request)
    if auth_resp:
        return JSONResponse([])
    return dashboard_svc.buscar(_club_id(request), q)
