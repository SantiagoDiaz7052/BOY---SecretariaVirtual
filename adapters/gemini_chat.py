import logging
import time
import threading
from typing import Optional
from google.genai import types

from adapters.gemini_client import gemini_client
from adapters.gemini_models import GeminiResult
from adapters.gemini_payments import consultar_estado_pago, iniciar_proceso_pago
from adapters.gemini_inscription import registrar_solicitud_ingreso
from services.inscripciones import consultar_deportista

logger = logging.getLogger("boy.gemini.chat")

# ============================================================
# CIRCUIT BREAKER - Proteccion contra fallos de Gemini
# ============================================================
class CircuitBreaker:
    """Circuit Breaker para proteger contra fallos de Gemini.
    
    Estados:
    - CLOSED: Funciona normal, permite requests
    - OPEN: Gemini esta fallando, bloquea requests
    - HALF_OPEN: Probando si Gemini se recupero
    """
    
    def __init__(self, failure_threshold: int = 3, 
                 recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"
        self._lock = threading.Lock()
    
    def record_failure(self) -> None:
        """Registra un fallo."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(
                    f"[CIRCUIT_BREAKER] Circuito ABIERTO. "
                    f"Fallos: {self.failure_count}. "
                    f"Gemini no disponible por {self.recovery_timeout}s"
                )
    
    def record_success(self) -> None:
        """Registra un exito."""
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"
    
    def is_available(self) -> bool:
        """Verifica si esta disponible para requests."""
        with self._lock:
            if self.state == "CLOSED":
                return True
            
            if self.state == "OPEN":
                # Verificar si ya paso el tiempo de recuperacion
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    logger.info("[CIRCUIT_BREAKER] Circuito HALF_OPEN - Probando Gemini")
                    return True
                return False
            
            if self.state == "HALF_OPEN":
                return True
            
            return False

# Instancia global del circuit breaker
_circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=120)


def gemini_fallback_response() -> str:
    """Retorna una respuesta fallback cuando Gemini esta caido."""
    return (
        "Estoy teniendo un problema temporal con el servicio. "
        "Por favor, intenta de nuevo en unos minutos. "
        "Si el problema persiste, escribe *10* para hablar con Ivonn."
    )


PROMPT_BASE = """
Eres una secretaria virtual eficiente de un club de patinaje.

REGLAS ESTRICTAS (incumplirlas causa error grave):
- Responde SIEMPRE en español
- Máximo 2 oraciones por respuesta
- Prohibido: saludos, despedidas, "claro que sí", "con gusto", "por supuesto"
- Ve directo al punto
- Pide UN SOLO DATO a la vez

INSCRIPCIÓN:
Cuando el usuario quiera inscribirse:
1. Preséntate como la secretaria virtual del CLUB DE PATINAJE STAR LINE
2. Indica los horarios: lunes a viernes 4pm-7pm, sábados 9am-12pm
3. Pregunta si desea continuar con los datos de matrícula
Si dice que sí, recolecta UN DATO POR MENSAJE en este orden:
1. "¿Cuál es el nombre completo del aspirante?"
2. "¿Cuál es su número de documento?"
3. "¿Cuál es su teléfono de contacto?"
4. "¿Cuál es su fecha de nacimiento? (YYYY-MM-DD)"
5. "¿Tiene experiencia en patinaje?" — si dice sí→"si", no→"no", no sabe→"no_sabe"
6. Si menor de edad: "¿Nombre del responsable?" y "¿WhatsApp del responsable?"

LLAMA registrar_solicitud_ingreso SOLO cuando tengas: nombre, documento, teléfono, fecha_nacimiento Y experiencia_reportada.

CONSULTA: "Dime tu documento" → consultar_deportista
ESTADO PAGO: "Dime tu documento" → consultar_estado_pago
PAGAR: "Dime tu documento" → iniciar_proceso_pago (retorna instrucciones)
"""

# Definición de herramientas para Gemini
herramientas = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="registrar_solicitud_ingreso",
            description="Registra una solicitud de ingreso cuando se tienen TODOS los datos del aspirante. No asigna nivel ni genera pagos.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "nombre": types.Schema(type=types.Type.STRING, description="Nombre completo del aspirante"),
                    "documento": types.Schema(type=types.Type.STRING, description="Número de documento del aspirante"),
                    "telefono": types.Schema(type=types.Type.STRING, description="Teléfono de contacto del aspirante"),
                    "fecha_nacimiento": types.Schema(type=types.Type.STRING, description="Fecha de nacimiento en formato YYYY-MM-DD"),
                    "experiencia_reportada": types.Schema(type=types.Type.STRING, description="Experiencia en patinaje: 'si', 'no', o 'no_sabe'"),
                    "responsable_nombre": types.Schema(type=types.Type.STRING, description="Nombre del responsable (si es menor de edad)"),
                    "responsable_whatsapp": types.Schema(type=types.Type.STRING, description="WhatsApp del responsable (si es menor de edad)"),
                },
                required=["nombre", "documento", "telefono", "fecha_nacimiento", "experiencia_reportada"]
            )
        ),
        types.FunctionDeclaration(
            name="consultar_deportista",
            description="Consulta la información de un deportista por su documento.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "documento": types.Schema(type=types.Type.STRING, description="Número de documento"),
                },
                required=["documento"]
            )
        ),
        types.FunctionDeclaration(
            name="consultar_estado_pago",
            description="Consulta el estado financiero de un deportista: cuánto debe, qué ha pagado, saldo pendiente.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "documento": types.Schema(type=types.Type.STRING, description="Número de documento del deportista"),
                },
                required=["documento"]
            )
        ),
        types.FunctionDeclaration(
            name="iniciar_proceso_pago",
            description="Inicia un proceso de pago para un deportista. Retorna instrucciones de pago y la obligación a pagar.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "documento": types.Schema(type=types.Type.STRING, description="Número de documento del deportista"),
                },
                required=["documento"]
            )
        )
    ])
]


class GeminiChatAdapter:
    """Adaptador para chat conversacional con Gemini.
    
    Aislamiento del dominio:
    - Recibe historial y mensaje
    - Retorna respuesta de texto o indica funcion a llamar
    - Nunca lanza excepciones
    - Circuit breaker para proteccion contra fallos
    """
    
    def __init__(self):
        self._prompt_base = PROMPT_BASE
    
    def _ejecutar_funcion(self, fn_name: str, args: dict, 
                          club_id: Optional[str]) -> Optional[str]:
        """Ejecuta una funcion llamada por Gemini."""
        if fn_name == "registrar_solicitud_ingreso" and club_id:
            resultado = registrar_solicitud_ingreso(club_id=club_id, **args)
            return resultado.get("mensaje", "Error al registrar solicitud de ingreso")
        
        elif fn_name == "consultar_deportista" and club_id:
            resultado = consultar_deportista(club_id=club_id, **args)
            if resultado.get("encontrado"):
                return (
                    f"Deportista: {resultado['nombre']}\n"
                    f"Nivel: {resultado['nivel']}\n"
                    f"Estado: {resultado['estado']}"
                )
            return resultado.get("mensaje", "Deportista no encontrado")
        
        elif fn_name == "consultar_estado_pago" and club_id:
            resultado = consultar_estado_pago(club_id=club_id, **args)
            return resultado.get("mensaje", "No se pudo consultar el estado")
        
        elif fn_name == "iniciar_proceso_pago" and club_id:
            resultado = iniciar_proceso_pago(club_id=club_id, **args)
            return resultado.get("mensaje", "No se pudo iniciar el proceso de pago")
        
        return None
    
    def get_respuesta(self, system_prompt: str, historial: list, 
                      mensaje_nuevo: str, 
                      club_id: Optional[str] = None) -> GeminiResult:
        """Obtiene respuesta de Gemini para un mensaje.
        
        Args:
            system_prompt: Prompt del club
            historial: Lista de mensajes anteriores
            mensaje_nuevo: Mensaje del usuario
            club_id: ID del club (para ejecutar funciones)
        
        Returns:
            GeminiResult con la respuesta de texto
        """
        # Verificar circuit breaker
        if not _circuit_breaker.is_available():
            logger.warning("[CHAT] Circuit breaker OPEN - Usando fallback")
            return GeminiResult.ok(
                data=gemini_fallback_response(),
                retries_used=0,
            )
        
        # Construir contenido
        contents = []
        for m in historial:
            role = "user" if m["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=m["content"])]
            ))
        
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=mensaje_nuevo)]
        ))
        
        # Configurar
        config = types.GenerateContentConfig(
            system_instruction=self._prompt_base + "\n\n" + system_prompt,
            max_output_tokens=300,
            temperature=0.5,
            tools=herramientas,
        )
        
        # Llamar a Gemini con reintentos y cadena de fallback
        resultado = gemini_client.generate_content(
            model="gemini-2.5-flash-lite",
            contents=contents,
            config=config,
            context="chat",
        )
        
        # Actualizar circuit breaker segun resultado
        if resultado.success:
            _circuit_breaker.record_success()
        else:
            _circuit_breaker.record_failure()
            # Retornar respuesta fallback en lugar de error
            return GeminiResult.ok(
                data=gemini_fallback_response(),
                retries_used=resultado.retries_used,
            )
        
        # Verificar si Gemini quiere llamar una funcion
        try:
            response = resultado.data
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fn = part.function_call
                    args = dict(fn.args)
                    
                    respuesta_funcion = self._ejecutar_funcion(
                        fn.name, args, club_id
                    )
                    if respuesta_funcion:
                        return GeminiResult.ok(
                            data=respuesta_funcion,
                            retries_used=resultado.retries_used,
                        )
            
            # Si no hay funcion, retornar texto
            return GeminiResult.ok(
                data=response.text,
                raw_response=response.text,
                retries_used=resultado.retries_used,
            )
            
        except (IndexError, AttributeError) as e:
            logger.error(f"[CHAT] Error procesando respuesta: {e}")
            return GeminiResult.ok(
                data=gemini_fallback_response(),
                retries_used=resultado.retries_used,
            )


# Instancia global del adaptador de chat
gemini_chat = GeminiChatAdapter()
