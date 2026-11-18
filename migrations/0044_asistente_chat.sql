-- 0044 · El asistente de elegibilidad como chat (DECISION_IA.md §10, aprobado por Oscar el 2026-11-11; paso 3 de
-- §10.7).
--
-- * ia_usage: el CHECK de «proposito» acepta también 'chat' (cada mensaje que la IA contesta en el chat). Igual que en
--   la 0043: SQLite no cambia un CHECK sin reconstruir la tabla; se copian todas las filas con su id, con las llaves
--   foráneas apagadas, y se revisan con PRAGMA foreign_key_check antes de confirmar. Los triggers se vuelven a crear.
-- * asistente_chat: los mensajes del chat de un cartel, en orden. «persona» es lo que escribió quien usa el asistente;
--   «asistente», lo que contestó la IA; «app», lo que dice la app (lo que se guardó, la pregunta siguiente, avisos).
--   Las respuestas a los requisitos se siguen guardando en eligibility_answers (la app las valida); aquí solo queda
--   la conversación. Los mensajes no se borran ni se modifican. Tapar los datos personales al terminar la oferta
--   (§10.4) es el paso 5 y tendrá su propia migración.
--
-- migracion: sin llaves foraneas

CREATE TABLE ia_usage_nueva (
    id              INTEGER PRIMARY KEY,
    creado_en       TEXT NOT NULL,
    proposito       TEXT NOT NULL CHECK (proposito IN ('prueba', 'resumen', 'verificacion', 'asistente',
                                                       'explicacion', 'oferta', 'chat')),
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

CREATE TABLE asistente_chat (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES eligibility_sessions (id),
    rol             TEXT NOT NULL CHECK (rol IN ('persona', 'asistente', 'app')),
    texto           TEXT NOT NULL CHECK (length(texto) BETWEEN 1 AND 6000),
    archivo_nombre  TEXT,                                   -- el archivo que la persona subió con su mensaje
    autor_id        INTEGER REFERENCES users (id),          -- quien escribió (solo en «persona»)
    autor_nombre    TEXT,
    ia_usage_id     INTEGER REFERENCES ia_usage (id),       -- la llamada que produjo el mensaje («asistente»)
    creado_en       TEXT NOT NULL
);

CREATE INDEX idx_asistente_chat ON asistente_chat (session_id, id);

CREATE TRIGGER asistente_chat_no_se_borra
BEFORE DELETE ON asistente_chat
BEGIN
    SELECT RAISE(ABORT, 'Los mensajes del chat no se borran');
END;

CREATE TRIGGER asistente_chat_no_se_modifica
BEFORE UPDATE ON asistente_chat
BEGIN
    SELECT RAISE(ABORT, 'Los mensajes del chat no se modifican');
END;
