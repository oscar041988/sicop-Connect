-- 0001 · Esquema inicial: tablas internas mínimas de la guía (sección 16.3).
--
-- Reglas:
-- * Identificadores SICOP como TEXT (conservan ceros iniciales; 8/11/16/24 dígitos).
-- * Dinero como TEXT decimal exacto («1234.50») y siempre con su moneda (código de 3 letras).
-- * Fechas como TEXT ISO 8601 con zona («2026-10-07T08:51:00-06:00»).
-- * Claves únicas impiden duplicados; las revisiones humanas no se borran.
-- * Solo columnas ya decididas en docs/MAPEO_DATOS.md (las marcadas «después» no están).
--
-- Una migración aplicada no se edita: los cambios van en un archivo nuevo (0002_...).
-- No usar BEGIN/COMMIT aquí: el comando migrate envuelve cada archivo en una transacción.

-- Obtención y trazabilidad -------------------------------------------------------

CREATE TABLE source_runs (
    id            INTEGER PRIMARY KEY,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    mode          TEXT NOT NULL CHECK (mode IN ('manual', 'asistido', 'auto')),
    data_origin   TEXT NOT NULL CHECK (data_origin IN ('real', 'sintetico', 'simulado')),
    filters       TEXT,
    period_from   TEXT,
    period_to     TEXT,
    status        TEXT NOT NULL CHECK (status IN ('en_curso', 'ok', 'fallo')),
    error         TEXT
);

CREATE TABLE imports (
    id             INTEGER PRIMARY KEY,
    source_run_id  INTEGER REFERENCES source_runs (id),
    report         TEXT NOT NULL,
    file_name      TEXT NOT NULL,
    file_hash      TEXT NOT NULL UNIQUE,  -- el mismo archivo no se importa dos veces
    data_origin    TEXT NOT NULL CHECK (data_origin IN ('real', 'sintetico', 'simulado')),
    rows_accepted  INTEGER NOT NULL DEFAULT 0 CHECK (rows_accepted >= 0),
    rows_rejected  INTEGER NOT NULL DEFAULT 0 CHECK (rows_rejected >= 0),
    imported_at    TEXT NOT NULL
);

-- Copia fiel de cada fila recibida. Si una fila no cambió, no se guarda otra vez.
CREATE TABLE raw_snapshots (
    id            INTEGER PRIMARY KEY,
    import_id     INTEGER NOT NULL REFERENCES imports (id),
    entity        TEXT NOT NULL,          -- p. ej. 'cartel', 'linea'
    natural_key   TEXT NOT NULL,          -- p. ej. Número SICOP, o «Número SICOP|línea»
    content_hash  TEXT NOT NULL,          -- SHA-256 de la fila original
    payload       TEXT NOT NULL,          -- fila original tal como llegó
    captured_at   TEXT NOT NULL,
    UNIQUE (entity, natural_key, content_hash)
);

-- Datos de SICOP normalizados -------------------------------------------------------

CREATE TABLE institutions (
    cedula      TEXT PRIMARY KEY,
    nombre      TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL
);

CREATE TABLE catalog_items (
    codigo_identificacion  TEXT PRIMARY KEY,  -- 16 dígitos
    codigo_clasificacion   TEXT,              -- 8 dígitos (UNSPSC)
    nombre                 TEXT,
    first_seen             TEXT NOT NULL,
    last_seen              TEXT NOT NULL
);

CREATE TABLE tenders (
    nro_sicop               TEXT PRIMARY KEY,
    nro_seq_sicop           TEXT,             -- si SICOP lo entrega (hoy no viene)
    nro_procedimiento       TEXT,
    -- Sin clave foránea a institutions: el reporte 11 aún no se descarga (ver MAPEO_DATOS.md).
    institution_cedula      TEXT,
    descripcion             TEXT,             -- texto original, sin normalizar
    fecha_publicacion       TEXT,
    fecha_inicio_recepcion  TEXT,
    fecha_cierre_recepcion  TEXT,
    content_hash            TEXT NOT NULL,
    first_import_id         INTEGER REFERENCES imports (id),
    last_import_id          INTEGER REFERENCES imports (id),
    first_seen              TEXT NOT NULL,
    last_seen               TEXT NOT NULL
);

CREATE INDEX idx_tenders_nro_procedimiento ON tenders (nro_procedimiento);
CREATE INDEX idx_tenders_cierre ON tenders (fecha_cierre_recepcion);

CREATE TABLE tender_lines (
    id                        INTEGER PRIMARY KEY,
    nro_sicop                 TEXT NOT NULL REFERENCES tenders (nro_sicop),
    numero_linea              TEXT NOT NULL,
    numero_partida            TEXT,
    -- Sin clave foránea a catalog_items: el reporte 10.2 aún no se descarga.
    codigo_identificacion     TEXT,
    cantidad_solicitada       TEXT,
    precio_unitario_estimado  TEXT,
    moneda                    TEXT CHECK (moneda IS NULL OR (length(moneda) = 3 AND moneda = upper(moneda))),
    content_hash              TEXT NOT NULL,
    first_seen                TEXT NOT NULL,
    last_seen                 TEXT NOT NULL,
    UNIQUE (nro_sicop, numero_linea),
    CHECK (precio_unitario_estimado IS NULL OR moneda IS NOT NULL)  -- dinero siempre con moneda
);

CREATE INDEX idx_tender_lines_codigo ON tender_lines (codigo_identificacion);

-- Evaluación, revisión y avisos ------------------------------------------------------

CREATE TABLE opportunity_assessments (
    id             INTEGER PRIMARY KEY,
    nro_sicop      TEXT NOT NULL REFERENCES tenders (nro_sicop),
    familia        TEXT NOT NULL,
    encaje         TEXT NOT NULL,
    prioridad      TEXT,
    evidencia      TEXT NOT NULL,             -- señales encontradas (regla y texto que coincidió)
    rules_version  TEXT NOT NULL,
    evaluated_at   TEXT NOT NULL,
    UNIQUE (nro_sicop, familia, rules_version)
);

CREATE TABLE users (
    id             INTEGER PRIMARY KEY,
    email          TEXT NOT NULL UNIQUE COLLATE NOCASE,
    nombre         TEXT,
    role           TEXT NOT NULL CHECK (role IN ('admin', 'encargado')),
    password_hash  TEXT NOT NULL,
    active         INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at     TEXT NOT NULL
);

-- Decisión humana: nunca se borra (ni directamente ni al actualizar carteles).
CREATE TABLE reviews (
    id          INTEGER PRIMARY KEY,
    nro_sicop   TEXT NOT NULL REFERENCES tenders (nro_sicop) ON DELETE RESTRICT,
    user_id     INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    decision    TEXT NOT NULL,
    comment     TEXT,
    created_at  TEXT NOT NULL
);

CREATE INDEX idx_reviews_nro_sicop ON reviews (nro_sicop);

CREATE TRIGGER reviews_no_se_borran
BEFORE DELETE ON reviews
BEGIN
    SELECT RAISE(ABORT, 'Las revisiones humanas no se borran');
END;

CREATE TABLE notification_outbox (
    id             INTEGER PRIMARY KEY,
    nro_sicop      TEXT NOT NULL REFERENCES tenders (nro_sicop),
    assessment_id  INTEGER REFERENCES opportunity_assessments (id),
    recipient      TEXT NOT NULL,
    dedup_key      TEXT NOT NULL UNIQUE,      -- el mismo aviso no se envía dos veces
    status         TEXT NOT NULL DEFAULT 'pendiente' CHECK (status IN ('pendiente', 'enviado', 'error')),
    error          TEXT,
    created_at     TEXT NOT NULL,
    sent_at        TEXT
);
