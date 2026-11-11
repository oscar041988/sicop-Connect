-- 0043 · Oferta completa con un botón (pedido de Oscar, comunicado por Ivania el 2026-11-10; DECISION_IA.md §9).
--
-- La oferta sale como la de NAVSAT: portada, el pliego copiado sección por sección con «Respuesta Sección NN»,
-- listado de anexos, oferta económica y los documentos del asistente adjuntos (app/propuesta.py).
--
-- * ia_usage: el CHECK de «proposito» acepta también 'oferta' (la IA marca dónde empieza cada sección del pliego).
--   SQLite no cambia un CHECK sin reconstruir la tabla: se copian todas las filas con su id. Otras tablas apuntan a
--   ia_usage: por eso esta migración corre con las llaves foráneas apagadas (línea de abajo, app/database.py) y antes
--   de confirmarse se revisan con PRAGMA foreign_key_check; los ids son los mismos. Los triggers se vuelven a crear.
-- * oferta_secciones_ia: las secciones que marcó la IA para un pliego (huella del texto + versión del prompt). Volver
--   a presionar «Oferta» con el mismo pliego no gasta IA. Solo guarda títulos y páginas del pliego (público), nunca
--   precios ni documentos de Hermatix.
--
-- migracion: sin llaves foraneas

CREATE TABLE ia_usage_nueva (
    id              INTEGER PRIMARY KEY,
    creado_en       TEXT NOT NULL,
    proposito       TEXT NOT NULL CHECK (proposito IN ('prueba', 'resumen', 'verificacion', 'asistente',
                                                       'explicacion', 'oferta')),
    nro_sicop       TEXT REFERENCES tenders (nro_sicop),
    modelo          TEXT NOT NULL,
    tokens_entrada  INTEGER CHECK (tokens_entrada IS NULL OR tokens_entrada >= 0),
    tokens_salida   INTEGER CHECK (tokens_salida IS NULL OR tokens_salida >= 0),
    costo_estimado  TEXT,
    moneda          TEXT CHECK (moneda IS NULL OR moneda = 'USD'),
    duracion_s      REAL NOT NULL CHECK (duracion_s >= 0),
    intentos        INTEGER NOT NULL CHECK (intentos BETWEEN 1 AND 3),
    resultado       TEXT NOT NULL CHECK (resultado IN ('ok', 'incompleta', 'fallo')),
    motivo          TEXT,
    CHECK (costo_estimado IS NULL OR moneda IS NOT NULL)
);

INSERT INTO ia_usage_nueva (id, creado_en, proposito, nro_sicop, modelo, tokens_entrada, tokens_salida,
                            costo_estimado, moneda, duracion_s, intentos, resultado, motivo)
SELECT id, creado_en, proposito, nro_sicop, modelo, tokens_entrada, tokens_salida, costo_estimado, moneda,
       duracion_s, intentos, resultado, motivo
FROM ia_usage;

DROP TABLE ia_usage;
ALTER TABLE ia_usage_nueva RENAME TO ia_usage;

CREATE INDEX idx_ia_usage_creado ON ia_usage (creado_en);

CREATE TRIGGER ia_usage_no_se_borra
BEFORE DELETE ON ia_usage
BEGIN
    SELECT RAISE(ABORT, 'El registro de uso de la IA no se borra');
END;

CREATE TRIGGER ia_usage_no_se_modifica
BEFORE UPDATE ON ia_usage
BEGIN
    SELECT RAISE(ABORT, 'El registro de uso de la IA no se modifica');
END;

CREATE TABLE oferta_secciones_ia (
    id              INTEGER PRIMARY KEY,
    nro_sicop       TEXT NOT NULL REFERENCES tenders (nro_sicop),
    huella          TEXT NOT NULL CHECK (length(huella) = 64),   -- SHA-256 del texto del pliego que leyó la IA
    prompt_version  TEXT NOT NULL,
    ia_usage_id     INTEGER REFERENCES ia_usage (id),
    secciones_json  TEXT NOT NULL,
    creado_en       TEXT NOT NULL
);

CREATE INDEX idx_oferta_secciones_ia ON oferta_secciones_ia (nro_sicop, huella, prompt_version, id);
