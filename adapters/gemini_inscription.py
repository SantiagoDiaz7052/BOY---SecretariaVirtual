import re
import logging
from typing import Optional

logger = logging.getLogger("boy.gemini.inscription")


def extraer_nombre_profesor(system_prompt: str) -> str:
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


def registrar_solicitud_ingreso(club_id: str, nombre: str, documento: str,
                                 telefono: str, fecha_nacimiento: str,
                                 experiencia_reportada: str = "",
                                 system_prompt: str = "",
                                 responsable_nombre: str = "",
                                 responsable_documento: str = "",
                                 responsable_whatsapp: str = "") -> dict:
    """Funcion que Gemini llama via function calling.

    FLUJO:
    1. Obtiene temporada activa
    2. Crea SolicitudIngreso (sin asignar nivel, sin crear pagos)
    3. Retorna mensaje: "seras evaluado por [profesor]"
    """
    try:
        from application.solicitud_ingreso_service import SolicitudIngresoService
        from application.temporada_service import TemporadaService
        from application.tarea_service import TareaService

        solicitud_service = SolicitudIngresoService()
        temporada_service = TemporadaService()
        tarea_service = TareaService()

        # 1. Obtener temporada activa
        temporada = temporada_service.obtener_activa(club_id)
        if not temporada:
            return {
                "exito": False,
                "mensaje": "No hay temporada activa. Contacta al administrador.",
            }

        # 2. Validar experiencia reportada (solo valores aceptados)
        exp = experiencia_reportada.strip().lower() if experiencia_reportada else ""
        exp_valores = {"si", "no", "no sé", "no_se", "no_sabe", "no se", "no sabe"}
        exp_limpia = None
        if exp in exp_valores:
            if exp in ("si",):
                exp_limpia = "si"
            elif exp in ("no",):
                exp_limpia = "no"
            else:
                exp_limpia = "no_sabe"

        # 3. Crear solicitud (sin nivel, sin pagos)
        solicitud = solicitud_service.iniciar_solicitud(
            club_id=club_id,
            temporada_id=temporada.id,
            datos={
                "nombre": nombre.strip(),
                "documento": documento.strip(),
                "telefono": telefono.strip(),
                "fecha_nacimiento": fecha_nacimiento,
                "experiencia_reportada": exp_limpia,
                "responsable_nombre": responsable_nombre.strip() if responsable_nombre else None,
                "responsable_documento": responsable_documento.strip() if responsable_documento else None,
                "responsable_whatsapp": responsable_whatsapp.strip() if responsable_whatsapp else None,
            }
        )

        # 4. Crear tarea de evaluacion para la secretaria
        nombre_profesor = extraer_nombre_profesor(system_prompt)
        tarea_service.crear_tarea_evaluacion(
            solicitud_id=solicitud.id,
            club_id=club_id,
            nombre=solicitud.nombre,
        )

        # 5. Construir mensaje
        mensaje = (
            f"¡Gracias {nombre}! Tu solicitud de ingreso ha sido registrada.\n\n"
            f"{nombre_profesor} te evaluará y te asignará el grupo correspondiente. "
            f"Te notificaremos cuando estés listo para continuar con la matrícula."
        )

        return {
            "exito": True,
            "mensaje": mensaje,
            "solicitud_id": solicitud.id,
        }

    except ValueError as e:
        logger.warning(f"[SOLICITUD] Validacion: {e}")
        return {"exito": False, "mensaje": str(e)}
    except Exception as e:
        logger.error(f"[SOLICITUD] Error: {e}", exc_info=True)
        return {
            "exito": False,
            "mensaje": "Hubo un error al procesar la solicitud. Intenta de nuevo.",
        }
