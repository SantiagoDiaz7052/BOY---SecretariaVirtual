-- 007_phase5_auth_notifications.sql
-- Migracion: Usuarios admin, notificaciones, roles

-- ============================================================
-- TABLA USUARIOS_ADMIN
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios_admin (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID REFERENCES clubs(id),
    nombre TEXT NOT NULL,
    usuario TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL DEFAULT 'secretaria',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA NOTIFICACIONES
-- ============================================================
CREATE TABLE IF NOT EXISTS notificaciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES clubs(id),
    tipo TEXT NOT NULL,
    icono TEXT NOT NULL DEFAULT '🔔',
    texto TEXT NOT NULL,
    referencia_id UUID,
    leida BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- USUARIO POR DEFECTO (ivonn / admin123)
-- ============================================================
-- El hash bcrypt de 'admin123' se genera en la aplicacion
-- Este INSERT se ejecuta condicionalmente desde la app

-- ============================================================
-- INDICES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios_admin(usuario);
CREATE INDEX IF NOT EXISTS idx_notificaciones_club ON notificaciones(club_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notificaciones_no_leidas ON notificaciones(club_id, leida) WHERE leida = FALSE;

-- ============================================================
-- COMENTARIOS
-- ============================================================
COMMENT ON TABLE usuarios_admin IS 'Usuarios del panel administrativo con roles';
COMMENT ON TABLE notificaciones IS 'Notificaciones del sistema para el panel';
COMMENT ON COLUMN usuarios_admin.rol IS 'administrador, secretaria, solo_lectura';
