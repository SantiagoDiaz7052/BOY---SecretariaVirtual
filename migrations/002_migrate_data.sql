-- =============================================================
-- MIGRACION DE DATOS: Mensualidades → Obligaciones
-- BOY - SecretariaVirtual
-- =============================================================
-- Ejecutar DESPUES de 001_phase1_schema.sql
-- =============================================================

-- 1. Crear configuracion para todos los clubes existentes
INSERT INTO configuracion_club (club_id)
SELECT id FROM clubs
WHERE id NOT IN (SELECT club_id FROM configuracion_club)
ON CONFLICT (club_id) DO NOTHING;

-- 2. Crear conceptos para todos los clubes existentes
DO $$
DECLARE
    v_club RECORD;
BEGIN
    FOR v_club IN SELECT id FROM clubs LOOP
        INSERT INTO conceptos (club_id, nombre, es_recurrente, genera_automaticamente, 
                               aplica_mora, requiere_periodo, monto_default, activo)
        VALUES (v_club.id, 'Mensualidad', true, true, true, true, 0, true)
        ON CONFLICT (club_id, nombre) WHERE activo = true DO NOTHING;

        INSERT INTO conceptos (club_id, nombre, es_recurrente, genera_automaticamente, 
                               aplica_mora, requiere_periodo, monto_default, activo)
        VALUES (v_club.id, 'Inscripcion', false, false, false, false, 50000, true)
        ON CONFLICT (club_id, nombre) WHERE activo = true DO NOTHING;

        INSERT INTO conceptos (club_id, nombre, es_recurrente, genera_automaticamente, 
                               aplica_mora, requiere_periodo, monto_default, activo)
        VALUES (v_club.id, 'Licra', false, false, false, false, 0, true)
        ON CONFLICT (club_id, nombre) WHERE activo = true DO NOTHING;

        INSERT INTO conceptos (club_id, nombre, es_recurrente, genera_automaticamente, 
                               aplica_mora, requiere_periodo, monto_default, activo)
        VALUES (v_club.id, 'Uniforme', false, false, false, false, 0, true)
        ON CONFLICT (club_id, nombre) WHERE activo = true DO NOTHING;

        INSERT INTO conceptos (club_id, nombre, es_recurrente, genera_automaticamente, 
                               aplica_mora, requiere_periodo, monto_default, activo)
        VALUES (v_club.id, 'Evento', false, false, false, false, 0, true)
        ON CONFLICT (club_id, nombre) WHERE activo = true DO NOTHING;
    END LOOP;
END $$;

-- 3. Funcion auxiliar para obtener monto por categoria
-- NOTA: Estos valores corresponden a las tarifas vigentes al momento de la migracion.
-- Si las tarifas cambian, esta funcion NO se modifica (es historica).
-- Las nuevas obligaciones usan la logica de la capa de aplicacion.
CREATE OR REPLACE FUNCTION _temp_obtener_monto_categoria(p_categoria TEXT)
RETURNS NUMERIC AS $$
BEGIN
    RETURN CASE p_categoria
        WHEN 'Iniciacion' THEN 90000
        WHEN 'Intermedio' THEN 100000
        WHEN 'Avanzado' THEN 110000
        WHEN 'Escuela' THEN 90000
        ELSE 90000
    END;
END;
$$ LANGUAGE plpgsql;

-- 4. Migrar TODAS las mensualidades (pagadas Y pendientes)
DO $$
DECLARE
    v_mensualidad RECORD;
    v_concepto_id UUID;
    v_monto NUMERIC;
    v_origen TEXT;
    v_total_migradas INT := 0;
    v_total_pagadas INT := 0;
    v_total_pendientes INT := 0;
BEGIN
    IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'mensualidades') THEN
        RAISE NOTICE 'Tabla mensualidades no existe, saltando migracion';
        RETURN;
    END IF;

    FOR v_mensualidad IN 
        SELECT m.*, d.club_id, d.categoria
        FROM mensualidades m
        JOIN deportistas d ON d.id = m.deportista_id
    LOOP
        -- Obtener concepto Mensualidad del club
        SELECT id INTO v_concepto_id 
        FROM conceptos 
        WHERE club_id = v_mensualidad.club_id 
        AND nombre = 'Mensualidad'
        AND activo = true
        LIMIT 1;

        IF v_concepto_id IS NULL THEN
            CONTINUE;
        END IF;

        -- Obtener monto real usando la funcion auxiliar
        v_monto := _temp_obtener_monto_categoria(v_mensualidad.categoria);

        -- Determinar origen
        v_origen := CASE 
            WHEN v_mensualidad.created_at < '2025-01-01' THEN 'importado'
            ELSE 'automatico'
        END;

        -- Crear obligacion (pagada o pendiente, todas se migran)
        INSERT INTO obligaciones (
            club_id, deportista_id, concepto_id, monto_total, 
            origen, fecha_creacion, periodo, referencia
        ) VALUES (
            v_mensualidad.club_id,
            v_mensualidad.deportista_id,
            v_concepto_id,
            v_monto,
            v_origen,
            COALESCE(v_mensualidad.created_at::date, CURRENT_DATE),
            v_mensualidad.mes_anio,
            'Mensualidad ' || v_mensualidad.mes_anio
        ) ON CONFLICT (club_id, deportista_id, concepto_id, periodo) DO NOTHING;

        v_total_migradas := v_total_migradas + 1;

        -- Solo si esta pagada, crear el pago referenciado
        IF v_mensualidad.estado = 'pagado' THEN
            INSERT INTO pagos (
                club_id, deportista_id, concepto_id, monto,
                estado, mes_anio, created_at
            ) VALUES (
                v_mensualidad.club_id,
                v_mensualidad.deportista_id,
                v_concepto_id,
                v_monto,
                'aprobado',
                v_mensualidad.mes_anio,
                COALESCE(v_mensualidad.pagado_at, v_mensualidad.created_at, now())
            );
            v_total_pagadas := v_total_pagadas + 1;
        ELSE
            v_total_pendientes := v_total_pendientes + 1;
        END IF;
    END LOOP;

    RAISE NOTICE 'Migracion completada: % total, % pagadas, % pendientes', 
        v_total_migradas, v_total_pagadas, v_total_pendientes;
END $$;

-- 5. Limpiar funcion auxiliar
DROP FUNCTION IF EXISTS _temp_obtener_monto_categoria(TEXT);

-- 6. Crear indice para pagos por concepto
CREATE INDEX IF NOT EXISTS idx_pagos_concepto_id 
ON pagos(concepto_id) WHERE concepto_id IS NOT NULL;

-- 7. Verificar migracion
SELECT 
    'Conceptos creados' AS accion,
    COUNT(*) AS cantidad
FROM conceptos
WHERE activo = true
UNION ALL
SELECT 
    'Configuraciones creadas' AS accion,
    COUNT(*) AS cantidad
FROM configuracion_club
UNION ALL
SELECT 
    'Obligaciones migradas (total)' AS accion,
    COUNT(*) AS cantidad
FROM obligaciones
UNION ALL
SELECT 
    'Obligaciones pagadas' AS accion,
    COUNT(*) AS cantidad
FROM pagos
WHERE estado = 'aprobado' AND concepto_id IS NOT NULL
UNION ALL
SELECT 
    'Obligaciones pendientes (sin pago aprobado)' AS accion,
    COUNT(*) AS cantidad
FROM obligaciones o
WHERE NOT EXISTS (
    SELECT 1 FROM pagos p 
    WHERE p.deportista_id = o.deportista_id 
    AND p.concepto_id = o.concepto_id
    AND p.mes_anio = o.periodo
    AND p.estado = 'aprobado'
);
