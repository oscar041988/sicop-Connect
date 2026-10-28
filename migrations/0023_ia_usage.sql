-- 0023 · Registro de uso de la IA (Reporte con IA, lección 2: cliente de OpenAI).
--
-- * ia_usage: una fila por cada llamada a OpenAI, salga bien o mal: para qué fue (prueba o resumen), el cartel,
--   el modelo, los tokens, el costo estimado en USD (vacío si no hay precio configurado), la duración, cuántos
--   intentos hizo y el resultado. Con esto se compara lo que registra la app con el panel de OpenAI.
-- * NUNCA se guarda el texto enviado (el expediente) ni la respuesta del modelo ni la clave: no hay columnas para
--   eso. El motivo de un fallo es solo el tipo de error y su código HTTP (el texto del error puede traer parte de
--   la clave).
-- * «incompleta»: OpenAI respondió pero cortó la respuesta (por ejemplo, llegó a IA_MAX_OUTPUT_TOKENS); los tokens
--   sí se cobran.
-- * No se modifica ni se borra (triggers), como la bitácora del enriquecimiento.

CREATE TABLE ia_usage (
    id              INTEGER PRIMARY KEY,
    creado_en       TEXT NOT NULL,
    proposito       TEXT NOT NULL CHECK (proposito IN ('prueba', 'resumen')),
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
    CHECK (costo_estimado IS NULL OR moneda IS NOT NULL)   -- dinero siempre con moneda
);

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
