-- 0031 · Asistente de elegibilidad, lección 3: el asistente que pregunta y no supone
-- (docs/Guia_Asistente_Elegibilidad_SICOP.docx; IA aprobada en docs/DECISION_IA.md §7).
--
-- * eligibility_sessions: la conversación del asistente de un cartel (una por cartel). Se pausa sola: todo se
--   guarda al responder y otra persona autorizada la retoma donde quedó.
-- * eligibility_questions: la pregunta de cada requisito de la lista que redactó la IA (una vez por cartel).
--   Si no hay (IA apagada, fallo, sin presupuesto, requisito corregido después), la app arma la suya al mostrarla.
-- * eligibility_answers: cada respuesta. NO se borran ni se modifican (triggers): cambiar una respuesta agrega
--   otra y vale la última. Guarda una copia del requisito y de su tipo de evidencia tal como se preguntó.
--   El archivo vive en ASSISTANT_DOCS_DIR/<nro_sicop>/<sha256>.<extensión>, fuera de Git y de la base: son
--   documentos internos de Hermatix (cada vista o descarga queda en audit_log).

CREATE TABLE eligibility_sessions (
    id                  INTEGER PRIMARY KEY,
    nro_sicop           TEXT NOT NULL UNIQUE REFERENCES tenders (nro_sicop),
    iniciada_por        INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    iniciada_por_nombre TEXT NOT NULL CHECK (length(trim(iniciada_por_nombre)) > 0),
    creado_en           TEXT NOT NULL
);

CREATE TABLE eligibility_questions (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER NOT NULL REFERENCES eligibility_sessions (id) ON DELETE RESTRICT,
    item_id         INTEGER NOT NULL REFERENCES eligibility_items (id) ON DELETE RESTRICT,
    requisito       TEXT NOT NULL,           -- el requisito cuando se redactó: si lo corrigen, la pregunta no sirve
    texto           TEXT NOT NULL CHECK (length(trim(texto)) > 0),
    ia_usage_id     INTEGER NOT NULL REFERENCES ia_usage (id),
    prompt_version  TEXT NOT NULL,
    creado_en       TEXT NOT NULL,
    UNIQUE (session_id, item_id)
);

CREATE TABLE eligibility_answers (
    id                  INTEGER PRIMARY KEY,
    session_id          INTEGER NOT NULL REFERENCES eligibility_sessions (id) ON DELETE RESTRICT,
    item_id             INTEGER NOT NULL REFERENCES eligibility_items (id) ON DELETE RESTRICT,
    requisito           TEXT NOT NULL,           -- copia, tal como se preguntó
    pregunta            TEXT NOT NULL,           -- la pregunta que vio la persona
    tipo_evidencia      TEXT NOT NULL CHECK (tipo_evidencia IN ('numero', 'si_no', 'fecha', 'documento', 'texto')),
    estado              TEXT NOT NULL CHECK (estado IN ('respondido', 'no_lo_tiene', 'no_se')),
    fuente              TEXT NOT NULL CHECK (fuente IN ('usuario', 'perfil')),
    perfil_version_id   INTEGER REFERENCES company_profile_versions (id),
    valor_texto         TEXT,
    valor_numero        TEXT,                    -- número exacto como texto decimal («8»)
    valor_fecha         TEXT,                    -- AAAA-MM-DD
    valor_si_no         INTEGER CHECK (valor_si_no IS NULL OR valor_si_no IN (0, 1)),
    unidad              TEXT,
    vence_el            TEXT,                    -- del documento, escrito por la persona (AAAA-MM-DD)
    nota                TEXT,
    archivo_nombre      TEXT,                    -- el nombre que mandó el navegador: solo para mostrar
    archivo_extension   TEXT CHECK (archivo_extension IS NULL OR archivo_extension IN ('.pdf', '.png', '.jpg')),
    archivo_tamano      INTEGER CHECK (archivo_tamano IS NULL OR archivo_tamano > 0),
    archivo_sha256      TEXT CHECK (archivo_sha256 IS NULL OR length(archivo_sha256) = 64),
    archivo_ruta        TEXT,
    respondido_por      INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    respondido_por_nombre TEXT NOT NULL CHECK (length(trim(respondido_por_nombre)) > 0),
    creado_en           TEXT NOT NULL,
    CHECK ((archivo_ruta IS NULL) = (archivo_sha256 IS NULL)),
    CHECK ((fuente = 'perfil') = (perfil_version_id IS NOT NULL))
);

CREATE INDEX idx_eligibility_answers ON eligibility_answers (session_id, item_id, id);

CREATE TRIGGER eligibility_sessions_no_se_borran
BEFORE DELETE ON eligibility_sessions
BEGIN
    SELECT RAISE(ABORT, 'Las sesiones del asistente no se borran');
END;

CREATE TRIGGER eligibility_answers_no_se_borran
BEFORE DELETE ON eligibility_answers
BEGIN
    SELECT RAISE(ABORT, 'Las respuestas del asistente no se borran: responde de nuevo');
END;

CREATE TRIGGER eligibility_answers_no_se_modifican
BEFORE UPDATE ON eligibility_answers
BEGIN
    SELECT RAISE(ABORT, 'Las respuestas del asistente no se modifican: responde de nuevo');
END;

CREATE TRIGGER eligibility_questions_no_se_borran
BEFORE DELETE ON eligibility_questions
BEGIN
    SELECT RAISE(ABORT, 'Las preguntas del asistente no se borran');
END;
-- Una pregunta se vuelve a redactar (UPDATE) cuando corrigen su requisito; las respuestas guardan su propia copia.
