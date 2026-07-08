from dataclasses import dataclass
from typing import Optional
from enum import Enum


class RolUsuario(str, Enum):
    ADMINISTRADOR = "administrador"
    SECRETARIA = "secretaria"
    SOLO_LECTURA = "solo_lectura"


@dataclass
class UsuarioAdmin:
    id: Optional[str] = None
    club_id: Optional[str] = None
    nombre: str = ""
    usuario: str = ""
    password_hash: str = ""
    rol: str = RolUsuario.SECRETARIA.value
    activo: bool = True
    created_at: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "UsuarioAdmin":
        return UsuarioAdmin(
            id=data.get("id"),
            club_id=data.get("club_id"),
            nombre=data.get("nombre", ""),
            usuario=data.get("usuario", ""),
            password_hash=data.get("password_hash", ""),
            rol=data.get("rol", RolUsuario.SECRETARIA.value),
            activo=data.get("activo", True),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "club_id": self.club_id,
            "nombre": self.nombre,
            "usuario": self.usuario,
            "password_hash": self.password_hash,
            "rol": self.rol,
            "activo": self.activo,
            "created_at": self.created_at,
        }

    @property
    def puede_editar(self) -> bool:
        return self.rol in (RolUsuario.ADMINISTRADOR.value, RolUsuario.SECRETARIA.value)

    @property
    def es_admin(self) -> bool:
        return self.rol == RolUsuario.ADMINISTRADOR.value
