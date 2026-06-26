from typing import Optional, List
from services.supabase_client import supabase
from domain.obligacion import Obligacion


class ObligacionRepository:
    """Repositorio para obligaciones en Supabase."""

    TABLE = "obligaciones"

    def obtener_por_id(self, obligacion_id: str) -> Optional[Obligacion]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("id", obligacion_id)\
            .single()\
            .execute()
        
        if not resultado.data:
            return None
        return Obligacion.from_dict(resultado.data)

    def listar_por_deportista(self, club_id: str, deportista_id: str, 
                              solo_pendientes: bool = False) -> List[Obligacion]:
        query = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("deportista_id", deportista_id)
        
        resultado = query.order("created_at", desc=True).execute()
        obligaciones = [Obligacion.from_dict(o) for o in (resultado.data or [])]
        
        if solo_pendientes:
            # Filtrar en memoria las que tienen saldo pendiente
            # Nota: Esto es una simplificacion. En V2 se puede hacer con vista SQL
            obligaciones = [o for o in obligaciones if o.saldo_pendiente > 0]
        
        return obligaciones

    def listar_por_club(self, club_id: str, periodo: Optional[str] = None) -> List[Obligacion]:
        query = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)
        
        if periodo:
            query = query.eq("periodo", periodo)
        
        resultado = query.order("created_at", desc=True).execute()
        return [Obligacion.from_dict(o) for o in (resultado.data or [])]

    def listar_por_concepto(self, club_id: str, concepto_id: str, 
                            periodo: Optional[str] = None) -> List[Obligacion]:
        query = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("concepto_id", concepto_id)
        
        if periodo:
            query = query.eq("periodo", periodo)
        
        resultado = query.execute()
        return [Obligacion.from_dict(o) for o in (resultado.data or [])]

    def existe_obligacion(self, club_id: str, deportista_id: str, 
                          concepto_id: str, periodo: Optional[str] = None) -> bool:
        """Verifica si ya existe una obligacion para evitar duplicados."""
        query = supabase.table(self.TABLE)\
            .select("id")\
            .eq("club_id", club_id)\
            .eq("deportista_id", deportista_id)\
            .eq("concepto_id", concepto_id)
        
        if periodo:
            query = query.eq("periodo", periodo)
        
        resultado = query.execute()
        return bool(resultado.data)

    def crear(self, obligacion: dict) -> Obligacion:
        resultado = supabase.table(self.TABLE)\
            .insert(obligacion)\
            .execute()
        return Obligacion.from_dict(resultado.data[0])

    def crear_varias(self, obligaciones: List[dict]) -> List[Obligacion]:
        """Crea multiples obligaciones en lote (para auto-generacion mensual)."""
        if not obligaciones:
            return []
        
        resultado = supabase.table(self.TABLE)\
            .insert(obligaciones)\
            .execute()
        return [Obligacion.from_dict(o) for o in (resultado.data or [])]

    def calcular_monto_pagado(self, obligacion: Obligacion) -> float:
        """Calcula el monto total pagado para una obligacion.
        
        Consulta la tabla de pagos y suma los montos aprobados.
        Esto es un dato derivado, NUNCA se almacena en la obligacion.
        """
        resultado = supabase.table("pagos")\
            .select("monto")\
            .eq("deportista_id", obligacion.deportista_id)\
            .eq("concepto_id", obligacion.concepto_id)\
            .eq("estado", "aprobado")
        
        if obligacion.periodo:
            resultado = resultado.eq("mes_anio", obligacion.periodo)
        
        resultado = resultado.execute()
        
        if not resultado.data:
            return 0.0
        
        return sum(float(p["monto"]) for p in resultado.data)

    def obtener_obligaciones_con_saldo(self, club_id: str, 
                                       deportista_id: Optional[str] = None) -> List[dict]:
        """Obtiene obligaciones con saldo pendiente calculado.
        
        Retorna una lista de diccionarios con la obligacion y su saldo.
        """
        query = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)
        
        if deportista_id:
            query = query.eq("deportista_id", deportista_id)
        
        resultado = query.execute()
        obligaciones_con_saldo = []
        
        for o in (resultado.data or []):
            obligacion = Obligacion.from_dict(o)
            monto_pagado = self.calcular_monto_pagado(obligacion)
            obligacion.calcular_estado(monto_pagado)
            
            if not obligacion.esta_cancelada:
                obligaciones_con_saldo.append(obligacion.to_dict())
        
        return obligaciones_con_saldo
