-- 0013 · A4: aviso de cierre próximo, resumen semanal y decisiones finales de la revisión.
--
-- * reviews: dos decisiones FINALES nuevas (decisión de Ivania, 2026-10-22): «ofertada» y «no_se_oferta».
--   Mientras la última revisión de un cartel sea «interesa» o «revisar_requisitos», el cartel puede recibir el
--   aviso de cierre próximo; una decisión final lo apaga. El motivo sigue siendo solo de «no_interesa».
-- * notification_outbox, dos motivos nuevos (van en la clave de deduplicación, como los demás):
--   - cierre_proximo: dedup_key = destinatario|Número SICOP|versión|cierre_proximo → una vez por versión.
--   - resumen_semanal: no es de un cartel (nro_sicop vacío); version = la semana ISO («2026-W44»),
--     dedup_key = destinatario|resumen|semana|resumen_semanal → un resumen por destinatario y semana.
-- * Ambas tablas se reconstruyen (SQLite no cambia un CHECK ni un NOT NULL sin hacerlo). Se copian todas las
--   filas con su id; DROP TABLE no dispara los triggers de borrado, que se vuelven a crear igual que antes.

CREATE TABLE reviews_nueva (
    id           INTEGER PRIMARY KEY,
    nro_sicop    TEXT NOT NULL REFERENCES tenders (nro_sicop) ON DELETE RESTRICT,
    user_id      INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    responsable  TEXT NOT NULL CHECK (length(trim(responsable)) > 0),
    decision     TEXT NOT NULL CHECK (decision IN ('interesa', 'no_interesa', 'revisar_requisitos',
                                                   'ofertada', 'no_se_oferta')),
    motivo       TEXT CHECK (motivo IS NULL OR motivo IN ('no_encaja', 'plazo', 'requisitos', 'presupuesto', 'otro')),
    comment      TEXT,
    created_at   TEXT NOT NULL,
    CHECK ((decision = 'no_interesa') = (motivo IS NOT NULL))
);

INSERT INTO reviews_nueva (id, nro_sicop, user_id, responsable, decision, motivo, comment, created_at)
SELECT id, nro_sicop, user_id, responsable, decision, motivo, comment, created_at FROM reviews;

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

CREATE TABLE notification_outbox_nueva (
    id             INTEGER PRIMARY KEY,
    dedup_key      TEXT NOT NULL UNIQUE,
    recipient      TEXT NOT NULL,
    nro_sicop      TEXT REFERENCES tenders (nro_sicop) ON DELETE RESTRICT,  -- vacío solo en el resumen
    version        TEXT NOT NULL,
    motivo         TEXT NOT NULL CHECK (motivo IN ('nueva', 'nueva_version', 'cambio_plazo',
                                                   'cierre_proximo', 'resumen_semanal')),
    cierre         TEXT,
    rules_version  TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'preparado'
                   CHECK (status IN ('preparado', 'aceptado', 'fallido', 'incierto')),
    detalle        TEXT,                      -- respuesta del proveedor o error; nunca credenciales
    created_at     TEXT NOT NULL,
    updated_at     TEXT,
    CHECK ((motivo = 'resumen_semanal') = (nro_sicop IS NULL))
);

INSERT INTO notification_outbox_nueva (id, dedup_key, recipient, nro_sicop, version, motivo, cierre, rules_version,
                                       status, detalle, created_at, updated_at)
SELECT id, dedup_key, recipient, nro_sicop, version, motivo, cierre, rules_version, status, detalle, created_at,
       updated_at
FROM notification_outbox;

DROP TABLE notification_outbox;
ALTER TABLE notification_outbox_nueva RENAME TO notification_outbox;

CREATE INDEX idx_outbox_destinatario ON notification_outbox (recipient, nro_sicop, id);
CREATE INDEX idx_outbox_status ON notification_outbox (status);

CREATE TRIGGER outbox_no_se_borra
BEFORE DELETE ON notification_outbox
BEGIN
    SELECT RAISE(ABORT, 'Los avisos de la outbox no se borran');
END;
