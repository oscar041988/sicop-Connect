-- 0024 · Gestor de documentos, paso 1B: correo al nuevo encargado (docs/GESTOR_DOCUMENTOS.md).
--
-- * notification_outbox, un motivo nuevo: «asignacion». Se prepara al asignar o cambiar el encargado de un cartel
--   en seguimiento y sale con el ciclo diario (8:00), como los demás avisos (decisión de Oscar, 2026-10-26).
--   - recipient = correo del usuario encargado (no tiene que estar en «Destinatarios»).
--   - version = id de la fila de seguimiento_asignaciones (texto): una asignación, un aviso.
--   - dedup_key = encargado|Número SICOP|id de la asignación|asignacion → repetir el ciclo no lo duplica.
-- * La tabla se reconstruye (SQLite no cambia un CHECK sin hacerlo), igual que en la 0013: se copian todas las
--   filas con su id; DROP TABLE no dispara el trigger de borrado, que se vuelve a crear igual que antes.

CREATE TABLE notification_outbox_nueva (
    id             INTEGER PRIMARY KEY,
    dedup_key      TEXT NOT NULL UNIQUE,
    recipient      TEXT NOT NULL,
    nro_sicop      TEXT REFERENCES tenders (nro_sicop) ON DELETE RESTRICT,  -- vacío solo en el resumen
    version        TEXT NOT NULL,
    motivo         TEXT NOT NULL CHECK (motivo IN ('nueva', 'nueva_version', 'cambio_plazo',
                                                   'cierre_proximo', 'resumen_semanal', 'asignacion')),
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
