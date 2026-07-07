-- 006_phase4_solicitudes.sql
-- Migracion: SolicitudIngreso reemplaza Preinscripcion, Tareas, ajustes finales

-- ============================================================
-- TABLA SOLICITUDES_INGRESO (reemplaza preinscripciones)
-- ============================================================
CREATE TABLE IF NOT EXISTS solicitudes_ingreso (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES clubs(id),
    temporada_id UUID NOT NULL REFERENCES temporadas(id),
    nombre TEXT NOT NULL,
    documento TEXT NOT NULL,
    telefono TEXT,
    fecha_nacimiento DATE,
    experiencia_reportada TEXT,
    responsable_nombre TEXT,
    responsable_documento TEXT,
    responsable_whatsapp TEXT,
    nivel TEXT,
    fecha_evaluacion DATE,
    estado TEXT NOT NULL DEFAULT 'pendiente_evaluacion',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA TAREAS (bandeja de trabajo, proyeccion derivada)
-- ============================================================
CREATE TABLE IF NOT EXISTS tareas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES clubs(id),
    tipo TEXT NOT NULL,
    referencia_id UUID NOT NULL,
    descripcion TEXT,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================================
-- CAMPOS NUEVOS EN DEPORTISTAS
-- ============================================================
ALTER TABLE deportistas ADD COLUMN IF NOT EXISTS experiencia_reportada TEXT;
-- nivel ya existe, pero cambiamos default: no default, nullable
-- Nota: PostgreSQL no permite cambiar default de columna existente a sin default
-- Se corrige en aplicacion (domain/deportista.py ya no setea default)

-- ============================================================
-- CAMPOS NUEVOS EN CONCEPTOS
-- ============================================================
ALTER TABLE conceptos ADD COLUMN IF NOT EXISTS precios_por_nivel JSONB;

-- ============================================================
-- CAMPOS NUEVOS EN PROCESOS_PAGO
-- ============================================================
ALTER TABLE procesos_pago ADD COLUMN IF NOT EXISTS solicitud_ingreso_id UUID REFERENCES solicitudes_ingreso(id);
ALTER TABLE procesos_pago ADD COLUMN IF NOT EXISTS expirado BOOLEAN DEFAULT FALSE;

-- ============================================================
-- MODIFICAR CHECK CONSTRAINT DE PROCESOS_PAGO.ESTADO
-- ============================================================
-- Primero intentamos dropear el constraint si existe (nombre generico)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname LIKE '%procesos_pago%estado%check%'
        OR (conrelid = 'procesos_pago'::regclass AND contype = 'c')
    ) THEN
        ALTER TABLE procesos_pago DROP CONSTRAINT IF EXISTS procesos_pago_estado_check;
    END IF;
END $$;

ALTER TABLE procesos_pago ADD CONSTRAINT procesos_pago_estado_check 
    CHECK (estado IN ('activo', 'finalizado', 'cancelado', 'expirado'));

-- ============================================================
-- NUEVOS CAMPOS EN CONFIGURACION_CLUB
-- ============================================================
ALTER TABLE configuracion_club ADD COLUMN IF NOT EXISTS experiencias_disponibles JSONB DEFAULT '["si", "no", "no_sabe"]';
ALTER TABLE configuracion_club ADD COLUMN IF NOT EXISTS niveles_disponibles JSONB DEFAULT '["iniciacion", "intermedio", "avanzado"]';

-- ============================================================
-- INDICES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_solicitudes_club ON solicitudes_ingreso(club_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_documento ON solicitudes_ingreso(club_id, documento);
CREATE INDEX IF NOT EXISTS idx_solicitudes_estado ON solicitudes_ingreso(club_id, estado);
CREATE INDEX IF NOT EXISTS idx_solicitudes_whatsapp ON solicitudes_ingreso(club_id, telefono);
CREATE INDEX IF NOT EXISTS idx_tareas_club ON tareas(club_id);
CREATE INDEX IF NOT EXISTS idx_tareas_referencia ON tareas(referencia_id);
CREATE INDEX IF NOT EXISTS idx_tareas_pendientes ON tareas(club_id, estado) WHERE estado = 'pendiente';
CREATE INDEX IF NOT EXISTS idx_procesos_pago_solicitud ON procesos_pago(solicitud_ingreso_id) WHERE solicitud_ingreso_id IS NOT NULL;

-- ============================================================
-- CONSTRAINTS
-- ============================================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_solicitud_activa 
ON solicitudes_ingreso(club_id, documento) 
WHERE estado NOT IN ('completado', 'cancelado');

-- ============================================================
-- COMENTARIOS
-- ============================================================
COMMENT ON TABLE solicitudes_ingreso IS 'Solicitudes de ingreso (reemplaza preinscripciones) - flujo completo de admision';
COMMENT ON TABLE tareas IS 'Bandeja de trabajo para secretaria - proyeccion derivada del dominio';
COMMENT ON COLUMN solicitudes_ingreso.estado IS 'pendiente_evaluacion, evaluado, pendiente_matricula, matricula_pagada, pendiente_activacion, completado, cancelado';
COMMENT ON COLUMN solicitudes_ingreso.nivel IS 'Asignado por secretaria en evaluacion - NULL hasta entonces';
COMMENT ON COLUMN solicitudes_ingreso.experiencia_reportada IS 'Referencia: si, no, no_sabe - NO determina nivel';
COMMENT ON COLUMN conceptos.precios_por_nivel IS 'Dict con precios por nivel ej: {"iniciacion": 30000, "intermedio": 35000, "avanzado": 40000}';
COMMENT ON COLUMN procesos_pago.solicitud_ingreso_id IS 'Relacion opcional con solicitud de ingreso (NO al reves)';
COMMENT ON COLUMN procesos_pago.estado IS 'activo, finalizado, cancelado, expirado';
