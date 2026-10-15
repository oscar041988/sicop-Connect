-- 0003 · Evaluación de oportunidades (comando evaluate; guía, sección 16.4).
--
-- Cada fila: un cartel × una familia × una versión de reglas (UNIQUE de 0001). Dimensiones separadas:
-- * encaje (columna de 0001): alta · media · baja · sin_coincidencia. Es la prioridad comercial.
-- * plazo_estado: abierto · cierra_7_dias · vencido · por_verificar (según fecha de cierre).
-- * calidad_datos: completo · sin_lineas · codigo_sin_catalogo · archivo_parcial.
-- * regla: términos del YAML que decidieron; evidencia (de 0001): frases exactas del texto original.
-- * prioridad (de 0001) queda sin usar por ahora: se reserva para combinar encaje y plazo.
-- La versión de reglas es la huella SHA-256 (12 caracteres) de config/hermatix_rules.yaml.
-- Los requisitos («viabilidad pendiente / revisado») son decisión humana: van en reviews.

ALTER TABLE opportunity_assessments ADD COLUMN producto TEXT;
ALTER TABLE opportunity_assessments ADD COLUMN regla TEXT;
ALTER TABLE opportunity_assessments ADD COLUMN plazo_estado TEXT
    CHECK (plazo_estado IS NULL OR plazo_estado IN ('abierto', 'cierra_7_dias', 'vencido', 'por_verificar'));
ALTER TABLE opportunity_assessments ADD COLUMN calidad_datos TEXT
    CHECK (calidad_datos IS NULL OR calidad_datos IN ('completo', 'sin_lineas', 'codigo_sin_catalogo', 'archivo_parcial'));

CREATE INDEX idx_assessments_encaje ON opportunity_assessments (rules_version, encaje);
