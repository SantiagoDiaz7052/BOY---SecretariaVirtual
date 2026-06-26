from typing import Optional, List
from services.supabase_client import supabase
from domain.concepto import Concepto


class ConceptoRepository:
    """Repositorio para conceptos en Supabase."""

    TABLE = "conceptos"

    def obtener_por_id(self, concepto_id: str) -> Optional[Concepto]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("id", concepto_id)\
            .single()\
            .execute()
        
        if not resultado.data:
            return None
        return Concepto.from_dict(resultado.data)

    def listar_por_club(self, club_id: str, solo_activos: bool = True) -> List[Concepto]:
        query = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)
        
        if solo_activos:
            query = query.eq("activo", True)
        
        resultado = query.order("nombre").execute()
        return [Concepto.from_dict(c) for c in (resultado.data or [])]

    def buscar_por_nombre(self, club_id: str, nombre: str) -> Optional[Concepto]:
        resultado = supabase.table(self.TABLE)\
            .select("*")\
            .eq("club_id", club_id)\
            .eq("nombre", nombre)\
            .eq("activo", True)\
            .single()\
            .execute()
        
        if not resultado.data:
            return None
        return Concepto.from_dict(resultado.data)

    def crear(self, concepto: dict) -> Concepto:
        resultado = supabase.table(self.TABLE)\
            .insert(concepto)\
            .execute()
        return Concepto.from_dict(resultado.data[0])

    def actualizar(self, concepto_id: str, datos: dict) -> Concepto:
        """Actualiza un concepto. IMPORTANTE: Esto crea una nueva version
        si se cambia el monto o comportamiento. Las obligaciones existentes
        NO se ven afectadas porque copian el precio al momento de crearse."""
        resultado = supabase.table(self.TABLE)\
            .update(datos)\
            .eq("id", concepto_id)\
            .execute()
        return Concepto.from_dict(resultado.data[0])

    def desactivar(self, concepto_id: str) -> bool:
        supabase.table(self.TABLE)\
            .update({"activo": False})\
            .eq("id", concepto_id)\
            .execute()
        return True
