import logging, bcrypt, sys, fastapi, os, json
import httpx
from datetime import datetime as _dt
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

async def _enviar_whatsapp(numero, texto):
    try:
        TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
        if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_NUMBER]):
            logger.error("[TWILIO] Credenciales no configuradas")
            return False, "Credenciales no configuradas en .env"
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
        to_number = numero if numero.startswith("whatsapp:") else f"whatsapp:{numero}"
        data = {"From": f"whatsapp:{TWILIO_NUMBER}", "To": to_number, "Body": texto}
        logger.info(f"[TWILIO] Enviando a {to_number}")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, data=data, auth=(TWILIO_SID, TWILIO_TOKEN))
            if resp.status_code == 201:
                logger.info(f"[TWILIO] Mensaje enviado OK a {to_number}")
                return True, None
            detail = resp.text[:300]
            logger.error(f"[TWILIO] Error {resp.status_code}: {detail}")
            return False, f"HTTP {resp.status_code}: {detail}"
    except httpx.TimeoutException:
        logger.error("[TWILIO] Timeout enviando mensaje")
        return False, "Timeout conectando con Twilio"
    except Exception as e:
        logger.error(f"[TWILIO] Error enviando: {e}", exc_info=True)
        return False, str(e)

def _saludo():
    h = _dt.now().hour
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
    acciones = []
    timeline = []
    stats = {"ingresos_hoy": "0", "activos": 0, "total_deportistas": 0, "vencidas": 0, "mora_acumulada": "0", "tasa_cobro": 0}
    try:
        from db import supabase
        if supabase:
            r = supabase.table("contextos_conversacionales") \
                .select("id,numero_whatsapp,control,estado,updated_at") \
                .order("updated_at", desc=True) \
                .limit(10) \
                .execute()
            logger.info(f"[DASHBOARD] contextos: {len(r.data) if r.data else 0}")
            if r.data:
                stats["activos"] = len([c for c in r.data if c.get("estado") == "activa"])
                for ctx in r.data:
                    if ctx.get("estado") != "activa":
                        continue
                    numero = ctx["numero_whatsapp"]
                    control = ctx.get("control", "boy")
                    updated = ctx.get("updated_at", "")
                    conv_r = supabase.table("conversaciones") \
                        .select("contenido") \
                        .eq("numero", numero) \
                        .limit(1) \
                        .execute()
                    ultimo_msg = ""
                    if conv_r.data and conv_r.data[0].get("contenido"):
                        try:
                            msgs = json.loads(conv_r.data[0]["contenido"])
                            user_msgs = [m for m in msgs if m.get("rol") == "user"]
                            if user_msgs:
                                ultimo_msg = user_msgs[-1].get("content", "")[:120]
                        except Exception:
                            pass
                    logger.info(f"[DASHBOARD] ctx={numero} control={control} msg='{ultimo_msg[:40]}'")
                    if control == "ivonn" and ultimo_msg:
                        acciones.append({
                            "color": "#a855f7",
                            "texto": ultimo_msg,
                            "persona": numero,
                            "contexto_id": ctx["id"],
                        })
                    if ultimo_msg:
                        try:
                            fecha = _dt.fromisoformat(updated.replace("Z", "+00:00")).strftime("%d/%m %H:%M")
                        except Exception:
                            fecha = updated[:16] if updated else ""
                        dot = "success" if control == "boy" else "primary"
                        icono = "🤖" if control == "boy" else "👩"
                        timeline.append({
                            "dot_class": dot,
                            "hora": fecha,
                            "texto": f"{icono} {numero} — {ultimo_msg[:80]}",
                        })
            logger.info(f"[DASHBOARD] acciones={len(acciones)} timeline={len(timeline)}")
    except Exception as e:
        logger.error(f"[DASHBOARD] Error: {e}", exc_info=True)
    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "saludo": _saludo(),
        "nombre": request.session.get("nombre", "Ivonn"),
        "ultima_sincronizacion": "ahora",
        "resumen": [{"color": "green", "texto": f"{stats['activos']} conversación(es) activa(s)"}],
        "acciones": acciones,
        "timeline": timeline,
        "stats": stats,
    })

@router.get("/bandeja", response_class=HTMLResponse)
async def bandeja(request: Request):
    auth = _auth(request)
    if auth:
        return auth
    conversaciones = []
    total = 0
    try:
        from db import supabase
        if supabase:
            r = supabase.table("contextos_conversacionales") \
                .select("id,numero_whatsapp,control,estado,updated_at") \
                .eq("estado", "activa") \
                .order("updated_at", desc=True) \
                .execute()
            if r.data:
                for ctx in r.data:
                    conv_r = supabase.table("conversaciones") \
                        .select("contenido") \
                        .eq("numero", ctx["numero_whatsapp"]) \
                        .limit(1) \
                        .execute()
                    last_msg = ""
                    if conv_r.data and conv_r.data[0].get("contenido"):
                        try:
                            msgs = json.loads(conv_r.data[0]["contenido"])
                            if msgs:
                                last_msg = msgs[-1].get("content", "")[:80]
                        except Exception:
                            pass
                    conversaciones.append({
                        "contexto_id": ctx["id"],
                        "numero": ctx["numero_whatsapp"],
                        "control": ctx.get("control", "boy"),
                        "ultimo_mensaje": last_msg,
                        "updated_at": ctx.get("updated_at", "")
                    })
                total = len(conversaciones)
    except Exception as e:
        logger.error(f"[BANDEJA] Error: {e}")
    return templates.TemplateResponse(request, "admin/bandeja.html", {
        "conversaciones": conversaciones,
        "total": total
    })

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
    try:
        from db import supabase
        if not supabase:
            return JSONResponse([])
        r = supabase.table("notificaciones") \
            .select("id,tipo,icono,texto,referencia_id,created_at") \
            .eq("leida", False) \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute()
        if not r.data:
            return JSONResponse([])
        result = []
        for n in r.data:
            result.append({
                "id": n["id"],
                "icon": n.get("icono", "🔔"),
                "text": n["texto"],
                "time": n.get("created_at", ""),
                "tipo": n.get("tipo", ""),
                "referencia_id": n.get("referencia_id")
            })
        return JSONResponse(result)
    except Exception as e:
        if "notificaciones" in str(e) and "PGRST205" in str(e):
            return JSONResponse([])
        logger.error(f"[API] Error notificaciones: {e}")
        return JSONResponse([])

@router.get("/api/buscar")
async def api_buscar(request: Request, q: str = Query(min_length=2)):
    auth = _auth(request)
    if auth:
        return JSONResponse([])
    return JSONResponse([])

# ──────────────────────────────
# API CONVERSACIONES
# ──────────────────────────────

@router.get("/api/conversaciones")
async def api_conversaciones(request: Request):
    auth = _auth(request)
    if auth:
        return JSONResponse([])
    try:
        from db import supabase
        if not supabase:
            return JSONResponse([])
        r = supabase.table("contextos_conversacionales") \
            .select("id,numero_whatsapp,control,estado,created_at,updated_at") \
            .eq("estado", "activa") \
            .order("updated_at", desc=True) \
            .execute()
        if not r.data:
            return JSONResponse([])
        result = []
        for ctx in r.data:
            conv_r = supabase.table("conversaciones") \
                .select("contenido") \
                .eq("numero", ctx["numero_whatsapp"]) \
                .limit(1) \
                .execute()
            last_msg = ""
            if conv_r.data and conv_r.data[0].get("contenido"):
                try:
                    msgs = json.loads(conv_r.data[0]["contenido"])
                    if msgs:
                        last_msg = msgs[-1].get("content", "")[:100]
                except Exception:
                    pass
            result.append({
                "contexto_id": ctx["id"],
                "numero": ctx["numero_whatsapp"],
                "control": ctx.get("control", "boy"),
                "created_at": ctx.get("created_at", ""),
                "updated_at": ctx.get("updated_at", ""),
                "ultimo_mensaje": last_msg
            })
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"[API] Error listando conversaciones: {e}")
        return JSONResponse([])

@router.get("/api/conversacion/{contexto_id}")
async def api_conversacion_historial(request: Request, contexto_id: str):
    auth = _auth(request)
    if auth:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        from db import supabase
        if not supabase:
            return JSONResponse({"error": "no_db"}, status_code=500)
        ctx_r = supabase.table("contextos_conversacionales") \
            .select("id,numero_whatsapp,control,estado") \
            .eq("id", contexto_id) \
            .limit(1) \
            .execute()
        if not ctx_r.data:
            return JSONResponse({"error": "not_found"}, status_code=404)
        ctx = ctx_r.data[0]
        numero = ctx["numero_whatsapp"]
        conv_r = supabase.table("conversaciones") \
            .select("contenido") \
            .eq("numero", numero) \
            .limit(1) \
            .execute()
        messages = []
        if conv_r.data and conv_r.data[0].get("contenido"):
            try:
                messages = json.loads(conv_r.data[0]["contenido"])
            except Exception:
                pass
        return JSONResponse({
            "contexto_id": ctx["id"],
            "numero": numero,
            "control": ctx.get("control", "boy"),
            "estado": ctx.get("estado", "activa"),
            "mensajes": messages
        })
    except Exception as e:
        logger.error(f"[API] Error historial: {e}")
        return JSONResponse({"error": "server_error"}, status_code=500)

@router.post("/api/conversacion/{contexto_id}/tomar-control")
async def api_tomar_control(request: Request, contexto_id: str):
    auth = _auth(request)
    if auth:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        from db import supabase
        if not supabase:
            return JSONResponse({"error": "no_db"}, status_code=500)
        supabase.table("contextos_conversacionales") \
            .update({"control": "ivonn"}) \
            .eq("id", contexto_id) \
            .execute()
        return JSONResponse({"ok": True, "control": "ivonn"})
    except Exception as e:
        logger.error(f"[API] Error tomando control: {e}")
        return JSONResponse({"error": "server_error"}, status_code=500)

@router.post("/api/conversacion/{contexto_id}/devolver-control")
async def api_devolver_control(request: Request, contexto_id: str):
    auth = _auth(request)
    if auth:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        from db import supabase
        if not supabase:
            return JSONResponse({"error": "no_db"}, status_code=500)
        supabase.table("contextos_conversacionales") \
            .update({"control": "boy"}) \
            .eq("id", contexto_id) \
            .execute()
        return JSONResponse({"ok": True, "control": "boy"})
    except Exception as e:
        logger.error(f"[API] Error devolviendo control: {e}")
        return JSONResponse({"error": "server_error"}, status_code=500)

@router.post("/api/conversacion/{contexto_id}/responder")
async def api_responder(request: Request, contexto_id: str):
    auth = _auth(request)
    if auth:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        body = await request.json()
        texto = body.get("texto", "").strip()
        if not texto:
            return JSONResponse({"error": "texto_requerido"}, status_code=400)
        from db import supabase
        if not supabase:
            return JSONResponse({"error": "no_db"}, status_code=500)
        ctx_r = supabase.table("contextos_conversacionales") \
            .select("numero_whatsapp,control") \
            .eq("id", contexto_id) \
            .limit(1) \
            .execute()
        if not ctx_r.data:
            return JSONResponse({"error": "not_found"}, status_code=404)
        numero = ctx_r.data[0]["numero_whatsapp"]
        control = ctx_r.data[0].get("control", "boy")
        if control != "ivonn":
            logger.warning(f"[API] Intento de respuesta con control={control}: {contexto_id}")
            return JSONResponse({"error": "no_tiene_control"}, status_code=403)
        logger.info(f"[API] Enviando respuesta a {numero} ({contexto_id})")
        twilio_ok, twilio_err = await _enviar_whatsapp(numero, texto)
        if twilio_ok:
            from bot import _agregar_y_guardar
            _agregar_y_guardar(numero, "model", texto)
            logger.info(f"[API] Respuesta enviada OK a {numero}")
            return JSONResponse({"ok": True})
        logger.error(f"[API] Twilio fallo para {numero}: {twilio_err}")
        return JSONResponse({"error": "twilio_error", "detail": twilio_err}, status_code=500)
    except Exception as e:
        logger.error(f"[API] Error respondiendo: {e}", exc_info=True)
        return JSONResponse({"error": "server_error"}, status_code=500)
