-- 005_phase3_lifecycle.sql
-- Migracion: Lifecycle de deportista, preinscripciones, contexto conversacional

-- ============================================================
-- TABLA TEMPORADAS
-- ============================================================
CREATE TABLE IF NOT EXISTS temporadas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES clubs(id),
    nombre TEXT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    estado TEXT NOT NULL DEFAULT 'activa',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA PREINSCRIPCIONES
-- ============================================================
CREATE TABLE IF NOT EXISTS preinscripciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES clubs(id),
    temporada_id UUID NOT NULL REFERENCES temporadas(id),
    nombre TEXT NOT NULL,
    documento TEXT NOT NULL,
    telefono TEXT,
    fecha_nacimiento DATE,
    nivel TEXT NOT NULL,
    responsable_nombre TEXT,
    responsable_documento TEXT,
    responsable_whatsapp TEXT,
    obligacion_id UUID REFERENCES obligaciones(id),
    proceso_pago_id UUID REFERENCES procesos_pago(id),
    estado TEXT NOT NULL DEFAULT 'pendiente_pago',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA CONTEXTOS CONVERSACIONALES
-- ============================================================
CREATE TABLE IF NOT EXISTS contextos_conversacionales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES clubs(id),
    numero_whatsapp TEXT NOT NULL,
    deportista_actual_id UUID,
    proceso_pago_actual_id UUID,
    obligacion_actual_id UUID,
    ultima_intencion TEXT,
    ultimo_comprobante_url TEXT,
    estado TEXT NOT NULL DEFAULT 'activa',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CAMPOS NUEVOS EN DEPORTISTAS
-- ============================================================
ALTER TABLE deportistas ADD COLUMN IF NOT EXISTS temporada_id UUID REFERENCES temporadas(id);
ALTER TABLE deportistas ADD COLUMN IF NOT EXISTS nivel TEXT DEFAULT 'iniciacion';
ALTER TABLE deportistas ADD COLUMN IF NOT EXISTS responsable_nombre TEXT;
ALTER TABLE deportistas ADD COLUMN IF NOT EXISTS responsable_documento TEXT;
ALTER TABLE deportistas ADD COLUMN IF NOT EXISTS responsable_whatsapp TEXT;

-- ============================================================
-- CAMPOS NUEVOS EN OBLIGACIONES
-- ============================================================
ALTER TABLE obligaciones ADD COLUMN IF NOT EXISTS preinscripcion_id UUID REFERENCES preinscripciones(id);
ALTER TABLE obligaciones ADD COLUMN IF NOT EXISTS temporada_id UUID REFERENCES temporadas(id);

-- ============================================================
-- CAMPOS NUEVOS EN PROCESOS_PAGO
-- ============================================================
ALTER TABLE procesos_pago ADD COLUMN IF NOT EXISTS preinscripcion_id UUID REFERENCES preinscripciones(id);
ALTER TABLE procesos_pago ADD COLUMN IF NOT EXISTS temporada_id UUID REFERENCES temporadas(id);

-- ============================================================
-- CAMPOS NUEVOS EN PAGOS
-- ============================================================
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS preinscripcion_id UUID REFERENCES preinscripciones(id);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS temporada_id UUID REFERENCES temporadas(id);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS hash_comprobante TEXT;
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS referencia_detectada TEXT;
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS fecha_detectada TEXT;
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS plataforma_detectada TEXT;

-- ============================================================
-- CAMPOS NUEVOS EN CONFIGURACION_CLUB
-- ============================================================
ALTER TABLE configuracion_club ADD COLUMN IF NOT EXISTS recargo_fijo DECIMAL(10,2) DEFAULT 0;
ALTER TABLE configuracion_club ADD COLUMN IF NOT EXISTS monto_inscripcion DECIMAL(10,2) DEFAULT 50000;
ALTER TABLE configuracion_club ADD COLUMN IF NOT EXISTS dias_gracia_recargo INTEGER DEFAULT 10;
ALTER TABLE configuracion_club ADD COLUMN IF NOT EXISTS horas_expiracion_proceso INTEGER DEFAULT 48;

-- ============================================================
-- INDICES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_temporadas_club ON temporadas(club_id);
CREATE INDEX IF NOT EXISTS idx_contextos_whatsapp ON contextos_conversacionales(club_id, numero_whatsapp);
CREATE INDEX IF NOT EXISTS idx_preinscripciones_documento ON preinscripciones(club_id, documento);
CREATE INDEX IF NOT EXISTS idx_pagos_hash ON pagos(hash_comprobante) WHERE hash_comprobante IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pagos_referencia ON pagos(referencia_detectada) WHERE referencia_detectada IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_deportistas_temporada ON deportistas(temporada_id);
CREATE INDEX IF NOT EXISTS idx_obligaciones_temporada ON obligaciones(temporada_id);

-- ============================================================
-- CONSTRAINTS
-- ============================================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_temporada_activa 
ON temporadas(club_id) WHERE estado = 'activa';

CREATE UNIQUE INDEX IF NOT EXISTS idx_contexto_activo 
ON contextos_conversacionales(club_id, numero_whatsapp) WHERE estado = 'activa';

CREATE UNIQUE INDEX IF NOT EXISTS idx_preinscripcion_pendiente 
ON preinscripciones(club_id, documento) WHERE estado = 'pendiente_pago';

-- ============================================================
-- COMENTARIOS
-- ============================================================
COMMENT ON TABLE temporadas IS 'Temporadas deportivas (2026, 2027, etc)';
COMMENT ON TABLE preinscripciones IS 'Preinscripciones antes de crear deportista';
COMMENT ON TABLE contextos_conversacionales IS 'Memoria activa del usuario en conversacion';
COMMENT ON COLUMN deportistas.estado IS 'inactivo: no pago mensualidad, activo: pago y puede entrenar';
COMMENT ON COLUMN deportistas.nivel IS 'iniciacion, intermedio, avanzado - asignado en matricula';
COMMENT ON COLUMN configuracion_club.monto_inscripcion IS 'Monto configurable para matricula por club';
COMMENT ON COLUMN configuracion_club.recargo_fijo IS 'Recargo para activacion tardia (dia 11+)';
COMMENT ON COLUMN configuracion_club.horas_expiracion_proceso IS 'Horas para expirar proceso abandonado';
