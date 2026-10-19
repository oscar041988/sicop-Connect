-- 0007 · Ciclo completo (lección 8): run-cycle registra cada ejecución en source_runs con su cobertura.
--
-- * kind: 'import' (una importación suelta, desde la CLI o el panel, como hasta ahora) o 'ciclo' (run-cycle).
--   Las filas que ya existen son importaciones sueltas.
-- * coverage: JSON legible con qué archivos vio el ciclo y qué pasó con cada uno (importado, ya importado,
--   con error, en espera), más el resumen de la evaluación y de los avisos. Así un fallo de la fuente queda
--   escrito y nunca se confunde con «cero oportunidades».
-- * Las importaciones de un ciclo apuntan a la fila del ciclo (imports.source_run_id).

ALTER TABLE source_runs ADD COLUMN kind TEXT NOT NULL DEFAULT 'import' CHECK (kind IN ('import', 'ciclo'));
ALTER TABLE source_runs ADD COLUMN coverage TEXT;
