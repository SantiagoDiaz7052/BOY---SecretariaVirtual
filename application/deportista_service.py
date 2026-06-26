from typing import Optional, List
from domain.deportista import Deportista, EstadoDeportista, NivelDeportista
from repositories.deportista_repo import DeportistaRepository


class DeportistaService:
    """Servicio de aplicacion para deportistas.
    
    Coordina el lifecycle del deportista.
    
    REGLAS:
    - Un deportista INACTIVO no puede entrenar
    - El nivel se asigna en matricula, admin puede modificar
    - Preparado para padres con varios hijos (responsable)
    - Se asocia a una temporada
    """

    def __init__(self):
        self.repo = DeportistaRepository()

    def obtener_por_id(self, deportista_id: str) -> Optional[Deportista]:
        return self.repo.obtener_por_id(deportista_id)

    def buscar_por_documento(self, club_id: str, 
                             documento: str) -> Optional[Deportista]:
        return self.repo.buscar_por_documento(club_id, documento)

    def listar_por_club(self, club_id: str, 
                        estado: Optional[str] = None,
                        temporada_id: Optional[str] = None) -> List[Deportista]:
        return self.repo.listar_por_club(club_id, estado, temporada_id)

    def listar_por_whatsapp(self, club_id: str, 
                            numero_whatsapp: str) -> List[Deportista]:
        """Busca deportistas por numero de WhatsApp (del responsable)."""
        return self.repo.listar_por_whatsapp(club_id, numero_whatsapp)

    def crear_deportista(self, club_id: str, temporada_id: str,
                         nombre: str, documento: str,
                         nivel: str = "iniciacion",
                         telefono: Optional[str] = None,
                         fecha_nacimiento: Optional[str] = None,
                         responsable_nombre: Optional[str] = None,
                         responsable_documento: Optional[str] = None,
                         responsable_whatsapp: Optional[str] = None) -> dict:
        """Crea un deportista nuevo (despues de matricula aprobada).
        
        REGLAS:
        - Se crea con estado INACTIVO
        - No se activa automaticamente
        - La activacion depende del pago de mensualidad
        """
        # Verificar duplicado
        existente = self.repo.buscar_por_documento(club_id, documento)
        if existente:
            return {
                "exito": False,
                "mensaje": "Ya existe un deportista con ese documento.",
            }

        datos = {
            "club_id": club_id,
            "temporada_id": temporada_id,
            "nombre": nombre,
            "documento": documento,
            "nivel": nivel,
            "estado": EstadoDeportista.INACTIVO.value,
            "telefono": telefono,
            "fecha_nacimiento": fecha_nacimiento,
            "responsable_nombre": responsable_nombre,
            "responsable_documento": responsable_documento,
            "responsable_whatsapp": responsable_whatsapp,
        }

        deportista = self.repo.crear(datos)
        return {
            "exito": True,
            "deportista_id": deportista.id,
            "mensaje": f"{nombre} registrado correctamente. Estado: INACTIVO.",
        }

    def activar(self, deportista_id: str) -> dict:
        """Activa un deportista (despues de pago de mensualidad)."""
        deportista = self.repo.obtener_por_id(deportista_id)
        if not deportista:
            return {"exito": False, "mensaje": "Deportista no encontrado."}

        if deportista.esta_activo:
            return {"exito": True, "mensaje": "El deportista ya esta activo."}

        self.repo.activar(deportista_id)
        return {
            "exito": True,
            "mensaje": f"{deportista.nombre} activado correctamente.",
        }

    def desactivar(self, deportista_id: str) -> dict:
        """Desactiva un deportista."""
        deportista = self.repo.obtener_por_id(deportista_id)
        if not deportista:
            return {"exito": False, "mensaje": "Deportista no encontrado."}

        self.repo.desactivar(deportista_id)
        return {
            "exito": True,
            "mensaje": f"{deportista.nombre} desactivado.",
        }

    def reiniciar_mensual(self, club_id: str, temporada_id: str) -> int:
        """Desactiva todos los deportistas al inicio del mes."""
        return self.repo.desactivar_todos(club_id, temporada_id)

    def actualizar_nivel(self, deportista_id: str, 
                         nuevo_nivel: str) -> dict:
        """Actualiza el nivel de un deportista (solo admin)."""
        if nuevo_nivel not in [e.value for e in NivelDeportista]:
            return {"exito": False, "mensaje": "Nivel no valido."}

        deportista = self.repo.obtener_por_id(deportista_id)
        if not deportista:
            return {"exito": False, "mensaje": "Deportista no encontrado."}

        self.repo.actualizar(deportista_id, {"nivel": nuevo_nivel})
        return {
            "exito": True,
            "mensaje": f"Nivel actualizado a {nuevo_nivel}.",
        }
