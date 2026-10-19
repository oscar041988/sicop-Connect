-- 0006 · Avisos por correo (lección 7): destinatarios editables y outbox con deduplicación.
--
-- * notification_recipients: a quién le llegan los avisos. Lo edita un administrador desde el panel
--   (pedido de Oscar, 2026-10-12: no fijos en MAIL_TO). No se borra: se desactiva. Cada cambio va al historial.
-- * notification_outbox se reconstruye (en 0001 tenía otros estados y no guardaba versión ni motivo).
--   Una fila = un aviso: un destinatario × una oportunidad × una versión × un motivo.
--   - dedup_key = destinatario|Número SICOP|versión|motivo (UNIQUE): el mismo aviso nunca se prepara dos veces.
--   - version: content_hash del cartel avisado (cambia si SICOP modifica el cartel).
--   - motivo: nueva · nueva_version · cambio_plazo.
--   - cierre: fecha de cierre avisada; si la nueva versión trae otra, el motivo es cambio_plazo.
--   - status: preparado (en la outbox) · aceptado (el proveedor lo recibió) · fallido (el proveedor lo
--     rechazó) · incierto (sin respuesta clara: no se reintenta solo). Aceptado no es «llegó a la bandeja».
--   - Como las revisiones, un aviso no se borra: es la memoria de qué se envió a quién.
--   - recipient es el correo (texto), no una referencia: si se desactiva o se vuelve a agregar a alguien,
--     lo que ya se le avisó sigue contando.

-- La outbox de 0001 nunca se usó. Si tuviera filas, esto falla (CHECK) y la migración no se aplica.
CREATE TABLE _outbox_vacia (filas INTEGER CHECK (filas = 0));
INSERT INTO _outbox_vacia SELECT count(*) FROM notification_outbox;
DROP TABLE _outbox_vacia;
DROP TABLE notification_outbox;

CREATE TABLE notification_recipients (
    id          INTEGER PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nombre      TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    active      INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at  TEXT NOT NULL
);

CREATE TABLE notification_outbox (
    id             INTEGER PRIMARY KEY,
    dedup_key      TEXT NOT NULL UNIQUE,
    recipient      TEXT NOT NULL,
    nro_sicop      TEXT NOT NULL REFERENCES tenders (nro_sicop) ON DELETE RESTRICT,
    version        TEXT NOT NULL,
    motivo         TEXT NOT NULL CHECK (motivo IN ('nueva', 'nueva_version', 'cambio_plazo')),
    cierre         TEXT,
    rules_version  TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'preparado'
                   CHECK (status IN ('preparado', 'aceptado', 'fallido', 'incierto')),
    detalle        TEXT,                      -- respuesta del proveedor o error; nunca credenciales
    created_at     TEXT NOT NULL,
    updated_at     TEXT
);

CREATE INDEX idx_outbox_destinatario ON notification_outbox (recipient, nro_sicop, id);
CREATE INDEX idx_outbox_status ON notification_outbox (status);

CREATE TRIGGER outbox_no_se_borra
BEFORE DELETE ON notification_outbox
BEGIN
    SELECT RAISE(ABORT, 'Los avisos de la outbox no se borran');
END;
