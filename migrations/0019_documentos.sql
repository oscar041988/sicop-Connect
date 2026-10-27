-- 0019 · Documentos de la ficha del concurso y su texto (enriquecimiento, lección 3; docs/DETALLE_CARTEL.md §4).
--
-- * tender_documents: una fila por cada intento con un documento de la ficha (guardado, duplicado, rechazado,
--   omitido o fallo), con su motivo. Un documento (mismo cartel y mismo nombre en el servidor de SICOP) se guarda
--   UNA sola vez: índice único parcial. Los intentos que no se guardaron quedan como historial.
-- * El archivo está en DOCUMENTS_DIR/<ruta_local>, fuera de Git; aquí solo su registro y su huella (SHA-256).
-- * tender_document_text: el texto de cada página (de un PDF, o de los PDF dentro de un ZIP). Es DATO: nunca se
--   interpreta como instrucciones.
-- * Nada se modifica ni se borra (triggers).

CREATE TABLE tender_documents (
    id                INTEGER PRIMARY KEY,
    nro_sicop         TEXT NOT NULL REFERENCES tenders (nro_sicop),
    detalle_id        INTEGER NOT NULL REFERENCES tender_details (id),
    doc_seq           TEXT,
    tipo_documento    TEXT,
    nombre_documento  TEXT,
    nombre_original   TEXT,
    server_file       TEXT NOT NULL,
    extension         TEXT,
    tamano_bytes      INTEGER,
    sha256            TEXT,
    ruta_local        TEXT,
    registrado_en     TEXT NOT NULL,
    estado            TEXT NOT NULL CHECK (estado IN
        ('guardado', 'duplicado', 'rechazado', 'omitido_tamano', 'omitido_tope', 'fallo')),
    motivo            TEXT,
    texto_estado      TEXT CHECK (texto_estado IS NULL OR texto_estado IN ('extraido', 'sin_texto', 'error', 'no_aplica')),
    paginas           INTEGER,
    CHECK (estado != 'guardado' OR (sha256 IS NOT NULL AND ruta_local IS NOT NULL AND texto_estado IS NOT NULL))
);

CREATE UNIQUE INDEX tender_documents_guardado_una_vez ON tender_documents (nro_sicop, server_file)
    WHERE estado = 'guardado';
CREATE INDEX idx_tender_documents_cartel ON tender_documents (nro_sicop, id);

CREATE TABLE tender_document_text (
    id               INTEGER PRIMARY KEY,
    documento_id     INTEGER NOT NULL REFERENCES tender_documents (id),
    archivo_interno  TEXT NOT NULL DEFAULT '',
    pagina           INTEGER NOT NULL CHECK (pagina >= 1),
    texto            TEXT NOT NULL,
    UNIQUE (documento_id, archivo_interno, pagina)
);

CREATE TRIGGER documentos_no_se_borran
BEFORE DELETE ON tender_documents
BEGIN
    SELECT RAISE(ABORT, 'Los documentos no se borran');
END;

CREATE TRIGGER documentos_no_se_modifican
BEFORE UPDATE ON tender_documents
BEGIN
    SELECT RAISE(ABORT, 'Los documentos no se modifican: cada intento es una fila nueva');
END;

CREATE TRIGGER texto_documentos_no_se_borra
BEFORE DELETE ON tender_document_text
BEGIN
    SELECT RAISE(ABORT, 'El texto de los documentos no se borra');
END;

CREATE TRIGGER texto_documentos_no_se_modifica
BEFORE UPDATE ON tender_document_text
BEGIN
    SELECT RAISE(ABORT, 'El texto de los documentos no se modifica');
END;
