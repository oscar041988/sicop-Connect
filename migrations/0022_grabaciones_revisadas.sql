-- 0022 · Grabaciones revisadas (lección 4, entrega 4B: bitácora de consultas en el panel).
--
-- * enrich_revisiones: un administrador marcó como revisada la grabación de una consulta con FALLO o CAPTCHA (desde
--   «Bitácora de consultas»). Desde ahí ese video sigue la retención normal (RECORDINGS_KEEP_DAYS); sin revisión se
--   conserva. Una sola vez por consulta (UNIQUE); el nombre se copia, como reviews.responsable.
-- * No se modifica ni se borra (triggers). No toca enrich_consultas.

CREATE TABLE enrich_revisiones (
    id           INTEGER PRIMARY KEY,
    consulta_id  INTEGER NOT NULL UNIQUE REFERENCES enrich_consultas (id),
    user_id      INTEGER NOT NULL REFERENCES users (id),
    nombre       TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    revisada_en  TEXT NOT NULL
);

CREATE TRIGGER revisiones_grabacion_no_se_borran
BEFORE DELETE ON enrich_revisiones
BEGIN
    SELECT RAISE(ABORT, 'Las revisiones de grabaciones no se borran');
END;

CREATE TRIGGER revisiones_grabacion_no_se_modifican
BEFORE UPDATE ON enrich_revisiones
BEGIN
    SELECT RAISE(ABORT, 'Las revisiones de grabaciones no se modifican');
END;
