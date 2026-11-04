-- 0033 · Asistente de elegibilidad, lección 4: el resultado «¿podemos participar?»
-- (docs/Guia_Asistente_Elegibilidad_SICOP.docx; reglas en app/elegibilidad.py).
--
-- * eligibility_item_reviews: la decisión de una persona sobre un requisito que la app no puede comparar sola
--   («revisar»: textos, fechas, cantidades de documentos, mínimos sin dirección). Guarda la respuesta que miró
--   (answer_id): si la respuesta cambia, la decisión deja de valer y el requisito vuelve a «revisar».
-- * eligibility_results: cada resultado calculado es una constancia: resultado, cierre usado, versión de la lista
--   (última generación con IA + huella de los requisitos activos), el detalle por requisito con su respuesta
--   (JSON), la explicación y de dónde salió (ia o app), quién y cuándo.
-- Nada se borra ni se modifica (triggers): recalcular agrega otra constancia y vale la última.

CREATE TABLE eligibility_item_reviews (
    id                   INTEGER PRIMARY KEY,
    session_id           INTEGER NOT NULL REFERENCES eligibility_sessions (id) ON DELETE RESTRICT,
    item_id              INTEGER NOT NULL REFERENCES eligibility_items (id) ON DELETE RESTRICT,
    answer_id            INTEGER NOT NULL REFERENCES eligibility_answers (id) ON DELETE RESTRICT,
    cumple               INTEGER NOT NULL CHECK (cumple IN (0, 1)),
    nota                 TEXT,
    revisado_por         INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    revisado_por_nombre  TEXT NOT NULL CHECK (length(trim(revisado_por_nombre)) > 0),
    creado_en            TEXT NOT NULL
);

CREATE INDEX idx_eligibility_item_reviews ON eligibility_item_reviews (session_id, item_id, id);

CREATE TABLE eligibility_results (
    id                    INTEGER PRIMARY KEY,
    session_id            INTEGER NOT NULL REFERENCES eligibility_sessions (id) ON DELETE RESTRICT,
    nro_sicop             TEXT NOT NULL REFERENCES tenders (nro_sicop),
    resultado             TEXT NOT NULL CHECK (resultado IN ('puede_participar', 'puede_si_completa',
                                                             'no_cumple_excluyente', 'falta_informacion')),
    cierre                TEXT,                    -- AAAA-MM-DD usado para los vencimientos
    lista_generacion_id   INTEGER REFERENCES eligibility_generations (id),
    lista_huella          TEXT NOT NULL CHECK (length(lista_huella) = 64),
    detalle               TEXT NOT NULL,           -- JSON: un objeto por requisito, con su respuesta
    explicacion           TEXT NOT NULL CHECK (length(trim(explicacion)) > 0),
    explicacion_origen    TEXT NOT NULL CHECK (explicacion_origen IN ('ia', 'app')),
    explicacion_motivo    TEXT,                    -- por qué no la redactó la IA (apagada, sin presupuesto…)
    ia_usage_id           INTEGER REFERENCES ia_usage (id),
    calculado_por         INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    calculado_por_nombre  TEXT NOT NULL CHECK (length(trim(calculado_por_nombre)) > 0),
    creado_en             TEXT NOT NULL
);

CREATE INDEX idx_eligibility_results ON eligibility_results (nro_sicop, id);

CREATE TRIGGER eligibility_item_reviews_no_se_borran
BEFORE DELETE ON eligibility_item_reviews
BEGIN
    SELECT RAISE(ABORT, 'Las revisiones del resultado no se borran: revisa de nuevo');
END;

CREATE TRIGGER eligibility_item_reviews_no_se_modifican
BEFORE UPDATE ON eligibility_item_reviews
BEGIN
    SELECT RAISE(ABORT, 'Las revisiones del resultado no se modifican: revisa de nuevo');
END;

CREATE TRIGGER eligibility_results_no_se_borran
BEFORE DELETE ON eligibility_results
BEGIN
    SELECT RAISE(ABORT, 'Las constancias del resultado no se borran: calcula de nuevo');
END;

CREATE TRIGGER eligibility_results_no_se_modifican
BEFORE UPDATE ON eligibility_results
BEGIN
    SELECT RAISE(ABORT, 'Las constancias del resultado no se modifican: calcula de nuevo');
END;
