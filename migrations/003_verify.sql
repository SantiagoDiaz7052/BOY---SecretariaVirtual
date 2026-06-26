-- =============================================================
-- VERIFICACION POST-MIGRACION
-- Ejecutar DESPUES de 001 y 002
-- =============================================================

-- 1. Conteo general
SELECT '=== RESUMEN ===' AS seccion;
SELECT 'Clubs' AS tabla, COUNT(*) AS registros FROM clubs;
SELECT 'Deportistas' AS tabla, COUNT(*) AS registros FROM deportistas;
SELECT 'Pagos' AS tabla, COUNT(*) AS registros FROM pagos;
SELECT 'Conceptos' AS tabla, COUNT(*) AS registros FROM conceptos;
SELECT 'Configuraciones' AS tabla, COUNT(*) AS registros FROM configuracion_club;
SELECT 'Obligaciones' AS tabla, COUNT(*) AS registros FROM obligaciones;

-- 2. Verificar foreign keys
SELECT '=== FOREIGN KEYS ===' AS seccion;

SELECT 'Conceptos sin club (ERROR)' AS verificacion, COUNT(*) AS cantidad
FROM conceptos c
LEFT JOIN clubs cl ON cl.id = c.club_id
WHERE cl.id IS NULL;

SELECT 'Configuracion sin club (ERROR)' AS verificacion, COUNT(*) AS cantidad
FROM configuracion_club cc
LEFT JOIN clubs cl ON cl.id = cc.club_id
WHERE cl.id IS NULL;

SELECT 'Obligaciones sin deportista (ERROR)' AS verificacion, COUNT(*) AS cantidad
FROM obligaciones o
LEFT JOIN deportistas d ON d.id = o.deportista_id
WHERE d.id IS NULL;

SELECT 'Obligaciones sin concepto (ERROR)' AS verificacion, COUNT(*) AS cantidad
FROM obligaciones o
LEFT JOIN conceptos c ON c.id = o.concepto_id
WHERE c.id IS NULL;

SELECT 'Pagos con concepto_id inexistente (ERROR)' AS verificacion, COUNT(*) AS cantidad
FROM pagos p
LEFT JOIN conceptos c ON c.id = p.concepto_id
WHERE p.concepto_id IS NOT NULL AND c.id IS NULL;

-- 3. Verificar que las tablas originales siguen intactas
SELECT '=== TABLAS ORIGINALES (deben estar igual) ===' AS seccion;
SELECT 'Clubs' AS tabla, COUNT(*) AS registros FROM clubs;
SELECT 'Deportistas' AS tabla, COUNT(*) AS registros FROM deportistas;
SELECT 'Conversaciones' AS tabla, COUNT(*) AS registros FROM conversaciones;
SELECT 'Pagos (totales)' AS tabla, COUNT(*) AS registros FROM pagos;

-- 4. Verificar saldo de obligaciones
SELECT '=== SALDO POR OBLIGACION (muestra) ===' AS seccion;
SELECT 
    obligacion_id,
    monto_total,
    monto_pagado,
    saldo_pendiente,
    estado_calculado
FROM v_saldo_obligaciones
ORDER BY created_at DESC
LIMIT 10;

-- 5. Verificar distribucion de estados
SELECT '=== DISTRIBUCION DE ESTADOS ===' AS seccion;
SELECT 
    estado_calculado,
    COUNT(*) AS cantidad,
    SUM(monto_total) AS monto_total,
    SUM(saldo_pendiente) AS saldo_pendiente
FROM v_saldo_obligaciones
GROUP BY estado_calculado;

-- 6. Verificar que no haya obligaciones huerfanas despues de la migracion
SELECT '=== INTEGRIDAD FINAL ===' AS seccion;
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'OK: No hay obligaciones huerfanas'
        ELSE 'ERROR: ' || COUNT(*) || ' obligaciones huerfanas'
    END AS verificacion
FROM obligaciones o
LEFT JOIN conceptos c ON c.id = o.concepto_id
LEFT JOIN deportistas d ON d.id = o.deportista_id
LEFT JOIN clubs cl ON cl.id = o.club_id
WHERE c.id IS NULL OR d.id IS NULL OR cl.id IS NULL;
