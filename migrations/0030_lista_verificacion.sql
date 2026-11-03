-- 0030 · Asistente de elegibilidad, lección 2: lista de verificación del cartel
-- (docs/Guia_Asistente_Elegibilidad_SICOP.docx; IA aprobada en docs/DECISION_IA.md §7).
--
-- * eligibility_items: la lista vigente de cada cartel, un requisito por fila, convertido en algo verificable:
--   qué tipo de respuesta lo prueba (tipo_evidencia), cuál es el mínimo («no indicado» si el pliego no lo dice),
--   si es excluyente y sus citas. «clave» es el texto normalizado del requerimiento de origen: al volver a generar,
--   la app reconoce el mismo requisito y NO toca lo que corrigió, agregó o quitó una persona.
--   Quitar = activo 0 (no se borra). Cada corrección queda en audit_log.
-- * eligibility_generations: cada vez que se generó la lista con IA (resumen usado, modelo, prompt, costo en
--   ia_usage, resultado).
-- * ia_usage: el CHECK de «proposito» acepta también 'verificacion' (esta lección), 'asistente' (lección 3) y
--   'explicacion' (lección 4). SQLite no cambia un CHECK sin reconstruir la tabla: se copian todas las filas con su
--   id. ia_summaries apunta a ia_usage: por eso esta migración corre con las llaves foráneas apagadas (línea de abajo,
--   app/database.py) y antes de confirmarse se revisan todas con PRAGMA foreign_key_check: los ids son los mismos,
--   así que ninguna queda rota. DROP TABLE no dispara el trigger de borrado; los triggers se vuelven a crear igual.
--
-- migracion: sin llaves foraneas

CREATE TABLE ia_usage_nueva (
    id              INTEGER PRIMARY KEY,
    creado_en       TEXT NOT NULL,
    proposito       TEXT NOT NULL CHECK (proposito IN ('prueba', 'resumen', 'verificacion', 'asistente',
                                                       'explicacion')),
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

CREATE TABLE eligibility_generations (
    id                 INTEGER PRIMARY KEY,
    nro_sicop          TEXT NOT NULL REFERENCES tenders (nro_sicop),
    ia_summary_id      INTEGER REFERENCES ia_summaries (id),
    ia_usage_id        INTEGER REFERENCES ia_usage (id),
    huella             TEXT,                -- del expediente que leyó la IA: las citas se enlazan solo si no cambió
    prompt_version     TEXT NOT NULL,
    modelo             TEXT,
    estado             TEXT NOT NULL CHECK (estado IN ('ok', 'fallido')),
    motivo             TEXT,
    items              INTEGER NOT NULL DEFAULT 0 CHECK (items >= 0),
    generado_por       INTEGER REFERENCES users (id),
    generado_por_nombre TEXT NOT NULL,
    creado_en          TEXT NOT NULL
);

CREATE INDEX idx_eligibility_generations ON eligibility_generations (nro_sicop, id);

CREATE TRIGGER eligibility_generations_no_se_borran
BEFORE DELETE ON eligibility_generations
BEGIN
    SELECT RAISE(ABORT, 'El registro de generaciones de la lista no se borra');
END;

CREATE TABLE eligibility_items (
    id                 INTEGER PRIMARY KEY,
    nro_sicop          TEXT NOT NULL REFERENCES tenders (nro_sicop),
    orden              INTEGER NOT NULL,
    clave              TEXT NOT NULL CHECK (length(clave) > 0),
    requisito          TEXT NOT NULL CHECK (length(trim(requisito)) > 0),
    tipo               TEXT NOT NULL CHECK (tipo IN ('tecnico', 'legal', 'financiero', 'experiencia')),
    tipo_evidencia     TEXT NOT NULL CHECK (tipo_evidencia IN ('numero', 'si_no', 'fecha', 'documento', 'texto')),
    minimo             TEXT NOT NULL,                -- el mínimo en palabras, o «no indicado»
    minimo_numero      TEXT,                         -- número exacto como texto decimal («3»), si aplica
    minimo_fecha       TEXT,                         -- AAAA-MM-DD, si aplica
    unidad             TEXT,
    excluyente         INTEGER NOT NULL CHECK (excluyente IN (0, 1)),
    citas              TEXT NOT NULL DEFAULT '[]',   -- JSON: ["[DOC 1 · pág. 3]", …]
    perfil_item_id     INTEGER REFERENCES company_profile_items (id),
    perfil_confirmado  INTEGER NOT NULL DEFAULT 0 CHECK (perfil_confirmado IN (0, 1)),
    origen             TEXT NOT NULL CHECK (origen IN ('ia', 'usuario')),
    editado            INTEGER NOT NULL DEFAULT 0 CHECK (editado IN (0, 1)),
    activo             INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    generacion_id      INTEGER REFERENCES eligibility_generations (id),
    editado_por_nombre TEXT,
    editado_en         TEXT,
    creado_en          TEXT NOT NULL,
    UNIQUE (nro_sicop, clave)
);

CREATE INDEX idx_eligibility_items ON eligibility_items (nro_sicop, activo, orden);

CREATE TRIGGER eligibility_items_no_se_borran
BEFORE DELETE ON eligibility_items
BEGIN
    SELECT RAISE(ABORT, 'Los ítems de la lista no se borran: se quitan (activo = 0)');
END;
