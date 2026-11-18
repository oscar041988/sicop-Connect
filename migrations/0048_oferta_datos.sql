-- 0048 · El asistente pide lo que le falta a la oferta (pedido de Ivania, 2026-11-18; docs/DECISION_PROPUESTA.md §9).
--
-- * oferta_precios: el precio de UN cartel, escrito por una persona en el asistente (la IA no pone ni cambia
--   precios: DECISION_IA.md regla 3). Manda sobre config/tarifario.yaml solo para ese cartel; el tarifario no cambia.
--   Montos como TEXTO (Decimal), con su moneda.
-- * oferta_fichas: el producto que se oferta y su ficha técnica en PDF (anexo 3), por cartel.
-- * oferta_pliegos / oferta_pliego_texto: un pliego subido por una persona cuando el enriquecimiento no trajo uno con
--   texto. Es aparte de tender_documents (lo que vino de SICOP): así nunca se confunde lo subido con lo descargado.
-- * representante_legal: nombre, cédula y calidades de quien firma. Uno para todas las ofertas; lo llena un
--   administrador. Nunca va a la IA. Manda sobre config/oferta.yaml.
-- * Vale la fila más nueva de cada uno; nada se borra ni se modifica (triggers): cambiar es agregar una fila.

CREATE TABLE oferta_precios (
    id                  INTEGER PRIMARY KEY,
    nro_sicop           TEXT NOT NULL REFERENCES tenders (nro_sicop),
    moneda              TEXT NOT NULL CHECK (moneda IN ('CRC', 'USD')),
    precio              TEXT NOT NULL,                        -- precio por unidad (Decimal como texto)
    periodo             TEXT NOT NULL CHECK (periodo IN ('mensual', 'unico')),
    iva                 TEXT NOT NULL,                        -- «13» o «exento: <motivo>»
    desglose_json       TEXT NOT NULL,                        -- los cuatro porcentajes del reajuste (suman 100)
    creado_por          INTEGER REFERENCES users (id),
    creado_por_nombre   TEXT NOT NULL,
    creado_en           TEXT NOT NULL
);
CREATE INDEX idx_oferta_precios ON oferta_precios (nro_sicop, id);

CREATE TABLE oferta_fichas (
    id                  INTEGER PRIMARY KEY,
    nro_sicop           TEXT NOT NULL REFERENCES tenders (nro_sicop),
    producto            TEXT NOT NULL,                        -- clave de config/hermatix_rules.yaml
    nombre_archivo      TEXT NOT NULL,                        -- el que mandó el navegador, solo para mostrar
    ruta                TEXT NOT NULL,                        -- relativa a ASSISTANT_DOCS_DIR
    sha256              TEXT NOT NULL,
    tamano              INTEGER NOT NULL,
    creado_por          INTEGER REFERENCES users (id),
    creado_por_nombre   TEXT NOT NULL,
    creado_en           TEXT NOT NULL
);
CREATE INDEX idx_oferta_fichas ON oferta_fichas (nro_sicop, id);

CREATE TABLE oferta_pliegos (
    id                  INTEGER PRIMARY KEY,
    nro_sicop           TEXT NOT NULL REFERENCES tenders (nro_sicop),
    nombre_archivo      TEXT NOT NULL,
    ruta                TEXT NOT NULL,
    sha256              TEXT NOT NULL,
    tamano              INTEGER NOT NULL,
    paginas             INTEGER NOT NULL CHECK (paginas >= 1),
    creado_por          INTEGER REFERENCES users (id),
    creado_por_nombre   TEXT NOT NULL,
    creado_en           TEXT NOT NULL
);
CREATE INDEX idx_oferta_pliegos ON oferta_pliegos (nro_sicop, id);

CREATE TABLE oferta_pliego_texto (
    id                  INTEGER PRIMARY KEY,
    pliego_id           INTEGER NOT NULL REFERENCES oferta_pliegos (id),
    pagina              INTEGER NOT NULL CHECK (pagina >= 1),
    texto               TEXT NOT NULL,
    UNIQUE (pliego_id, pagina)
);

CREATE TABLE representante_legal (
    id                  INTEGER PRIMARY KEY,
    nombre              TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    cedula              TEXT NOT NULL CHECK (length(trim(cedula)) > 0),   -- texto: guiones y ceros iniciales
    calidades           TEXT NOT NULL DEFAULT '',
    cargo               TEXT NOT NULL DEFAULT 'representante legal',
    creado_por          INTEGER REFERENCES users (id),
    creado_por_nombre   TEXT NOT NULL,
    creado_en           TEXT NOT NULL
);

CREATE TRIGGER oferta_precios_no_se_borran BEFORE DELETE ON oferta_precios
BEGIN SELECT RAISE(ABORT, 'Los precios del cartel no se borran'); END;
CREATE TRIGGER oferta_precios_no_se_modifican BEFORE UPDATE ON oferta_precios
BEGIN SELECT RAISE(ABORT, 'Los precios del cartel no se modifican: cambiar es agregar uno nuevo'); END;

CREATE TRIGGER oferta_fichas_no_se_borran BEFORE DELETE ON oferta_fichas
BEGIN SELECT RAISE(ABORT, 'Las fichas técnicas no se borran'); END;
CREATE TRIGGER oferta_fichas_no_se_modifican BEFORE UPDATE ON oferta_fichas
BEGIN SELECT RAISE(ABORT, 'Las fichas técnicas no se modifican: cambiar es agregar una nueva'); END;

CREATE TRIGGER oferta_pliegos_no_se_borran BEFORE DELETE ON oferta_pliegos
BEGIN SELECT RAISE(ABORT, 'Los pliegos subidos no se borran'); END;
CREATE TRIGGER oferta_pliegos_no_se_modifican BEFORE UPDATE ON oferta_pliegos
BEGIN SELECT RAISE(ABORT, 'Los pliegos subidos no se modifican'); END;

CREATE TRIGGER oferta_pliego_texto_no_se_borra BEFORE DELETE ON oferta_pliego_texto
BEGIN SELECT RAISE(ABORT, 'El texto del pliego subido no se borra'); END;
CREATE TRIGGER oferta_pliego_texto_no_se_modifica BEFORE UPDATE ON oferta_pliego_texto
BEGIN SELECT RAISE(ABORT, 'El texto del pliego subido no se modifica'); END;

CREATE TRIGGER representante_no_se_borra BEFORE DELETE ON representante_legal
BEGIN SELECT RAISE(ABORT, 'Los datos del representante no se borran'); END;
CREATE TRIGGER representante_no_se_modifica BEFORE UPDATE ON representante_legal
BEGIN SELECT RAISE(ABORT, 'Los datos del representante no se modifican: cambiar es agregar unos nuevos'); END;
