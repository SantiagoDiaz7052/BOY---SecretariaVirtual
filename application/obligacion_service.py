from typing import Optional, List
from datetime import date, timedelta
from domain.obligacion import Obligacion, OrigenObligacion
from domain.concepto import Concepto
from repositories.obligacion_repo import ObligacionRepository
from repositories.concepto_repo import ConceptoRepository
from repositories.config_repo import ConfiguracionClubRepository


class ObligacionService:
    """Servicio de aplicacion para obligaciones.
    
    Coordina la creacion y consulta de obligaciones.
    El saldo se calcula, nunca se almacena.
    """

    def __init__(self):
        self.repo = ObligacionRepository()
        self.concepto_repo = ConceptoRepository()
        self.config_repo = ConfiguracionClubRepository()

    def obtener_por_id(self, obligacion_id: str) -> Optional[dict]:
        """Obtiene una obligacion con su estado calculado."""
        obligacion = self.repo.obtener_por_id(obligacion_id)
        if not obligacion:
            return None
        
        monto_pagado = self.repo.calcular_monto_pagado(obligacion)
        obligacion.calcular_estado(monto_pagado)
        return obligacion.to_dict()

    def listar_por_deportista(self, club_id: str, deportista_id: str,
                              solo_pendientes: bool = False) -> List[dict]:
        """Lista obligaciones de un deportista con estado calculado."""
        obligaciones = self.repo.listar_por_deportista(club_id, deportista_id)
        
        resultado = []
        for obligacion in obligaciones:
            monto_pagado = self.repo.calcular_monto_pagado(obligacion)
            obligacion.calcular_estado(monto_pagado)
            
            if solo_pendientes and obligacion.esta_cancelada:
                continue
            
            resultado.append(obligacion.to_dict())
        
        return resultado

    def crear_obligacion(self, club_id: str, deportista_id: str, 
                         concepto_id: str, monto: float,
                         origen: OrigenObligacion = OrigenObligacion.MANUAL,
                         fecha_limite: Optional[date] = None,
                         periodo: Optional[str] = None,
                         referencia: Optional[str] = None,
                         nota: Optional[str] = None,
                         temporada_id: Optional[str] = None,
                         preinscripcion_id: Optional[str] = None) -> dict:
        """Crea una nueva obligacion.
        
        REGLAS:
        - El monto se copia del concepto (o se especifica manualmente)
        - Si es recurrente, se requiere periodo
        - Se verifica que no exista duplicada
        - Se asocia a temporada y preinscripcion (opcional)
        """
        # Verificar que el concepto existe y esta activo
        concepto = self.concepto_repo.obtener_por_id(concepto_id)
        if not concepto or not concepto.activo:
            raise ValueError(f"Concepto {concepto_id} no encontrado o inactivo")
        
        # Verificar duplicado para conceptos con periodo
        if concepto.requiere_periodo and periodo:
            if self.repo.existe_obligacion(club_id, deportista_id, concepto_id, periodo):
                raise ValueError(f"Ya existe una obligacion para el periodo {periodo}")
        
        # Calcular fecha limite si no se especifica
        if fecha_limite is None and concepto.requiere_periodo:
            config = self.config_repo.obtener_por_club(club_id)
            dias_limite = concepto.obtener_dias_limite(30) if config else 30
            fecha_limite = date.today() + timedelta(days=dias_limite)
        
        # Crear la obligacion
        datos = {
            "club_id": club_id,
            "deportista_id": deportista_id,
            "concepto_id": concepto_id,
            "monto_total": monto,
            "origen": origen.value,
            "fecha_creacion": date.today().isoformat(),
            "fecha_limite": fecha_limite.isoformat() if fecha_limite else None,
            "periodo": periodo,
            "referencia": referencia,
            "nota": nota,
        }
        
        # Campos opcionales nuevos
        if temporada_id:
            datos["temporada_id"] = temporada_id
        if preinscripcion_id:
            datos["preinscripcion_id"] = preinscripcion_id
        
        obligacion = self.repo.crear(datos)
        return obligacion.to_dict()

    def auto_generar_mensualidades(self, club_id: str, periodo: str) -> List[dict]:
        """Genera automaticamente las mensualidades para todos los deportistas activos.
        
        Este metodo se ejecuta al inicio de cada mes.
        Solo crea obligaciones para conceptos con genera_automaticamente=True.
        
        Args:
            club_id: ID del club
            periodo: Periodo en formato "YYYY-MM"
        
        Returns:
            Lista de obligaciones creadas
        """
        # Obtener conceptos que se auto-generan
        conceptos = self.concepto_repo.listar_por_club(club_id, solo_activos=True)
        conceptos_automaticos = [c for c in conceptos if c.genera_automaticamente]
        
        if not conceptos_automaticos:
            return []
        
        # Obtener deportistas activos del club
        from services.supabase_client import supabase
        deportistas_res = supabase.table("deportistas")\
            .select("id, nombre, categoria")\
            .eq("club_id", club_id)\
            .eq("estado", "activo")\
            .execute()
        
        if not deportistas_res.data:
            return []
        
        obligaciones_creadas = []
        
        for deportista in deportistas_res.data:
            for concepto in conceptos_automaticos:
                # Verificar que no exista ya
                if self.repo.existe_obligacion(
                    club_id, deportista["id"], concepto.id, periodo
                ):
                    continue
                
                # El monto se copia EXCLUSIVAMENTE del concepto
                # Si monto_default es 0, el admin debe configurarlo antes de auto-generar
                monto = concepto.monto_default
                
                # Crear la obligacion
                try:
                    obligacion = self.crear_obligacion(
                        club_id=club_id,
                        deportista_id=deportista["id"],
                        concepto_id=concepto.id,
                        monto=monto,
                        origen=OrigenObligacion.AUTOMATICO,
                        periodo=periodo,
                        referencia=f"Mensualidad {periodo}",
                    )
                    obligaciones_creadas.append(obligacion)
                except ValueError:
                    # Ya existe, ignorar
                    continue
        
        return obligaciones_creadas

    def resumen_estado(self, club_id: str, deportista_id: str) -> dict:
        """Retorna un resumen del estado financiero de un deportista.
        
        Este metodo es el que responde a "¿cuanto debo?" y "¿que he pagado?".
        """
        obligaciones = self.repo.listar_por_deportista(club_id, deportista_id)
        
        total_debe = 0
        total_pagado = 0
        obligaciones_pendientes = []
        obligaciones_pagadas = []
        
        for obligacion in obligaciones:
            monto_pagado = self.repo.calcular_monto_pagado(obligacion)
            obligacion.calcular_estado(monto_pagado)
            
            if obligacion.esta_cancelada:
                obligaciones_pagadas.append(obligacion.to_dict())
                total_pagado += monto_pagado
            else:
                obligaciones_pendientes.append(obligacion.to_dict())
                total_debe += obligacion.saldo_pendiente
        
        return {
            "deportista_id": deportista_id,
            "total_debe": total_debe,
            "total_pagado": total_pagado,
            "obligaciones_pendientes": obligaciones_pendientes,
            "obligaciones_pagadas": obligaciones_pagadas,
            "cantidad_pendientes": len(obligaciones_pendientes),
            "cantidad_pagadas": len(obligaciones_pagadas),
        }
