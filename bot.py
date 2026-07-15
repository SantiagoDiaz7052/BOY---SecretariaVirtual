import logging, time, threading, os
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
# SUPABASE - PROMPT
# ──────────────────────────────

PROMPT_DEFAULT = """
Eres BOY, el asistente virtual del STAR CLUB DEPORTIVO.

PERSONALIDAD:
- Responde siempre en español, con energía y actitud
- Sin rodeos, ve al grano
- Trata a los padres con respeto pero sin arrastrarte
- Usa emojis ocasionalmente
- Sé breve y claro

MENÚ PRINCIPAL - Cuando el usuario escriba "hola", "menú" o algo similar, presenta las opciones:

📲 *STAR CLUB DEPORTIVO* 🛼💙
¡Hola! 👋 Soy *Boy*, tu asistente virtual ✨
Estoy aquí para ayudarte 💙
Escribe el número de la opción que necesitas 👇

1️⃣ Quiénes somos
2️⃣ Horarios y sedes
3️⃣ Copa StarX3
4️⃣ Uniformes y tienda
5️⃣ Pagos y mensualidades
6️⃣ Área de deportistas
7️⃣ Próximos eventos
8️⃣ Preguntas frecuentes
9️⃣ Redes sociales
🔟 Hablar con una persona

INFORMACIÓN DEL CLUB:
- Star Club Deportivo, fundado en 2013
- Afiliado a Liga de Patinaje de Cundinamarca y Federación Colombiana de Patinaje
- Sedes: Girardot y Melgar
- Niños desde 3 años
- Profesora: Ivonn

INSCRIPCIÓN:
- Inscripción anual: $50.000
- Sede Melgar (Escuela): $90.000/mes, 4 veces por semana
- Sede Girardot:
  • Iniciación: $90.000/mes, 3 veces por semana
  • Intermedio: $100.000/mes, 5 veces por semana
  • Avanzado: $110.000/mes, 9 jornadas por semana

HORARIOS - Cuando pregunten por horarios:
- Pregunta primero: ¿Girardot o Melgar? ¿Y qué nivel?
- Luego envía la imagen correspondiente

Si el usuario elige una opción del menú, responde con la información de esa sección.
Si el usuario se pone grosero o insiste con temas que no manejas, responde:
"Comunicaré a Ivonn para que te contacte. Escribe *10* y la llamo."
"""

_prompt_cache = {"valor": None, "ts": 0}

def _cargar_prompt():
    ahora = time.time()
    if _prompt_cache["valor"] and ahora - _prompt_cache["ts"] < 300:
        return _prompt_cache["valor"]
    try:
        from db import supabase
        if not supabase:
            return PROMPT_DEFAULT
        r = supabase.table("configuracion").select("valor").eq("id", "system_prompt").execute()
        if r.data and len(r.data) > 0:
            _prompt_cache["valor"] = r.data[0]["valor"]
            _prompt_cache["ts"] = ahora
            return _prompt_cache["valor"]
    except Exception as e:
        logger.warning(f"[PROMPT] Error cargando de Supabase: {e}")
    return PROMPT_DEFAULT

# ──────────────────────────────
# SUPABASE - MEMORIA + RESÚMENES
# ──────────────────────────────

MAX_MENSAJES = 8
UMBRAL_RESUMEN = 8

def _guardar_mensaje(numero, rol, contenido):
    try:
        from db import supabase
        if supabase:
            supabase.table("conversaciones").insert({
                "numero": numero,
                "rol": rol,
                "contenido": contenido,
            }).execute()
    except Exception as e:
        logger.warning(f"[MEMORIA] Error guardando: {e}")

def _contar_mensajes(numero):
    try:
        from db import supabase
        if not supabase:
            return 0
        r = supabase.table("conversaciones").select("id", count="exact").eq("numero", numero).execute()
        return r.count or 0
    except Exception:
        return 0

def _leer_historial(numero, limite=8):
    try:
        from db import supabase
        if not supabase:
            return []
        r = (supabase.table("conversaciones")
             .select("rol,contenido")
             .eq("numero", numero)
             .order("created_at", desc=True)
             .limit(limite)
             .execute())
        if r.data:
            return list(reversed(r.data))
    except Exception as e:
        logger.warning(f"[MEMORIA] Error leyendo: {e}")
    return []

def _leer_resumen(numero):
    try:
        from db import supabase
        if not supabase:
            return None
        r = (supabase.table("resumenes")
             .select("contenido")
             .eq("numero", numero)
             .order("created_at", desc=True)
             .limit(1)
             .execute())
        if r.data and len(r.data) > 0:
            return r.data[0]["contenido"]
    except Exception as e:
        logger.warning(f"[RESUMEN] Error leyendo: {e}")
    return None

def _crear_resumen(numero):
    try:
        from db import supabase
        if not supabase:
            return
        mensajes = _leer_historial(numero, limite=20)
        if len(mensajes) < UMBRAL_RESUMEN:
            return
        texto = "\n".join([f"{m['rol']}: {m['contenido']}" for m in mensajes])
        resp = _cliente().models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"Resume esta conversación en 2-3 oraciones. Sé conciso:\n\n{texto}",
            config=types.GenerateContentConfig(
                system_instruction="Eres un asistente que resume conversaciones. Solo d el resumen, nada más.",
                max_output_tokens=150,
                temperature=0.3,
            ),
        )
        resumen = (resp.text or "").strip()
        if resumen:
            supabase.table("resumenes").insert({
                "numero": numero,
                "contenido": resumen,
            }).execute()
            supabase.table("conversaciones").delete().eq("numero", numero).execute()
            logger.info(f"[RESUMEN] Creado para {numero}")
    except Exception as e:
        logger.warning(f"[RESUMEN] Error creando: {e}")

def _obtener_contexto(numero):
    resumen = _leer_resumen(numero)
    mensajes = _leer_historial(numero, limite=8)
    historial = []
    if resumen:
        historial.append({"rol": "system", "contenido": f"Resumen de conversación anterior: {resumen}"})
    historial.extend(mensajes)
    return historial

# ──────────────────────────────
# CHAT
# ──────────────────────────────

def gemini_chat(historial, mensaje):
    if not _cb.disponible():
        return "Estoy teniendo un problema temporal. Intenta de nuevo en unos minutos."

    prompt = _cargar_prompt()

    contents = []
    for m in historial:
        if m["rol"] == "system":
            contents.append(types.Content(role="user", parts=[types.Part(text=m["contenido"])]))
            contents.append(types.Content(role="model", parts=[types.Part(text="Entendido, tengo el contexto.")]))
        else:
            role = "user" if m["rol"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=m["contenido"])]))
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

CLASIFICAR_PROMPT = """Clasifica el mensaje del usuario en UNA de estas opciones.
Responde SOLO con el nombre exacto, nada más:

iniciacion → si menciona iniciación, motricidad, niños pequeños, 3-5 años, principiantes
intermedio → si menciona intermedio, técnica básica, 6-12 años
avanzado → si menciona avanzado, competitivo, alto rendimiento, 13+ años
melgar → si menciona Melgar como sede o ubicación
ninguno → si no habla de horarios ni niveles"""

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
        mapa = {
            "iniciacion": "StarLINE-iniciacion.jpeg",
            "intermedio": "StarLINE-intermedio.jpeg",
            "avanzado": "StarLINE-avanzado.jpeg",
            "melgar": "StarLINE-melgar.jpeg",
        }
        return mapa.get(resultado)
    except Exception as e:
        logger.error(f"[CLASIFICAR] Error: {e}")
        return None

# ──────────────────────────────
# ESTADO POR CONVERSACIÓN
# ──────────────────────────────

_estado = {}

def _guardar_estado(numero, estado):
    _estado[numero] = estado

def _leer_estado(numero):
    return _estado.pop(numero, None)

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

        logger.info(f"[WEBHOOK] De: {numero} | Msg: {texto[:50]}")

        estado = _leer_estado(numero)
        imagen = None

        if estado == "esperando_horario":
            imagen = clasificar_nivel(texto)
            if imagen:
                respuesta = "Acá te va el horario 🛼"
            else:
                respuesta = "No te entendí bien. Decime: iniciación, intermedio, avanzado o Melgar."
                _guardar_estado(numero, "esperando_horario")
        else:
            t = texto.lower()
            if any(p in t for p in ["horario", "horarios", "clase", "clases", "entreno", "entrenamiento"]):
                respuesta = "¿Qué horario te gustaría saber? 📍\n• Girardot: iniciación, intermedio o avanzado\n• Melgar"
                _guardar_estado(numero, "esperando_horario")
            else:
                historial = _obtener_contexto(numero)
                respuesta = gemini_chat(historial, texto)

        _guardar_mensaje(numero, "user", texto)
        _guardar_mensaje(numero, "model", respuesta)

        total = _contar_mensajes(numero)
        if total >= UMBRAL_RESUMEN:
            _crear_resumen(numero)

    except Exception as e:
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

    return PlainTextResponse(content=twiml, media_type="application/xml")
