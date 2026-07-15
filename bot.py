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
# ESTADO POR CONVERSACIÓN
# ──────────────────────────────

_conversaciones = {}

def _guardar_estado(numero, estado):
    _conversaciones[numero] = estado

def _leer_estado(numero):
    return _conversaciones.pop(numero, None)

# ──────────────────────────────
# GEMINI
# ──────────────────────────────

def _cliente():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no configurada")
    return genai.Client(api_key=api_key)


def gemini_generar(contents, config, intento=0):
    max_intentos = 3
    modelos = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
    for i in range(max_intentos):
        modelo = modelos[0] if i == 0 else modelos[-1]
        try:
            resp = _cliente().models.generate_content(model=modelo, contents=contents, config=config)
            if resp.candidates:
                return {"ok": True, "data": resp}
        except ServerError as e:
            err = str(e)
            if "503" in err or "UNAVAILABLE" in err:
                if "gemini-2.5-flash" not in modelo:
                    logger.warning(f"[GEMINI] 503 en {modelo}, probando fallback")
                    continue
            if i < max_intentos - 1:
                time.sleep(min(2 * (2 ** i), 10))
                continue
            return {"ok": False, "error": err}
        except Exception as e:
            if i < max_intentos - 1:
                time.sleep(2)
                continue
            return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "max_intentos"}


PROMPT = """
Eres BOY, la secretaria virtual del CLUB DE PATINAJE STAR LINE.

PERSONALIDAD:
- Responde siempre en español, con energía y actitud
- Sin rodeos, ve al grano
- Trata a los padres con respeto pero sin arrastrarte
- Usa emojis ocasionalmente
- Máximo 3 oraciones por respuesta

INFORMACIÓN DEL CLUB:
- Ubicaciones: Girardot y Melgar
- Edades: desde 3 años hasta adultos
- Profesora: Ivonn

INSCRIPCIÓN:
Si el usuario quiere inscribirse:
1. Pregunta la edad del niño
2. Según la edad, explica el grupo correspondiente:
   - 3-5 años → iniciación (motricidad, juegos)
   - 6-12 años → intermedio (técnica básica, pruebas)
   - 13+ años → avanzado (competitivo, alto rendimiento)
3. Pregunta si quiere más información o si tiene alguna duda
NO registres nada en el sistema. Solo informa.

Si el usuario se pone grosero o insiste con temas que no manejas, responde:
"Comunicaré a Ivonn para que te contacte. Escribe *10* y la llamo."
"""


def gemini_chat(historial, mensaje):
    if not _cb.disponible():
        return "Estoy teniendo un problema temporal. Intenta de nuevo en unos minutos."

    contents = []
    for m in historial:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=mensaje)]))

    config = types.GenerateContentConfig(
        system_instruction=PROMPT,
        max_output_tokens=300,
        temperature=0.7,
    )

    r = gemini_generar(contents, config)
    if not r["ok"]:
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
                respuesta = gemini_chat([], texto)

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
