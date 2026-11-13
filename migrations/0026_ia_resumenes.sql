-- 0026 · Resumen ejecutivo de un cartel con IA (Reporte con IA, lección 3).
--
-- * ia_summaries: un resumen pedido al modelo para el expediente de un cartel, con la versión del prompt, el modelo,
--   la huella (SHA-256) del expediente, el resumen en JSON (salida estructurada), su estado y su costo.
-- * Estados: ok · revisar (alguna fecha, monto o cantidad no coincide con SICOP; las diferencias van en
--   diferencias_json) · fallido (rechazo, respuesta incompleta o error: sin resumen, con su motivo).
-- * Misma huella y misma versión del prompt con un resumen ok o revisar = no se vuelve a pedir (lo revisa
--   app/ai/resumen.py). Un fallido sí se puede volver a pedir: queda una fila nueva.
-- * El resumen es información pública de SICOP reescrita por el modelo; nunca lleva datos internos de Hermatix.
-- * La recomendación es preliminar: no toca reviews ni seguimientos.
-- * No se modifica ni se borra (triggers): un resumen nuevo agrega una fila.

CREATE TABLE ia_summaries (
    id                INTEGER PRIMARY KEY,
    nro_sicop         TEXT NOT NULL REFERENCES tenders (nro_sicop) ON DELETE RESTRICT,
    prompt_version    TEXT NOT NULL CHECK (prompt_version GLOB 'v[0-9]*'),
    modelo            TEXT NOT NULL,
    huella            TEXT NOT NULL CHECK (length(huella) = 64),
    resumen_json      TEXT,
    estado            TEXT NOT NULL CHECK (estado IN ('ok', 'revisar', 'fallido')),
    motivo            TEXT,
    diferencias_json  TEXT,
    costo_estimado    TEXT,
    moneda            TEXT CHECK (moneda IS NULL OR moneda = 'USD'),
    ia_usage_id       INTEGER REFERENCES ia_usage (id),
    creado_en         TEXT NOT NULL,
    CHECK ((estado = 'fallido') = (resumen_json IS NULL)),       -- un fallido nunca trae un resumen inventado
    CHECK (estado <> 'fallido' OR motivo IS NOT NULL),
    CHECK (costo_estimado IS NULL OR moneda IS NOT NULL)         -- dinero siempre con moneda
);

CREATE INDEX idx_ia_summaries_expediente ON ia_summaries (nro_sicop, huella, prompt_version, id);

CREATE TRIGGER ia_summaries_no_se_borran
BEFORE DELETE ON ia_summaries
BEGIN
    SELECT RAISE(ABORT, 'Los resúmenes de la IA no se borran');
END;

CREATE TRIGGER ia_summaries_no_se_modifican
BEFORE UPDATE ON ia_summaries
BEGIN
    SELECT RAISE(ABORT, 'Los resúmenes de la IA no se modifican: pide uno nuevo');
END;
