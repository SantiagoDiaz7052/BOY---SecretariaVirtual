from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from routers.auth import usuario_autenticado

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

# Context processor: expone session y request a todas las templates
def _context_processor(request: Request) -> dict:
    return {"session": dict(request.session)}

templates.context_processors.insert(0, _context_processor)


def _auth(request: Request):
    if not usuario_autenticado(request):
        return RedirectResponse(url="/login", status_code=303)
    return None

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
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


def _saludo() -> str:
    h = datetime.now().hour
    if h < 12:
        return "días"
    elif h < 18:
        return "tardes"
    return "noches"


# ──────────────────────────────────────────────
# Router principal
# ──────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    auth_resp = _auth(request); 
    if auth_resp: 
        return auth_resp
    nombre = request.session.get("nombre", "Ivonn")
    resumen = [
        {"color": "red", "texto": "3 comprobantes por revisar"},
        {"color": "orange", "texto": "2 deportistas por evaluar"},
        {"color": "green", "texto": "15 deportistas activos"},
    ]
    acciones = [
        {"color": "#ef4444", "texto": "Aprobar pago de Carlos Gómez", "persona": "Matrícula · $50,000"},
        {"color": "#f59e0b", "texto": "Evaluar a Laura Martínez", "persona": "Nueva solicitud de ingreso"},
        {"color": "#3b82f6", "texto": "Activar deportista Juan Pérez", "persona": "Matrícula pagada · Pendiente activación"},
        {"color": "#f59e0b", "texto": "Revisar comprobante de Mateo López", "persona": "Matrícula · Nequi"},
    ]
    timeline = [
        {"hora": "22:30", "dot_class": "success", "icono": "✅", "texto": "Carlos Pérez fue ACTIVADO"},
        {"hora": "22:28", "dot_class": "warning", "icono": "💳", "texto": "Laura envió comprobante"},
        {"hora": "22:25", "dot_class": "primary", "icono": "📝", "texto": "Se creó solicitud de Sofía Ramírez"},
        {"hora": "22:12", "dot_class": "success", "icono": "✅", "texto": "Ivonn aprobó un pago"},
        {"hora": "21:50", "dot_class": "info", "icono": "📅", "texto": "Mensualidades generadas"},
        {"hora": "21:30", "dot_class": "danger", "icono": "⚠️", "texto": "Mensualidad de Carlos vencida"},
    ]
    stats = {
        "ingresos_hoy": "50,000",
        "activos": 15,
        "total_deportistas": 18,
        "vencidas": 8,
        "mora_acumulada": "240,000",
        "tasa_cobro": 56,
    }
    return templates.TemplateResponse(
        request, "admin/dashboard.html", {
            "saludo": _saludo(),
            "nombre": nombre,
            "ultima_sincronizacion": "12 segundos",
            "resumen": resumen,
            "acciones": acciones,
            "timeline": timeline,
            "stats": stats,
        }
    )


@router.get("/bandeja", response_class=HTMLResponse)
async def bandeja(request: Request):
    auth_resp = _auth(request); 
    if auth_resp: 
        return auth_resp
    items = [
        {"tipo": "evaluacion", "color": "#ef4444", "texto": "Evaluar solicitud de ingreso",
         "persona": "Laura Martínez", "detalle": "Nuevo aspirante · Sin experiencia",
         "hace": "hace 10 min"},
        {"tipo": "evaluacion", "color": "#ef4444", "texto": "Evaluar solicitud de ingreso",
         "persona": "Sofía Ramírez", "detalle": "Nuevo aspirante · No sabe",
         "hace": "hace 2h"},
        {"tipo": "evaluacion", "color": "#ef4444", "texto": "Evaluar solicitud de ingreso",
         "persona": "Pedro Gómez", "detalle": "Nuevo aspirante",
         "hace": "hace 1d"},
        {"tipo": "comprobante", "color": "#f59e0b", "texto": "Revisar comprobante de pago",
         "persona": "Mateo López", "detalle": "Matrícula · $50,000 · Nequi",
         "hace": "hace 30 min"},
        {"tipo": "comprobante", "color": "#f59e0b", "texto": "Revisar comprobante de pago",
         "persona": "Carlos Gómez", "detalle": "Mensualidad · $30,000 · Transferencia",
         "hace": "hace 2h"},
        {"tipo": "activacion", "color": "#3b82f6", "texto": "Activar deportista",
         "persona": "Juan Pérez", "detalle": "Matrícula pagada · Pendiente activación",
         "hace": "hace 1d"},
        {"tipo": "vencida", "color": "#8b5cf6", "texto": "Mensualidad vencida",
         "persona": "Sofía Ramírez", "detalle": "Mensualidad junio · $30,000",
         "hace": "hace 3d"},
        {"tipo": "vencida", "color": "#8b5cf6", "texto": "Mensualidad vencida",
         "persona": "Carlos Pérez", "detalle": "Mensualidad junio · $30,000",
         "hace": "hace 5d"},
    ]
    grupos = [
        {"key": "evaluacion", "titulo": "🔴 Evaluación pendiente",
         "lista": [i for i in items if i["tipo"] == "evaluacion"]},
        {"key": "comprobante", "titulo": "🟡 Comprobante por revisar",
         "lista": [i for i in items if i["tipo"] == "comprobante"]},
        {"key": "activacion", "titulo": "🔵 Activación pendiente",
         "lista": [i for i in items if i["tipo"] == "activacion"]},
        {"key": "vencida", "titulo": "🟠 Mensualidad vencida",
         "lista": [i for i in items if i["tipo"] == "vencida"]},
    ]
    return templates.TemplateResponse(
        request, "admin/bandeja.html", {"grupos": grupos, "total": len(items)}
    )


@router.get("/deportistas", response_class=HTMLResponse)
async def deportistas(request: Request):
    auth_resp = _auth(request); 
    if auth_resp: 
        return auth_resp
    lista = [
        {"id": "1", "nombre": "Valentina Gómez", "documento": "9988776655",
         "nivel": "Iniciación", "estado": "Activo", "badge": "success",
         "ultimo_pago": "2026-07-01", "telefono": "3008889900"},
        {"id": "2", "nombre": "Carlos Pérez", "documento": "0987654321",
         "nivel": "Intermedio", "estado": "Inactivo", "badge": "danger",
         "ultimo_pago": "2026-05-15", "telefono": "3004445566"},
        {"id": "3", "nombre": "Sofía Ramírez", "documento": "1122334455",
         "nivel": None, "estado": "Inactivo", "badge": "danger",
         "ultimo_pago": None, "telefono": "3007778899"},
        {"id": "4", "nombre": "Mateo López", "documento": "5544332211",
         "nivel": "Avanzado", "estado": "Inactivo", "badge": "danger",
         "ultimo_pago": None, "telefono": "3002223344"},
        {"id": "5", "nombre": "Laura Martínez", "documento": "1234567890",
         "nivel": None, "estado": "Inactivo", "badge": "danger",
         "ultimo_pago": None, "telefono": "3001112233"},
        {"id": "6", "nombre": "Juan Pérez", "documento": "5566778899",
         "nivel": "Iniciación", "estado": "Inactivo", "badge": "danger",
         "ultimo_pago": None, "telefono": "3005556677"},
    ]
    return templates.TemplateResponse(
        request, "admin/deportistas.html", {
            "deportistas": lista,
            "total": len(lista),
            "activos": sum(1 for d in lista if d["estado"] == "Activo"),
        }
    )


@router.get("/finanzas", response_class=HTMLResponse)
async def finanzas(request: Request):
    auth_resp = _auth(request); 
    if auth_resp: 
        return auth_resp
    datos = {
        "ingresos_hoy": "50,000",
        "pagos_hoy": 1,
        "ingresos_mes": "450,000",
        "pagos_mes": 12,
        "pagadas": 10,
        "total_mensualidades": 18,
        "pendientes": 8,
        "monto_pendiente": "240,000",
        "mora_acumulada": "240,000",
        "vencidas": 8,
        "tasa_cobro": 56,
        "ultimos_pagos": [
            {"deportista": "Mateo López", "concepto": "Matrícula", "monto": "50,000",
             "estado": "Pendiente", "badge": "warning"},
            {"deportista": "Valentina Gómez", "concepto": "Matrícula", "monto": "50,000",
             "estado": "Aprobado", "badge": "success"},
            {"deportista": "Carlos Pérez", "concepto": "Mensualidad", "monto": "30,000",
             "estado": "En revisión", "badge": "info"},
        ],
        "conceptos": [
            {"nombre": "Mensualidad", "monto": "30,000", "activo": True},
            {"nombre": "Matrícula", "monto": "50,000", "activo": True},
            {"nombre": "Uniforme", "monto": "80,000", "activo": True},
            {"nombre": "Evento", "monto": "20,000", "activo": True},
            {"nombre": "Licra", "monto": "15,000", "activo": False},
        ],
    }
    return templates.TemplateResponse(
        request, "admin/finanzas.html", {"datos": datos}
    )


@router.get("/configuracion", response_class=HTMLResponse)
async def configuracion(request: Request):
    auth_resp = _auth(request); 
    if auth_resp: 
        return auth_resp
    config = {
        "llave_breb": "3101234567",
        "monto_matricula": 50000,
        "recargo_mora": 5000,
        "dias_recordatorio": 3,
        "tolerancia_pago": 5,
    }
    return templates.TemplateResponse(
        request, "admin/configuracion.html", {"config": config}
    )


@router.get("/historial", response_class=HTMLResponse)
async def historial(request: Request):
    auth_resp = _auth(request); 
    if auth_resp: 
        return auth_resp
    ahora = datetime.now()
    entries = [
        {"hora": "09:13", "color": "success", "icono": "✅",
         "texto": "Carlos Pérez fue ACTIVADO", "usuario": "Ivonn", "tipo": "activacion"},
        {"hora": "09:20", "color": "warning", "icono": "💳",
         "texto": "Laura Martínez envió comprobante", "usuario": None, "tipo": "pago"},
        {"hora": "09:32", "color": "success", "icono": "✅",
         "texto": "Ivonn aprobó un pago de Mateo López", "usuario": "Ivonn", "tipo": "pago"},
        {"hora": "10:01", "color": "primary", "icono": "📝",
         "texto": "Se creó solicitud de Sofía Ramírez", "usuario": None, "tipo": "solicitud"},
        {"hora": "10:07", "color": "info", "icono": "📅",
         "texto": "Mensualidades de julio generadas automáticamente", "usuario": "Sistema", "tipo": "sistema"},
        {"hora": "11:15", "color": "danger", "icono": "⚠️",
         "texto": "Mensualidad de Carlos Pérez marcada como vencida", "usuario": "Sistema", "tipo": "sistema"},
        {"hora": "11:30", "color": "warning", "icono": "💳",
         "texto": "Carlos Gómez envió comprobante de mensualidad", "usuario": None, "tipo": "pago"},
        {"hora": "14:00", "color": "primary", "icono": "📝",
         "texto": "Se creó solicitud de Pedro Gómez", "usuario": None, "tipo": "solicitud"},
        {"hora": "14:22", "color": "success", "icono": "✅",
         "texto": "Ivonn evaluó y asignó nivel a Laura Martínez", "usuario": "Ivonn", "tipo": "solicitud"},
        {"hora": "14:45", "color": "warning", "icono": "💳",
         "texto": "Juan Pérez envió comprobante de matrícula", "usuario": None, "tipo": "pago"},
    ]
    return templates.TemplateResponse(
        request, "admin/historial.html", {"historial": entries}
    )


@router.get("/sistema", response_class=HTMLResponse)
async def sistema(request: Request):
    auth_resp = _auth(request); 
    if auth_resp: 
        return auth_resp
    import sys
    import fastapi
    ctx = {
        "version": "2.1.0",
        "entorno": "Desarrollo",
        "python_version": sys.version.split()[0],
        "fastapi_version": fastapi.__version__,
        "ultimo_deploy": "2026-07-07",
        "servidor": {
            "plataforma": "Render",
            "uptime": "12h 34m",
            "version": "2.1.0",
        },
        "gemini": {
            "online": True,
            "modelo": "gemini-2.5-flash-lite",
            "fallback": "gemini-2.5-flash",
            "ultimo_error": None,
        },
        "supabase": {
            "online": True,
            "proyecto": "boy-secretaria",
            "registros": "1,234",
            "ultimo_backup": "Hace 1 día",
        },
        "whatsapp": {
            "ultimo_mensaje": "Hace 3 min",
            "mensajes_hoy": 47,
        },
    }
    return templates.TemplateResponse(
        request, "admin/sistema.html", {"sistema": ctx}
    )


# ──────────────────────────────────────────────
# API endpoints (para JS)
# ──────────────────────────────────────────────

@router.get("/api/notificaciones")
async def api_notificaciones(request: Request):
    auth_resp = _auth(request); 
    if auth_resp: 
        return JSONResponse([])
    from repositories.notificacion_repo import NotificacionRepository
    repo = NotificacionRepository()
    club_id = request.session.get("club_id", "default")
    notis = repo.listar_recientes(club_id, limite=10)
    return [
        {
            "id": n.id or "",
            "icon": n.icono,
            "text": n.texto,
            "time": _time_ago(datetime.fromisoformat(n.created_at)) if n.created_at else "ahora",
        }
        for n in notis
    ]


@router.get("/api/buscar")
async def api_buscar(request: Request, q: str = Query(min_length=2)):
    auth_resp = _auth(request); 
    if auth_resp: 
        return JSONResponse([])
    db = [
        {"id": "1", "nombre": "Valentina Gómez", "documento": "9988776655",
         "nivel": "Iniciación", "estado": "Activo", "telefono": "3008889900"},
        {"id": "2", "nombre": "Carlos Pérez", "documento": "0987654321",
         "nivel": "Intermedio", "estado": "Inactivo", "telefono": "3004445566"},
        {"id": "3", "nombre": "Sofía Ramírez", "documento": "1122334455",
         "nivel": None, "estado": "Inactivo", "telefono": "3007778899"},
        {"id": "4", "nombre": "Mateo López", "documento": "5544332211",
         "nivel": "Avanzado", "estado": "Inactivo", "telefono": "3002223344"},
        {"id": "5", "nombre": "Laura Martínez", "documento": "1234567890",
         "nivel": None, "estado": "Inactivo", "telefono": "3001112233"},
        {"id": "6", "nombre": "Juan Pérez", "documento": "5566778899",
         "nivel": "Iniciación", "estado": "Inactivo", "telefono": "3005556677"},
    ]
    ql = q.lower()
    results = [
        d for d in db
        if ql in d["nombre"].lower() or ql in d["documento"] or ql in d.get("telefono", "")
    ]
    return results[:8]
