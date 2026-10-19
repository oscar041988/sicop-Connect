-- 0002 · Líneas, catálogo e instituciones: lo que necesitan sus importadores y sus relaciones.
--
-- * tender_lines.estimado_linea: cantidad × precio unitario, calculado en Python con Decimal y
--   guardado como texto exacto. Va siempre en la moneda de la línea: es una estimación por línea,
--   no el presupuesto ni el monto adjudicado.
-- * content_hash en catálogo e instituciones: detecta si una fila cambió entre importaciones.
-- * Sin claves foráneas nuevas: el catálogo se descarga por clasificación (no está completo) y
--   SQLite no permite agregarlas sin reconstruir la tabla. La relación se consulta con JOIN y los
--   códigos que no unen quedan marcados en la vista v_tender_lines.

ALTER TABLE tender_lines ADD COLUMN estimado_linea TEXT;
ALTER TABLE catalog_items ADD COLUMN content_hash TEXT;
ALTER TABLE institutions ADD COLUMN content_hash TEXT;

CREATE INDEX idx_tenders_institution ON tenders (institution_cedula);
CREATE INDEX idx_catalog_items_clasificacion ON catalog_items (codigo_clasificacion);

-- Cada línea con su nombre de catálogo y el estado de la unión:
-- * 'en_catalogo': el código está en catalog_items.
-- * 'clasificacion_no_descargada': no se ha importado el catálogo de esa clasificación (8 primeros dígitos).
-- * 'codigo_no_esta_en_catalogo': la clasificación sí se importó, pero el código no aparece en ella.
CREATE VIEW v_tender_lines AS
SELECT
    l.*,
    c.nombre AS nombre_catalogo,
    CASE
        WHEN c.codigo_identificacion IS NOT NULL THEN 'en_catalogo'
        WHEN EXISTS (SELECT 1 FROM catalog_items k
                     WHERE k.codigo_clasificacion = substr(l.codigo_identificacion, 1, 8))
            THEN 'codigo_no_esta_en_catalogo'
        ELSE 'clasificacion_no_descargada'
    END AS estado_catalogo
FROM tender_lines l
LEFT JOIN catalog_items c ON c.codigo_identificacion = l.codigo_identificacion;
