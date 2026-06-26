-- =============================================================
-- FASE 1: Conceptos, ConfiguracionClub, Obligaciones
-- BOY - SecretariaVirtual
-- =============================================================
-- Ejecutar en Supabase SQL Editor
-- NO eliminar tablas existentes, solo crear nuevas
-- =============================================================

-- 1. TABLA: conceptos (SE CREA PRIMERO - es dependencia de pagos.concepto_id)
CREATE TABLE IF NOT EXISTS conceptos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    es_recurrente BOOLEAN DEFAULT false,
    genera_automaticamente BOOLEAN DEFAULT false,
    aplica_mora BOOLEAN DEFAULT false,
    requiere_periodo BOOLEAN DEFAULT false,
    monto_default NUMERIC DEFAULT 0,
    recargo_fijo NUMERIC DEFAULT NULL,
    dias_limite_pago INT DEFAULT NULL,
    version INT DEFAULT 1,
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Un concepto no se duplica por club mientras este activo
CREATE UNIQUE INDEX IF NOT EXISTS idx_conceptos_club_nombre 
ON conceptos(club_id, nombre) WHERE activo = true;

-- 2. TABLA: configuracion_club
CREATE TABLE IF NOT EXISTS configuracion_club (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL UNIQUE REFERENCES clubs(id) ON DELETE CASCADE,
    llave_bre_b TEXT DEFAULT NULL,
    tolerancia_monto NUMERIC DEFAULT 5000,
    recargo_default NUMERIC DEFAULT 0,
    recordatorio_dias INT[] DEFAULT '{3, 1, 0}',
    notificar_estado_pago BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. TABLA: obligaciones
CREATE TABLE IF NOT EXISTS obligaciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    deportista_id UUID NOT NULL REFERENCES deportistas(id) ON DELETE CASCADE,
    concepto_id UUID NOT NULL REFERENCES conceptos(id) ON DELETE RESTRICT,
    monto_total NUMERIC NOT NULL,
    origen TEXT NOT NULL DEFAULT 'automatico' CHECK (origen IN ('automatico', 'manual', 'importado')),
    fecha_creacion DATE DEFAULT CURRENT_DATE,
    fecha_limite DATE DEFAULT NULL,
    periodo TEXT DEFAULT NULL,
    referencia TEXT DEFAULT NULL,
    nota TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Constraint unico: una obligacion por deportista+concepto+periodo
CREATE UNIQUE INDEX IF NOT EXISTS idx_obligaciones_unique 
ON obligaciones(club_id, deportista_id, concepto_id, periodo) 
WHERE periodo IS NOT NULL;

-- Indices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_obligaciones_club_deportista 
ON obligaciones(club_id, deportista_id);

CREATE INDEX IF NOT EXISTS idx_obligaciones_deportista 
ON obligaciones(deportista_id);

CREATE INDEX IF NOT EXISTS idx_obligaciones_periodo 
ON obligaciones(periodo) WHERE periodo IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_obligaciones_fecha_limite 
ON obligaciones(fecha_limite) WHERE fecha_limite IS NOT NULL;

-- 4. AGREGAR COLUMNA concepto_id A TABLA pagos
-- (conceptos ya existe, la FK es segura)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'pagos' AND column_name = 'concepto_id'
    ) THEN
        ALTER TABLE pagos ADD COLUMN concepto_id UUID REFERENCES conceptos(id) ON DELETE SET NULL;
    END IF;
END $$;

-- =============================================================
-- VISTA: Saldo pendiente (se calcula, no se almacena)
-- =============================================================
CREATE OR REPLACE VIEW v_saldo_obligaciones AS
SELECT 
    o.id AS obligacion_id,
    o.club_id,
    o.deportista_id,
    o.concepto_id,
    o.monto_total,
    o.origen,
    o.fecha_creacion,
    o.fecha_limite,
    o.periodo,
    o.referencia,
    o.nota,
    COALESCE(SUM(p.monto) FILTER (WHERE p.estado = 'aprobado'), 0) AS monto_pagado,
    o.monto_total - COALESCE(SUM(p.monto) FILTER (WHERE p.estado = 'aprobado'), 0) AS saldo_pendiente,
    CASE 
        WHEN o.monto_total - COALESCE(SUM(p.monto) FILTER (WHERE p.estado = 'aprobado'), 0) <= 0 THEN 'pagada'
        WHEN o.fecha_limite IS NOT NULL AND o.fecha_limite < CURRENT_DATE THEN 'vencida'
        ELSE 'pendiente'
    END AS estado_calculado,
    o.created_at
FROM obligaciones o
LEFT JOIN pagos p ON p.deportista_id = o.deportista_id 
    AND p.concepto_id = o.concepto_id
    AND (o.periodo IS NULL OR p.mes_anio = o.periodo)
GROUP BY o.id;

-- =============================================================
-- FUNCIONES
-- =============================================================

-- Funcion para crear conceptos iniciales cuando se registra un club
CREATE OR REPLACE FUNCTION crear_conceptos_iniciales(p_club_id UUID)
RETURNS VOID AS $$
BEGIN
    INSERT INTO conceptos (club_id, nombre, es_recurrente, genera_automaticamente, 
                           aplica_mora, requiere_periodo, monto_default, activo)
    VALUES (p_club_id, 'Mensualidad', true, true, true, true, 0, true)
    ON CONFLICT DO NOTHING;

    INSERT INTO conceptos (club_id, nombre, es_recurrente, genera_automaticamente, 
                           aplica_mora, requiere_periodo, monto_default, activo)
    VALUES (p_club_id, 'Inscripcion', false, false, false, false, 50000, true)
    ON CONFLICT DO NOTHING;

    INSERT INTO conceptos (club_id, nombre, es_recurrente, genera_automaticamente, 
                           aplica_mora, requiere_periodo, monto_default, activo)
    VALUES (p_club_id, 'Licra', false, false, false, false, 0, true)
    ON CONFLICT DO NOTHING;

    INSERT INTO conceptos (club_id, nombre, es_recurrente, genera_automaticamente, 
                           aplica_mora, requiere_periodo, monto_default, activo)
    VALUES (p_club_id, 'Uniforme', false, false, false, false, 0, true)
    ON CONFLICT DO NOTHING;

    INSERT INTO conceptos (club_id, nombre, es_recurrente, genera_automaticamente, 
                           aplica_mora, requiere_periodo, monto_default, activo)
    VALUES (p_club_id, 'Evento', false, false, false, false, 0, true)
    ON CONFLICT DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- Funcion para crear configuracion por defecto para un club
CREATE OR REPLACE FUNCTION crear_configuracion_default(p_club_id UUID)
RETURNS VOID AS $$
BEGIN
    INSERT INTO configuracion_club (club_id) VALUES (p_club_id)
    ON CONFLICT (club_id) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

-- =============================================================
-- TRIGGER: Auto-actualizar updated_at
-- =============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_configuracion_club_updated_at 
BEFORE UPDATE ON configuracion_club
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conceptos_updated_at 
BEFORE UPDATE ON conceptos
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
