CREATE TABLE IF NOT EXISTS notificaciones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tipo TEXT NOT NULL,
  icono TEXT DEFAULT '🔔',
  texto TEXT NOT NULL,
  referencia_id UUID,
  leida BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE notificaciones ENABLE ROW LEVEL SECURITY;
