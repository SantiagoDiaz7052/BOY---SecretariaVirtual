-- =============================================================
-- FASE 2: ProcesoPago (contexto conversacional)
-- BOY - SecretariaVirtual
-- =============================================================
-- Ejecutar en Supabase SQL Editor DESPUES de Fase 1
-- =============================================================

-- TABLA: procesos_pago
-- Contexto conversacional de un intento de pago
-- NO es una entidad financiera - representa la CONVERSACION
CREATE TABLE IF NOT EXISTS procesos_pago (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    club_id UUID NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    deportista_id UUID NOT NULL REFERENCES deportistas(id) ON DELETE CASCADE,
    obligacion_id UUID REFERENCES obligaciones(id) ON DELETE SET NULL,
    llave_bre_b TEXT DEFAULT NULL,
    monto_informado NUMERIC DEFAULT NULL,
    estado TEXT NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'finalizado', 'cancelado')),
    historial JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_procesos_pago_club_deportista 
ON procesos_pago(club_id, deportista_id);

CREATE INDEX IF NOT EXISTS idx_procesos_pago_estado 
ON procesos_pago(estado) WHERE estado = 'activo';

CREATE INDEX IF NOT EXISTS idx_procesos_pago_created_at 
ON procesos_pago(created_at);

-- Solo un proceso activo por deportista por club
-- (se valida en aplicacion, pero el indice ayuda a la consulta)
CREATE UNIQUE INDEX IF NOT EXISTS idx_procesos_pago_activo_unico 
ON procesos_pago(club_id, deportista_id) 
WHERE estado = 'activo';

-- Trigger para updated_at
CREATE TRIGGER update_procesos_pago_updated_at 
BEFORE UPDATE ON procesos_pago
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================
-- VERIFICACION
-- =============================================================
SELECT 
    'Tabla procesos_pago creada' AS accion,
    COUNT(*) AS registros
FROM procesos_pago;
