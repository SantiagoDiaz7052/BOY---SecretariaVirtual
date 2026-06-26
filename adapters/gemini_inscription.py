import re
import logging
from typing import Optional

logger = logging.getLogger("boy.gemini.inscription")


def extraer_nombre_profesor(system_prompt: str) -> str:
    """Extrae el nombre del profesor/secretaria del system_prompt.
    
    Ejemplos de system_prompt:
    - "Eres Ivonn, secretaria virtual del club..."
    - "Tu nombre es Maria y eres la asistente..."
    """
    patrones = [
        r"[Ee]res\s+(\w+)",
        r"[Tt]u nombre es\s+(\w+)",
        r"[Ss]oy\s+(\w+)",
    ]
    for patron in patrones:
        match = re.search(patron, system_prompt)
        if match:
            return match.group(1)
    return "la profesora"


def mapear_experiencia_a_nivel(respuesta_usuario: str) -> str:
    """Mapea respuesta libre del usuario a nivel inicial.
    
    Niveles:
    - INICIACION: no tiene experiencia
    - INTERMEDIO: algo de experiencia
    - AVANZADO: experiencia competitiva
    """
    if not respuesta_usuario or respuesta_usuario.strip() == "":
        return "iniciacion"

    respuesta = respuesta_usuario.lower()

    patron_ninguna = [
        "no", "ninguna", "nunca", "nuevo", "principiante",
        "no tengo", "no se", "desconozco", "primera vez"
    ]
    patron_algo = [
        "algo", "poco", "intermedio", "he patinado", "un poco",
        "regular", "basico", "basica", "algunas veces"
    ]
    patron_avanzado = [
        "competitivo", "avanzado", "profesional", "he competido",
        "experiencia", "experto", "desde hace", "varios anios"
    ]

    for p in patron_ninguna:
        if p in respuesta:
            return "iniciacion"
    for p in patron_algo:
        if p in respuesta:
            return "intermedio"
    for p in patron_avanzado:
        if p in respuesta:
            return "avanzado"

    return "iniciacion"


def construir_mensaje_default(nombre_profesor: str) -> str:
    """Construye el mensaje cuando el usuario no responde experiencia."""
    return f"Ok, {nombre_profesor} te evaluara y determinara en que grupo debes estar."


def registrar_inscripcion(club_id: str, nombre: str, documento: str,
                          telefono: str, fecha_nacimiento: str,
                          experiencia_patinaje: str = "",
                          system_prompt: str = "") -> dict:
    """Funcion que Gemini llama via function calling.
    
    FLUJO:
    1. Mapea experiencia → nivel
    2. Crea Preinscripcion
    3. Crea Obligacion de matricula
    4. Inicia ProcesoPago
    5. Retorna instrucciones de pago
    """
    try:
        from application.preinscripcion_service import PreinscripcionService
        from application.temporada_service import TemporadaService

        preinscripcion_service = PreinscripcionService()
        temporada_service = TemporadaService()

        # 1. Obtener temporada activa
        temporada = temporada_service.obtener_activa(club_id)
        if not temporada:
            return {
                "exito": False,
                "mensaje": "No hay temporada activa. Contacta al administrador.",
            }

        # 2. Mapear experiencia a nivel
        nivel = mapear_experiencia_a_nivel(experiencia_patinaje)

        # 3. Crear preinscripcion
        resultado = preinscripcion_service.crear_preinscripcion(
            club_id=club_id,
            temporada_id=temporada.id,
            datos={
                "nombre": nombre,
                "documento": documento,
                "telefono": telefono,
                "fecha_nacimiento": fecha_nacimiento,
                "nivel": nivel,
            }
        )

        if not resultado["exito"]:
            return resultado

        # 4. Construir mensaje con instrucciones
        nombre_profesor = extraer_nombre_profesor(system_prompt)

        if not experiencia_patinaje or experiencia_patinaje.strip() == "":
            mensaje_default = construir_mensaje_default(nombre_profesor)
            mensaje = (
                f"{mensaje_default}\n\n"
                f"Nivel asignado: {nivel}\n\n"
                f"Para completar la inscripcion, realiza el pago de matricula:\n"
                f"Monto: ${resultado['monto']:,.0f} COP\n\n"
                f"Una vez realices el pago, envia el comprobante por imagen."
            )
        else:
            mensaje = (
                f"{nombre} sera categoria {nivel}.\n\n"
                f"Para completar la inscripcion, realiza el pago de matricula:\n"
                f"Monto: ${resultado['monto']:,.0f} COP\n\n"
                f"Una vez realices el pago, envia el comprobante por imagen."
            )

        return {
            "exito": True,
            "mensaje": mensaje,
            "preinscripcion_id": resultado["preinscripcion_id"],
            "proceso_id": resultado["proceso_id"],
            "monto": resultado["monto"],
            "nivel": nivel,
        }

    except Exception as e:
        logger.error(f"[INSCRIPTION] Error: {e}", exc_info=True)
        return {
            "exito": False,
            "mensaje": "Hubo un error al procesar la inscripcion. Intenta de nuevo.",
        }
