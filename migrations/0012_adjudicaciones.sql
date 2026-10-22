-- 0012 · Adjudicaciones en firme (reportes 6, 6.1 y 6.2): base del módulo de competencia.
--
-- Encabezados reales del 2026-10-22 en docs/MAPEO_DATOS.md. Lo que el archivo trae y lo que no:
-- * El adjudicatario viene SOLO como cédula («Cédula Empresa Proveedora»), sin nombre. El nombre lo pone
--   Hermatix en config/competidores.yaml; una cédula sin nombre se muestra como cédula.
-- * Las líneas adjudicadas no traen descripción: la familia sale del cartel (tenders), evaluado con las
--   mismas reglas que las oportunidades.
-- * En el reporte 6 un mismo cartel tiene varias filas (una por cada acto en firme, con su hora), y en
--   el 6.2 hay líneas con más de un registro distinto (cambia el tipo de cambio, a veces la moneda o la
--   cantidad). Se guarda cada registro distinto una vez (content_hash = el de raw_snapshots, así cada
--   cifra se rastrea hasta la fila original); los que chocan no se suman (ver app/competencia.py).
-- * Dinero como texto Decimal exacto y siempre con su moneda; nunca se convierte con el tipo de cambio.

CREATE TABLE adjudicaciones (
    id                     INTEGER PRIMARY KEY,
    nro_sicop              TEXT NOT NULL,
    nro_procedimiento      TEXT,
    fecha_comunicacion     TEXT,
    fecha_adj_firme        TEXT,
    permite_recursos       TEXT,
    fecha_maxima_recursos  TEXT,
    desierto               TEXT,
    content_hash           TEXT NOT NULL UNIQUE,
    first_import_id        INTEGER REFERENCES imports (id),
    first_seen             TEXT NOT NULL,
    last_seen              TEXT NOT NULL
);

CREATE INDEX idx_adjudicaciones_nro_sicop ON adjudicaciones (nro_sicop);

CREATE TABLE adjudicacion_proveedores (
    id                 INTEGER PRIMARY KEY,
    nro_sicop          TEXT NOT NULL,
    nro_procedimiento  TEXT,
    cedula_proveedor   TEXT NOT NULL,
    content_hash       TEXT NOT NULL,
    first_import_id    INTEGER REFERENCES imports (id),
    first_seen         TEXT NOT NULL,
    last_seen          TEXT NOT NULL,
    UNIQUE (nro_sicop, cedula_proveedor)
);

CREATE INDEX idx_adjudicacion_proveedores_cedula ON adjudicacion_proveedores (cedula_proveedor);

CREATE TABLE adjudicacion_lineas (
    id                   INTEGER PRIMARY KEY,
    nro_sicop            TEXT NOT NULL,
    numero_linea         TEXT NOT NULL,
    cedula_proveedor     TEXT NOT NULL,
    cantidad             TEXT NOT NULL,
    precio_unitario      TEXT NOT NULL,
    moneda               TEXT NOT NULL CHECK (length(moneda) = 3 AND moneda = upper(moneda)),
    descuento            TEXT,
    iva                  TEXT,
    otros_impuestos      TEXT,
    acarreos             TEXT,
    tipo_cambio_crc      TEXT,
    monto_sin_impuestos  TEXT NOT NULL,  -- cantidad × precio unitario − descuento, en la moneda de la línea
    content_hash         TEXT NOT NULL UNIQUE,
    first_import_id      INTEGER REFERENCES imports (id),
    first_seen           TEXT NOT NULL,
    last_seen            TEXT NOT NULL
);

CREATE INDEX idx_adjudicacion_lineas_clave ON adjudicacion_lineas (nro_sicop, numero_linea, cedula_proveedor);
CREATE INDEX idx_adjudicacion_lineas_cedula ON adjudicacion_lineas (cedula_proveedor);
