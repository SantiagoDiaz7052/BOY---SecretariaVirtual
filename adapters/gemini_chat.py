import logging
from typing import Optional
from google.genai import types

from adapters.gemini_client import gemini_client
from adapters.gemini_models import GeminiResult
from adapters.gemini_payments import consultar_estado_pago, iniciar_proceso_pago
from adapters.gemini_inscription import registrar_inscripcion
from services.inscripciones import consultar_deportista

logger = logging.getLogger("boy.gemini.chat")

PROMPT_BASE = """
Eres una secretaria virtual eficiente de un club de patinaje.

REGLAS ESTRICTAS:
- Responde SIEMPRE en español
- Máximo 3 oraciones por respuesta
- Sin saludos largos ni despedidas
- Sin frases como "claro que sí", "por supuesto", "con gusto"
- Ve directo al punto
- Si necesitas datos del usuario, pide UN solo dato a vez

PROCESO DE INSCRIPCIÓN (MATRÍCULA):
Cuando el usuario quiera inscribirse, recolecta estos datos UNO POR UNO en este orden:
1. Nombre completo
2. Número de documento
3. Teléfono de contacto
4. Fecha de nacimiento (formato YYYY-MM-DD)
5. Experiencia en patinaje (pregunta abierta: "¿Ya tiene experiencia patinando?")

Si el usuario no responde claramente sobre experiencia o dice "no se",
responde: "Ok, [nombre] te evaluará y determinará en qué grupo debes estar."
y continúa con el flujo.

Cuando tengas TODOS los datos, llama a la función registrar_inscripcion.

CONSULTA DE DEPORTISTA:
Cuando el usuario quiera saber su estado o info, pide el documento y llama a consultar_deportista.

ESTADO DE PAGO:
Cuando el usuario pregunte "¿cuánto debo?", "¿qué he pagado?", "¿está al día?", 
o cualquier consulta sobre su estado financiero, pide su número de documento 
y llama a consultar_estado_pago.

PAGO DE MENSUALIDAD:
Cuando el usuario quiera pagar, enviar comprobante, o diga "quiero pagar", "pagar mensualidad",
pide su número de documento y llama a iniciar_proceso_pago. 
La función retornará las instrucciones de pago que debes enviar al usuario.
Después de enviar las instrucciones, indica que puede enviar el comprobante por imagen.
"""

# Definición de herramientas para Gemini
herramientas = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="registrar_inscripcion",
            description="Registra una preinscripción de matrícula cuando se tienen todos los datos del deportista.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "nombre": types.Schema(type=types.Type.STRING, description="Nombre completo"),
                    "documento": types.Schema(type=types.Type.STRING, description="Número de documento"),
                    "telefono": types.Schema(type=types.Type.STRING, description="Teléfono de contacto"),
                    "fecha_nacimiento": types.Schema(type=types.Type.STRING, description="Fecha YYYY-MM-DD"),
                    "experiencia_patinaje": types.Schema(type=types.Type.STRING, description="Experiencia en patinaje del usuario"),
                },
                required=["nombre", "documento", "telefono", "fecha_nacimiento"]
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
    """
    
    def __init__(self):
        self._prompt_base = PROMPT_BASE
    
    def _ejecutar_funcion(self, fn_name: str, args: dict, 
                          club_id: Optional[str]) -> Optional[str]:
        """Ejecuta una funcion llamada por Gemini."""
        if fn_name == "registrar_inscripcion" and club_id:
            resultado = registrar_inscripcion(club_id=club_id, **args)
            return resultado.get("mensaje", "Error al registrar inscripcion")
        
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
        
        # Llamar a Gemini con reintentos
        resultado = gemini_client.generate_content(
            model="gemini-2.5-flash-lite",
            contents=contents,
            config=config,
            context="chat",
            fallback_model="gemini-2.0-flash",
        )
        
        if not resultado.success:
            return resultado
        
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
            return GeminiResult.fail(
                error_type="RESPONSE_PARSE_ERROR",
                message="Error al procesar respuesta de Gemini",
                retries_used=resultado.retries_used,
            )


# Instancia global del adaptador de chat
gemini_chat = GeminiChatAdapter()
