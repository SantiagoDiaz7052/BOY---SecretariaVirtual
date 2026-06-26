from typing import Optional, List
from domain.concepto import Concepto
from repositories.concepto_repo import ConceptoRepository


class ConceptoService:
    """Servicio de aplicacion para conceptos.
    
    Coordina las operaciones de conceptos sin exponer detalles de persistencia.
    """

    def __init__(self):
        self.repo = ConceptoRepository()

    def obtener_por_id(self, concepto_id: str) -> Optional[Concepto]:
        return self.repo.obtener_por_id(concepto_id)

    def listar_por_club(self, club_id: str, solo_activos: bool = True) -> List[Concepto]:
        return self.repo.listar_por_club(club_id, solo_activos)

    def buscar_por_nombre(self, club_id: str, nombre: str) -> Optional[Concepto]:
        return self.repo.buscar_por_nombre(club_id, nombre)

    def crear(self, club_id: str, nombre: str, monto_default: float = 0,
              es_recurrente: bool = False, genera_automaticamente: bool = False,
              aplica_mora: bool = False, requiere_periodo: bool = False,
              recargo_fijo: Optional[float] = None, 
              dias_limite_pago: Optional[int] = None) -> Concepto:
        """Crea un nuevo concepto para un club."""
        datos = {
            "club_id": club_id,
            "nombre": nombre,
            "monto_default": monto_default,
            "es_recurrente": es_recurrente,
            "genera_automaticamente": genera_automaticamente,
            "aplica_mora": aplica_mora,
            "requiere_periodo": requiere_periodo,
            "recargo_fijo": recargo_fijo,
            "dias_limite_pago": dias_limite_pago,
        }
        return self.repo.crear(datos)

    def actualizar(self, concepto_id: str, **kwargs) -> Concepto:
        """Actualiza un concepto.
        
        IMPORTANTE: Esto no afecta obligaciones existentes.
        Las obligaciones copian el precio al momento de crearse.
        """
        return self.repo.actualizar(concepto_id, kwargs)

    def desactivar(self, concepto_id: str) -> bool:
        return self.repo.desactivar(concepto_id)

    def obtener_conceptos_iniciales(self) -> List[dict]:
        """Retorna la definicion de conceptos iniciales para un club nuevo.
        
        Estos conceptos se crean cuando un club se registra en el sistema.
        """
        return [
            {
                "nombre": "Mensualidad",
                "es_recurrente": True,
                "genera_automaticamente": True,
                "aplica_mora": True,
                "requiere_periodo": True,
                "monto_default": 0,
            },
            {
                "nombre": "Inscripcion",
                "es_recurrente": False,
                "genera_automaticamente": False,
                "aplica_mora": False,
                "requiere_periodo": False,
                "monto_default": 50000,
            },
            {
                "nombre": "Licra",
                "es_recurrente": False,
                "genera_automaticamente": False,
                "aplica_mora": False,
                "requiere_periodo": False,
                "monto_default": 0,
            },
            {
                "nombre": "Uniforme",
                "es_recurrente": False,
                "genera_automaticamente": False,
                "aplica_mora": False,
                "requiere_periodo": False,
                "monto_default": 0,
            },
            {
                "nombre": "Evento",
                "es_recurrente": False,
                "genera_automaticamente": False,
                "aplica_mora": False,
                "requiere_periodo": False,
                "monto_default": 0,
            },
        ]

    def crear_conceptos_iniciales(self, club_id: str) -> List[Concepto]:
        """Crea los conceptos iniciales para un club nuevo."""
        conceptos = []
        for def_concepto in self.obtener_conceptos_iniciales():
            concepto = self.crear(club_id=club_id, **def_concepto)
            conceptos.append(concepto)
        return conceptos
