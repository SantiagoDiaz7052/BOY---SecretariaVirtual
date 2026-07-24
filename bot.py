import json, logging, time, threading, os
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("boy.bot")

router = APIRouter()

# ──────────────────────────────
# CIRCUIT BREAKER
# ──────────────────────────────

class CircuitBreaker:
    def __init__(self, threshold=2, recovery=120):
        self.threshold = threshold
        self.recovery = recovery
        self.fails = 0
        self.last_fail = 0.0
        self.state = "CLOSED"
        self._lock = threading.Lock()

    def ok(self):
        with self._lock:
            self.fails = 0
            self.state = "CLOSED"

    def fail(self):
        with self._lock:
            self.fails += 1
            self.last_fail = time.time()
            if self.fails >= self.threshold:
                self.state = "OPEN"

    def disponible(self) -> bool:
        with self._lock:
            if self.state == "CLOSED":
                return True
            if self.state == "OPEN" and time.time() - self.last_fail >= self.recovery:
                self.state = "HALF_OPEN"
                return True
            return self.state == "HALF_OPEN"

_cb = CircuitBreaker()

# ──────────────────────────────
# GEMINI (cliente singleton)
# ──────────────────────────────

_client = None

def _cliente():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY no configurada")
        _client = genai.Client(api_key=api_key)
    return _client

# ──────────────────────────────
# GEMINI - GENERAR
# ──────────────────────────────

def gemini_generar(contents, config):
    max_intentos = 3
    modelos = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
    for i in range(max_intentos):
        modelo = modelos[0] if i == 0 else modelos[-1]
        try:
            resp = _cliente().models.generate_content(model=modelo, contents=contents, config=config)
            if resp.candidates:
                return {"ok": True, "data": resp}
            return {"ok": False, "error": "sin_candidates"}
        except ServerError as e:
            err = str(e)
            logger.warning(f"[GEMINI] {modelo}: {err}")
            if "503" in err or "UNAVAILABLE" in err:
                if "gemini-2.5-flash" not in modelo:
                    continue
            if i < max_intentos - 1:
                time.sleep(min(2 * (2 ** i), 10))
                continue
            return {"ok": False, "error": err}
        except Exception as e:
            logger.error(f"[GEMINI] {modelo}: {e}")
            if i < max_intentos - 1:
                time.sleep(2)
                continue
            return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "max_intentos"}

# ──────────────────────────────
# SUPABASE - PROMPT (solo de BD)
# ──────────────────────────────

_prompt_cache = {"valor": None, "ts": 0}

def _cargar_prompt():
    ahora = time.time()
    if _prompt_cache["valor"] and ahora - _prompt_cache["ts"] < 300:
        return _prompt_cache["valor"]
    from db import supabase
    if not supabase:
        raise RuntimeError("Supabase no disponible para cargar prompt")
    r = supabase.table("configuracion").select("valor").eq("id", "system_prompt").execute()
    if not r.data or len(r.data) == 0:
        raise RuntimeError("system_prompt no encontrado en configuracion")
    _prompt_cache["valor"] = r.data[0]["valor"]
    _prompt_cache["ts"] = ahora
    return _prompt_cache["valor"]

# ──────────────────────────────
# SUPABASE - MEMORIA (1 fila por número, resumen en content)
# ──────────────────────────────

MAX_MENSAJES = 8

def _leer_conversacion(numero):
    try:
        from db import supabase
        if not supabase:
            return [], None
        r = supabase.table("conversaciones").select("id,contenido").eq("numero", numero).execute()
        if r.data and len(r.data) > 0:
            row = r.data[0]
            datos = json.loads(row["contenido"]) if row["contenido"] else []
            return datos, row["id"]
        return [], None
    except Exception as e:
        logger.warning(f"[MEMORIA] Error leyendo: {e}")
        return [], None

def _guardar_conversacion(numero, mensajes, row_id=None):
    try:
        from db import supabase
        if not supabase:
            return
        contenido = json.dumps(mensajes, ensure_ascii=False)
        if row_id:
            supabase.table("conversaciones").update({"contenido": contenido}).eq("id", row_id).execute()
        else:
            supabase.table("conversaciones").insert({"numero": numero, "contenido": contenido}).execute()
    except Exception as e:
        logger.warning(f"[MEMORIA] Error guardando: {e}")

def _resumir(mensajes):
    try:
        from db import supabase
        texto = "\n".join([f"{m['rol']}: {m['content']}" for m in mensajes])
        resp = _cliente().models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"Resume esta conversación en 2-3 oraciones. Sé conciso:\n\n{texto}",
            config=types.GenerateContentConfig(
                max_output_tokens=150,
                temperature=0.3,
            ),
        )
        return (resp.text or "").strip() or "Conversación sin detalles relevantes."
    except Exception as e:
        logger.warning(f"[RESUMEN] Error: {e}")
        return "Conversación sin detalles relevantes."

def _agregar_y_guardar(numero, rol, contenido):
    mensajes, row_id = _leer_conversacion(numero)
    mensajes.append({"rol": rol, "content": contenido})

    mensajes_reales = [m for m in mensajes if m["rol"] != "resumen"]
    if len(mensajes_reales) > MAX_MENSAJES:
        resumen_texto = _resumir(mensajes)
        mensajes = [{"rol": "resumen", "content": resumen_texto}]

    _guardar_conversacion(numero, mensajes, row_id)

def _obtener_historial(numero):
    mensajes, _ = _leer_conversacion(numero)
    return mensajes

# ──────────────────────────────
# CONTROL DE CONVERSACIÓN
# ──────────────────────────────

def _verificar_control(numero):
    try:
        from db import supabase
        if not supabase:
            return "boy", None
        r = supabase.table("contextos_conversacionales") \
            .select("id,control") \
            .eq("numero_whatsapp", numero) \
            .eq("estado", "activa") \
            .limit(1) \
            .execute()
        if r.data and len(r.data) > 0:
            return r.data[0].get("control", "boy"), r.data[0]["id"]
        club_r = supabase.table("clubs").select("id").eq("activo", True).limit(1).execute()
        if not club_r.data or len(club_r.data) == 0:
            logger.warning(f"[CONTROL] No hay club activo: {numero}")
            return "boy", None
        club_id = club_r.data[0]["id"]
        result = supabase.table("contextos_conversacionales").insert({
            "club_id": club_id,
            "numero_whatsapp": numero,
            "estado": "activa",
            "control": "boy"
        }).select("id").execute()
        contexto_id = result.data[0]["id"] if result.data else None
        return "boy", contexto_id
    except Exception as e:
        logger.warning(f"[CONTROL] Error: {e}")
        return "boy", None

# ──────────────────────────────
# DETECCIÓN DE SITUACIONES
# ──────────────────────────────

SITUACION_PROMPT = """Eres un clasificador de situaciones para una secretaria de club de patinaje.
Analiza el mensaje del usuario y responde SOLO con una de estas opciones exactas:

visita → quiere ir al club, visitar, conocer, pasar hoy/esta noche, llevar a su hijo
inscripcion → quiere inscribirse, registrar, matricular, iniciar proceso
atencion_humana → quiere hablar con persona, secretaria, necesita ayuda humana
pago → envió comprobante, reporta pago, transferencia, factura, recibo
ninguna → pregunta normal sobre precios, horarios, grupos, información general"""

SITUACIONES = {
    "visita":         {"tipo": "interes",          "icono": "📍", "texto": "El padre muestra interés en visitar el club"},
    "inscripcion":    {"tipo": "inscripcion",       "icono": "📝", "texto": "El padre quiere iniciar el proceso de inscripción"},
    "atencion_humana":{"tipo": "atencion_humana",   "icono": "👤", "texto": "El padre solicita atención humana"},
    "pago":           {"tipo": "comprobante_pago",  "icono": "💰", "texto": "El padre envió un comprobante o reporta un pago"},
}

TRIGGERS_DETECCION = [
    "ir", "visitar", "conocer", "pasar", "llevar", "hoy", "noche", "mañana",
    "inscribir", "inscripción", "registrar", "matricular",
    "hablar", "secretaria", "persona", "atender", "ayuda",
    "comprobante", "pagué", "transferí", "factura", "recibo",
]

def _tiene_trigger(texto):
    t = texto.lower()
    return any(trig in t for trig in TRIGGERS_DETECCION)

def _clasificar_situacion(texto):
    try:
        resp = _cliente().models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=texto,
            config=types.GenerateContentConfig(
                system_instruction=SITUACION_PROMPT,
                max_output_tokens=15,
                temperature=0.0,
            ),
        )
        resultado = (resp.text or "").strip().lower()
        logger.info(f"[SITUACION] '{texto[:40]}' → {resultado}")
        return SITUACIONES.get(resultado)
    except Exception as e:
        logger.warning(f"[SITUACION] Error: {e}")
        return None

def _crear_notificacion(tipo, texto, contexto_id, icono="🔔"):
    try:
        from db import supabase
        if not supabase or not contexto_id:
            return
        r = supabase.table("notificaciones") \
            .select("id") \
            .eq("tipo", tipo) \
            .eq("referencia_id", contexto_id) \
            .eq("leida", False) \
            .limit(1) \
            .execute()
        if r.data and len(r.data) > 0:
            return
        supabase.table("notificaciones").insert({
            "tipo": tipo,
            "icono": icono,
            "texto": texto,
            "referencia_id": contexto_id,
        }).execute()
        logger.info(f"[NOTIF] Creada: {tipo} para {contexto_id}")
    except Exception as e:
        logger.warning(f"[NOTIF] Error creando: {e}")

# ──────────────────────────────
# CHAT
# ──────────────────────────────

def gemini_chat(historial, mensaje):
    if not _cb.disponible():
        return "Estoy teniendo un problema temporal. Intenta de nuevo en unos minutos."

    try:
        prompt = _cargar_prompt()
    except Exception as e:
        logger.error(f"[PROMPT] Error: {e}")
        return "Estoy teniendo un problema con la configuración. Intenta de nuevo."

    contents = []
    for m in historial:
        if m["rol"] == "resumen":
            contents.append(types.Content(role="user", parts=[types.Part(text=m["content"])]))
            contents.append(types.Content(role="model", parts=[types.Part(text="Contexto entendido.")]))
        else:
            role = "user" if m["rol"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=mensaje)]))

    config = types.GenerateContentConfig(
        system_instruction=prompt,
        max_output_tokens=500,
        temperature=0.7,
    )

    r = gemini_generar(contents, config)
    if not r["ok"]:
        logger.error(f"[GEMINI] Fallo: {r['error']}")
        _cb.fail()
        return "Estoy teniendo un problema temporal. Intenta de nuevo en unos minutos."
    _cb.ok()
    return r["data"].text or "..." if r["data"] else "..."

# ──────────────────────────────
# CLASIFICACIÓN DE HORARIO
# ──────────────────────────────

CLASIFICAR_PROMPT = """Eres un clasificador de intenciones para un club de patinaje.
Analiza el mensaje del usuario y responde SOLO con una de estas opciones exactas:

iniciacion → quiere ver horario de iniciación, niños pequeños, 3-5 años, principiantes
intermedio → quiere ver horario de intermedio, técnica básica, 6-12 años
avanzado → quiere ver horario de avanzado, competitivo, alto rendimiento, 13+ años
melgar → quiere ver horarios de Melgar o pregunta por la sede Melgar
todos → quiere ver todos los horarios, los 3 horarios, todos los niveles, o no sabe cuál elegir
ninguno → no habla de horarios ni niveles"""

IMAGENES = {
    "iniciacion": "StarLINE-iniciacion.jpeg",
    "intermedio": "StarLINE-intermedio.jpeg",
    "avanzado": "StarLINE-avanzado.jpeg",
    "melgar": "StarLINE-melgar.jpeg",
}

RESPUESTAS_HORARIO = {
    "iniciacion": (
        "¡Bienvenidos a la temporada 2026! 🎉🛼\n\n"
        "📌 *Grupo Iniciación* ✓\n"
        "Mensualidad tiene un costo de $99.999 y entrenan 4 veces a la semana ✅\n\n"
        "Cuéntame, ¿te gustaría inscribirte o necesitas más información? 😊"
    ),
    "intermedio": (
        "¡Bienvenidos a la temporada 2026! 🎉🛼\n\n"
        "📌 *Grupo Intermedio* ✓\n"
        "Mensualidad tiene un costo de $99.999 y entrenan 6 días a la semana 🏅\n\n"
        "Cuéntame, ¿te gustaría inscribirte o necesitas más información? 😊"
    ),
    "avanzado": (
        "¡Bienvenidos a la temporada 2026! 🎉🛼\n\n"
        "📌 *Grupo Avanzado* ✓\n"
        "Mensualidad tiene un costo de $110.000 y entrenan 8 jornadas a la semana 🏆\n\n"
        "Cuéntame, ¿te gustaría inscribirte o necesitas más información? 😊"
    ),
    "melgar": (
        "¡Bienvenidos a la temporada 2026 Melgar! 🎉🛼\n\n"
        "A continuación te enviamos la información de interés:\n\n"
        "📌 Matrícula tiene un costo de $50.000 pesos 💲\n\n"
        "*Grupo Único* 🛼\n"
        "Mensualidad tiene un costo de $89.999 y entrenan martes, miércoles, jueves y sábado 🗓️\n\n"
        "Opción de asistencia 1 vez a la semana en nuestra sede en Girardot 🔥\n\n"
        "¿Te gustaría inscribirte o necesitas más información? 😊"
    ),
    "todos": (
        "¡Claro! Te muestro todos nuestros horarios 🛼💙\n\n"
        "• *Iniciación*: $99.999/mes, 4 veces por semana\n"
        "• *Intermedio*: $99.999/mes, 6 días por semana\n"
        "• *Avanzado*: $110.000/mes, 8 jornadas por semana\n\n"
        "¿Cuál grupo te interesa conocer? 😊"
    ),
}

def clasificar_nivel(mensaje):
    try:
        resp = _cliente().models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=mensaje,
            config=types.GenerateContentConfig(
                system_instruction=CLASIFICAR_PROMPT,
                max_output_tokens=15,
                temperature=0.0,
            ),
        )
        resultado = (resp.text or "").strip().lower()
        logger.info(f"[CLASIFICAR] '{mensaje[:40]}' → {resultado}")

        if resultado == "todos":
            return None, RESPUESTAS_HORARIO["todos"]

        imagen = IMAGENES.get(resultado)
        if imagen:
            return imagen, RESPUESTAS_HORARIO.get(resultado, "Acá te va el horario 🛼")

        return None, None
    except Exception as e:
        logger.error(f"[CLASIFICAR] Error: {e}")
        return None, None

# ──────────────────────────────
# WEBHOOK
# ──────────────────────────────

@router.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request):
    import xml.sax.saxutils as saxutils

    try:
        form = await request.form()
        numero = form.get("From", "")
        texto = form.get("Body", "").strip()

        print(f"[WH-debug] De: {numero} | Msg: {texto[:50]}")

        control, contexto_id = _verificar_control(numero)
        print(f"[WH-debug] Control: {control}")
        _agregar_y_guardar(numero, "user", texto)

        if control == "ivonn":
            print(f"[WH-debug] Control Ivonn, sin respuesta")
            return PlainTextResponse(
                content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                media_type="text/xml"
            )

        if control == "boy" and _tiene_trigger(texto):
            sit = _clasificar_situacion(texto)
            if sit:
                _crear_notificacion(sit["tipo"], sit["texto"], contexto_id, sit["icono"])

        imagen, respuesta_clasif = clasificar_nivel(texto)
        print(f"[WH-debug] Clasificar: imagen={imagen} resp={str(respuesta_clasif)[:60]}")

        if imagen:
            respuesta = respuesta_clasif
        elif respuesta_clasif:
            respuesta = respuesta_clasif
        else:
            historial = _obtener_historial(numero)
            respuesta = gemini_chat(historial, texto)
            print(f"[WH-debug] Gemini resp: {str(respuesta)[:80]}")

        _agregar_y_guardar(numero, "model", respuesta)

    except Exception as e:
        print(f"[WH-debug] ERROR: {e}")
        logger.error(f"[WEBHOOK] Error: {e}", exc_info=True)
        respuesta = "Ocurrió un error. Intenta de nuevo."
        imagen = None

    safe = saxutils.escape(str(respuesta))

    if imagen:
        host = request.headers.get("host", "")
        url = f"https://{host}/static/img/{imagen}"
        twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message><Body>{safe}</Body><Media>{url}</Media></Message></Response>'
    else:
        twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{safe}</Message></Response>'

    print(f"[WH-debug] TwiML length: {len(twiml)} | First 200: {twiml[:200]}")
    return PlainTextResponse(content=twiml, media_type="text/xml")
