import logging
from typing import Optional
from domain.preinscripcion import Preinscripcion, EstadoPreinscripcion
from domain.deportista import EstadoDeportista
from repositories.preinscripcion_repo import PreinscripcionRepository
from application.obligacion_service import ObligacionService
from application.proceso_pago_service import ProcesoPagoService
from application.config_service import ConfiguracionClubService
from application.deportista_service import DeportistaService
from repositories.concepto_repo import ConceptoRepository

logger = logging.getLogger("boy.preinscripcion")


class PreinscripcionService:
    """Servicio de aplicacion para preinscripciones (matricula).
    
    Coordina el flujo de matricula de un deportista nuevo.
    
    FLUJO:
    1. Crear Preinscripcion (pendiente_pago)
    2. Crear Obligacion de matricula
    3. Iniciar ProcesoPago
    4. Enviar instrucciones de pago
    5. Esperar comprobante
    6. Comprobante aprobado → CONFIRMADA
    7. Crear Deportista (INACTIVO)
    8. Crear Obligacion mensual
    9. Enviar instrucciones de activacion
    
    REGLAS:
    - No existe Deportista hasta que Preinscripcion sea CONFIRMADA
    - ProcesoPago se vincula a Preinscripcion, no a Deportista
    - El nivel se asigna en este proceso
    """

    def __init__(self):
        self.repo = PreinscripcionRepository()
        self.obligacion_service = ObligacionService()
        self.proceso_service = ProcesoPagoService()
        self.config_service = ConfiguracionClubService()
        self.deportista_service = DeportistaService()
        self.concepto_repo = ConceptoRepository()

    def crear_preinscripcion(self, club_id: str, 
                             temporada_id: str,
                             datos: dict) -> dict:
        """Crea preinscripcion + obligacion de matricula + proceso de pago.
        
        Args:
            club_id: ID del club
            temporada_id: ID de la temporada activa
            datos: Dict con nombre, documento, telefono, fecha_nacimiento,
                   nivel, responsable_nombre, responsable_documento,
                   responsable_whatsapp
        
        Returns:
            dict con exito, preinscripcion_id, proceso_id, monto
        """
        # 1. Verificar si ya existe preinscripcion pendiente
        existente = self.repo.obtener_pendiente(club_id, datos["documento"])
        if existente:
            return {
                "exito": False,
                "mensaje": "Ya tienes una inscripcion pendiente de pago.",
                "preinscripcion_id": existente.id,
            }

        # 2. Buscar concepto Matricula
        concepto = self.concepto_repo.buscar_por_nombre(club_id, "Matrícula")
        if not concepto or not concepto.activo:
            # Fallback: buscar "Inscripcion"
            concepto = self.concepto_repo.buscar_por_nombre(club_id, "Inscripción")
        if not concepto or not concepto.activo:
            return {
                "exito": False,
                "mensaje": "El concepto de matricula no esta configurado.",
            }

        # 3. Obtener monto configurable del club
        config = self.config_service.obtener_por_club(club_id)
        monto_matricula = config.monto_inscripcion if config else 50000

        # 4. Crear preinscripcion
        preinscripcion_data = {
            "club_id": club_id,
            "temporada_id": temporada_id,
            "nombre": datos["nombre"],
            "documento": datos["documento"],
            "nivel": datos.get("nivel", "iniciacion"),
            "estado": EstadoPreinscripcion.PENDIENTE_PAGO.value,
            "telefono": datos.get("telefono"),
            "fecha_nacimiento": datos.get("fecha_nacimiento"),
            "responsable_nombre": datos.get("responsable_nombre"),
            "responsable_documento": datos.get("responsable_documento"),
            "responsable_whatsapp": datos.get("responsable_whatsapp"),
        }
        preinscripcion = self.repo.crear(preinscripcion_data)

        # 5. Crear obligacion de matricula
        obligacion = self.obligacion_service.crear_obligacion(
            club_id=club_id,
            deportista_id="PENDIENTE",
            concepto_id=concepto.id,
            monto=monto_matricula,
            origen="MANUAL",
            periodo=None,
            referencia=f"Matricula {datos['nombre']}",
            nota=f"Preinscripcion {preinscripcion.id}",
            temporada_id=temporada_id,
            preinscripcion_id=preinscripcion.id,
        )

        # 6. Actualizar preinscripcion con obligacion
        self.repo.actualizar(preinscripcion.id, {
            "obligacion_id": obligacion["id"],
        })

        # 7. Iniciar proceso de pago
        proceso = self.proceso_service.iniciar_proceso(
            club_id=club_id,
            temporada_id=temporada_id,
            deportista_id=None,
            preinscripcion_id=preinscripcion.id,
            obligacion_id=obligacion["id"],
        )

        # 8. Actualizar preinscripcion con proceso
        self.repo.actualizar(preinscripcion.id, {
            "proceso_pago_id": proceso["id"],
        })

        return {
            "exito": True,
            "preinscripcion_id": preinscripcion.id,
            "obligacion_id": obligacion["id"],
            "proceso_id": proceso["id"],
            "monto": monto_matricula,
            "nivel": datos.get("nivel", "iniciacion"),
            "mensaje": f"Preinscripcion creada. Monto: ${monto_matricula:,.0f}",
        }

    def confirmar_pago(self, preinscripcion_id: str, 
                       pago_id: str) -> dict:
        """Confirma el pago y crea el deportista definitivo.
        
        FLUJO:
        1. Preinscripcion → CONFIRMADA
        2. Crear Deportista (INACTIVO)
        3. Asociar a temporada activa
        4. Asignar nivel
        5. Crear Obligacion mensual (pendiente)
        6. Finalizar ProcesoPago matricula
        7. NO activar deportista
        """
        preinscripcion = self.repo.obtener_por_id(preinscripcion_id)
        if not preinscripcion:
            return {"exito": False, "mensaje": "Preinscripcion no encontrada."}

        # 1. Actualizar estado
        self.repo.actualizar(preinscripcion_id, {
            "estado": EstadoPreinscripcion.CONFIRMADA.value,
        })

        # 2. Crear deportista
        resultado_deportista = self.deportista_service.crear_deportista(
            club_id=preinscripcion.club_id,
            temporada_id=preinscripcion.temporada_id,
            nombre=preinscripcion.nombre,
            documento=preinscripcion.documento,
            nivel=preinscripcion.nivel,
            telefono=preinscripcion.telefono,
            fecha_nacimiento=preinscripcion.fecha_nacimiento,
            responsable_nombre=preinscripcion.responsable_nombre,
            responsable_documento=preinscripcion.responsable_documento,
            responsable_whatsapp=preinscripcion.responsable_whatsapp,
        )

        if not resultado_deportista["exito"]:
            return resultado_deportista

        deportista_id = resultado_deportista["deportista_id"]

        # 3. Crear obligacion mensual pendiente
        concepto_mensual = self.concepto_repo.buscar_por_nombre(
            preinscripcion.club_id, "Mensualidad"
        )
        if concepto_mensual and concepto_mensual.activo:
            self.obligacion_service.crear_obligacion(
                club_id=preinscripcion.club_id,
                deportista_id=deportista_id,
                concepto_id=concepto_mensual.id,
                monto=concepto_mensual.monto_default,
                origen="AUTOMATICO",
                periodo=None,
                referencia=f"Mensualidad inicial {preinscripcion.nombre}",
                temporada_id=preinscripcion.temporada_id,
            )

        # 4. Finalizar proceso de pago
        if preinscripcion.proceso_pago_id:
            self.proceso_service.finalizar_proceso(
                preinscripcion.proceso_pago_id
            )

        return {
            "exito": True,
            "deportista_id": deportista_id,
            "mensaje": (
                f"{preinscripcion.nombre} inscrito correctamente. "
                f"Estado: INACTIVO. Debe activar pagando la mensualidad."
            ),
        }

    def obtener_por_id(self, preinscripcion_id: str) -> Optional[dict]:
        preinscripcion = self.repo.obtener_por_id(preinscripcion_id)
        if not preinscripcion:
            return None
        return preinscripcion.to_dict()
