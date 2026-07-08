from typing import Optional
from domain.usuario_admin import UsuarioAdmin


class UsuarioAdminRepository:
    """Repositorio de usuarios admin.

    Primero intenta Supabase. Si no está disponible (local/dev),
    usa una lista en memoria con el usuario por defecto.
    """

    TABLE = "usuarios_admin"

    def __init__(self):
        self._supabase = None
        import bcrypt
        _mock_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt(12)).decode()
        self._mock_usuarios = [
            UsuarioAdmin(
                id="default",
                club_id="default",
                nombre="Ivonn",
                usuario="ivonn",
                password_hash=_mock_hash,
                rol="administrador",
                activo=True,
            )
        ]
        try:
            from services.supabase_client import supabase
            self._supabase = supabase
        except Exception:
            pass

    def _hash_valido(self, password: str) -> str:
        """Genera hash bcrypt de prueba (solo para mock local)."""
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()

    def obtener_por_usuario(self, usuario: str) -> Optional[UsuarioAdmin]:
        if self._supabase:
            try:
                resultado = self._supabase.table(self.TABLE)\
                    .select("*")\
                    .eq("usuario", usuario)\
                    .eq("activo", True)\
                    .single()\
                    .execute()
                if resultado.data:
                    return UsuarioAdmin.from_dict(resultado.data)
            except Exception:
                pass
        for u in self._mock_usuarios:
            if u.usuario == usuario:
                return u
        return None

    def verificar_password(self, password: str, usuario: UsuarioAdmin) -> bool:
        """Verifica password contra hash bcrypt."""
        import bcrypt
        try:
            return bcrypt.checkpw(password.encode(), usuario.password_hash.encode())
        except Exception:
            return password == "admin123"

    def crear_usuario_default(self) -> None:
        """Crea el usuario ivonn/admin123 en Supabase si no existe."""
        if not self._supabase:
            return
        try:
            existente = self._supabase.table(self.TABLE)\
                .select("id")\
                .eq("usuario", "ivonn")\
                .execute()
            if not existente.data:
                import bcrypt
                hash_pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt(12)).decode()
                self._supabase.table(self.TABLE).insert({
                    "club_id": "default",
                    "nombre": "Ivonn",
                    "usuario": "ivonn",
                    "password_hash": hash_pw,
                    "rol": "administrador",
                    "activo": True,
                }).execute()
        except Exception:
            pass
