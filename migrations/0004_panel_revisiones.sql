-- 0004 · Panel web (lección 5): tipo de procedimiento y revisiones humanas con responsable y motivo.
--
-- * tenders.tipo_procedimiento: nombre tal como viene en el reporte 2 («Licitación Reducida», …). Los carteles
--   ya importados se rellenan desde su última copia fiel en raw_snapshots; los nuevos los guarda el importador.
-- * reviews se reconstruye (SQLite no permite quitar un NOT NULL sin hacerlo):
--   - user_id pasa a ser opcional: no hay usuarios hasta la lección 6. Mientras tanto, «responsable» es texto.
--   - decision: interesa · no_interesa · revisar_requisitos.
--   - motivo: obligatorio solo si la decisión es no_interesa (no_encaja · plazo · requisitos · presupuesto · otro).
--     Así, al sugerir términos (lección 13), solo cuentan los descartes por «no encaja».
--   - Una revisión no se borra ni se modifica: una decisión nueva es una fila nueva (historial).
--     La vigente es la última. Está ligada a nro_sicop, que no cambia al reimportar.

ALTER TABLE tenders ADD COLUMN tipo_procedimiento TEXT;

UPDATE tenders SET tipo_procedimiento = (
    SELECT json_extract(s.payload, '$."Tipo de procedimiento"')
    FROM raw_snapshots s
    WHERE s.entity = 'cartel' AND s.natural_key = tenders.nro_sicop
    ORDER BY s.id DESC
    LIMIT 1
);

CREATE INDEX idx_tenders_tipo_procedimiento ON tenders (tipo_procedimiento);

CREATE TABLE reviews_nueva (
    id           INTEGER PRIMARY KEY,
    nro_sicop    TEXT NOT NULL REFERENCES tenders (nro_sicop) ON DELETE RESTRICT,
    user_id      INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    responsable  TEXT NOT NULL CHECK (length(trim(responsable)) > 0),
    decision     TEXT NOT NULL CHECK (decision IN ('interesa', 'no_interesa', 'revisar_requisitos')),
    motivo       TEXT CHECK (motivo IS NULL OR motivo IN ('no_encaja', 'plazo', 'requisitos', 'presupuesto', 'otro')),
    comment      TEXT,
    created_at   TEXT NOT NULL,
    CHECK ((decision = 'no_interesa') = (motivo IS NOT NULL))
);

-- Si ya hubiera revisiones (hoy no hay), se copian; una decisión fuera de la lista hace fallar la migración
-- completa en vez de perder datos.
INSERT INTO reviews_nueva (id, nro_sicop, user_id, responsable, decision, motivo, comment, created_at)
SELECT r.id, r.nro_sicop, r.user_id, coalesce(u.nombre, u.email), r.decision, NULL, r.comment, r.created_at
FROM reviews r LEFT JOIN users u ON u.id = r.user_id;

-- DROP TABLE no dispara el trigger de borrado de filas.
DROP TABLE reviews;
ALTER TABLE reviews_nueva RENAME TO reviews;

CREATE INDEX idx_reviews_nro_sicop ON reviews (nro_sicop, id);

CREATE TRIGGER reviews_no_se_borran
BEFORE DELETE ON reviews
BEGIN
    SELECT RAISE(ABORT, 'Las revisiones humanas no se borran');
END;

CREATE TRIGGER reviews_no_se_modifican
BEFORE UPDATE ON reviews
BEGIN
    SELECT RAISE(ABORT, 'Las revisiones humanas no se modifican: registra una revisión nueva');
END;
