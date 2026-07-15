import logging, bcrypt, sys, fastapi, os
from datetime import datetime
from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from google import genai

logger = logging.getLogger("boy.admin")

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

def _ctx(request):
    return {"session": dict(request.session)}
templates.context_processors.insert(0, _ctx)

ADMIN_HASH = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
ADMIN = {"usuario": "ivonn", "nombre": "Ivonn", "hash": ADMIN_HASH, "rol": "administrador"}

def _auth(request):
    if "usuario" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    return None

def _saludo():
    h = datetime.now().hour
    return "días" if h < 12 else "tardes" if h < 18 else "noches"

login_router = APIRouter(tags=["auth"])

@login_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    if "usuario" in request.session:
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": error})

@login_router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...), recordarme: str = Form("")):
    if username == ADMIN["usuario"] and bcrypt.checkpw(password.encode(), ADMIN["hash"].encode()):
        request.session["usuario"] = ADMIN["usuario"]
        request.session["nombre"] = ADMIN["nombre"]
        request.session["rol"] = ADMIN["rol"]
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": "Usuario o contraseña incorrectos"}, status_code=401)

@login_router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    auth = _auth(request)
    if auth:
        return auth
    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "saludo": _saludo(),
        "nombre": request.session.get("nombre", "Ivonn"),
        "ultima_sincronizacion": "ahora",
        "resumen": [{"color": "green", "texto": "BOY activo y respondiendo"}],
        "acciones": [],
        "timeline": [],
        "stats": {"ingresos_hoy": "0", "activos": 0, "total_deportistas": 0, "vencidas": 0, "mora_acumulada": "0", "tasa_cobro": 0},
    })

@router.get("/bandeja", response_class=HTMLResponse)
async def bandeja(request: Request):
    auth = _auth(request)
    if auth:
        return auth
    return templates.TemplateResponse(request, "admin/bandeja.html", {"grupos": [], "total": 0})

@router.get("/deportistas", response_class=HTMLResponse)
async def deportistas(request: Request):
    auth = _auth(request)
    if auth:
        return auth
    return templates.TemplateResponse(request, "admin/deportistas.html", {"deportistas": [], "total": 0, "activos": 0})

@router.get("/finanzas", response_class=HTMLResponse)
async def finanzas(request: Request):
    auth = _auth(request)
    if auth:
        return auth
    return templates.TemplateResponse(request, "admin/finanzas.html", {"datos": {
        "ingresos_hoy": "0", "pagos_hoy": 0, "ingresos_mes": "0", "pagos_mes": 0,
        "pagadas": 0, "total_mensualidades": 0, "pendientes": 0, "monto_pendiente": "0",
        "mora_acumulada": "0", "vencidas": 0, "tasa_cobro": 0,
        "ultimos_pagos": [], "conceptos": [],
    }})

@router.get("/configuracion", response_class=HTMLResponse)
async def configuracion(request: Request):
    auth = _auth(request)
    if auth:
        return auth
    return templates.TemplateResponse(request, "admin/configuracion.html", {"config": {
        "llave_breb": "—", "monto_matricula": 50000, "recargo_mora": 5000,
        "dias_recordatorio": 3, "tolerancia_pago": 5000,
    }})

@router.get("/historial", response_class=HTMLResponse)
async def historial(request: Request):
    auth = _auth(request)
    if auth:
        return auth
    return templates.TemplateResponse(request, "admin/historial.html", {"historial": []})

@router.get("/sistema", response_class=HTMLResponse)
async def sistema(request: Request):
    auth = _auth(request)
    if auth:
        return auth
    gemini_ok = False
    try:
        genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        gemini_ok = True
    except Exception:
        pass
    return templates.TemplateResponse(request, "admin/sistema.html", {"sistema": {
        "version": "2.1.0", "entorno": "Desarrollo" if not os.getenv("RENDER") else "Producción",
        "python_version": sys.version.split()[0],
        "fastapi_version": fastapi.__version__,
        "ultimo_deploy": "2026-07-07",
        "servidor": {"plataforma": "Render", "uptime": "—", "version": "2.1.0"},
        "gemini": {"online": gemini_ok, "modelo": "gemini-2.5-flash-lite", "ultimo_error": None},
        "supabase": {"online": False, "proyecto": "—", "registros": "—", "ultimo_backup": "—"},
        "whatsapp": {"ultimo_mensaje": "—", "mensajes_hoy": 0},
    }})

@router.get("/api/notificaciones")
async def api_notificaciones(request: Request):
    auth = _auth(request)
    if auth:
        return JSONResponse([])
    return JSONResponse([])

@router.get("/api/buscar")
async def api_buscar(request: Request, q: str = Query(min_length=2)):
    auth = _auth(request)
    if auth:
        return JSONResponse([])
    return JSONResponse([])
