from typing import Optional
from repositories.usuario_admin_repo import UsuarioAdminRepository
from domain.usuario_admin import UsuarioAdmin, RolUsuario


class UsuarioAdminService:
    def __init__(self):
        self.repo = UsuarioAdminRepository()
        self._usuario_cache: Optional[UsuarioAdmin] = None

    def autenticar(self, usuario: str, password: str) -> Optional[UsuarioAdmin]:
        user = self.repo.obtener_por_usuario(usuario)
        if not user:
            return None
        if not self.repo.verificar_password(password, user):
            return None
        self._usuario_cache = user
        return user

    def obtener_usuario(self, usuario: str) -> Optional[UsuarioAdmin]:
        return self.repo.obtener_por_usuario(usuario)

    @property
    def usuario_actual(self) -> Optional[UsuarioAdmin]:
        return self._usuario_cache

    def crear_usuario_default(self) -> None:
        self.repo.crear_usuario_default()
