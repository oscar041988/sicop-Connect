-- 0032 · Asistente de elegibilidad: respuesta «Lo tiene · archivo pendiente» (pedido de Ivania, 2026-11-04).
--
-- Los documentos de Hermatix son delicados y no se suben hasta que el asistente esté listo, pero Hermatix sí los
-- tiene: «Todavía no lo sé» no lo dice. eligibility_answers.estado acepta ahora 'archivo_pendiente' (solo en
-- requisitos de tipo documento; lo revisa app/asistente.py): se guarda sin archivo y se completa después con
-- «Cambiar», que agrega otra respuesta (las anteriores no se borran ni se modifican).
--
-- SQLite no cambia un CHECK sin reconstruir la tabla: se copian todas las respuestas con su id. Ninguna tabla
-- apunta a eligibility_answers, así que las llaves foráneas quedan encendidas. DROP TABLE no dispara el trigger de
-- borrado; el índice y los triggers se vuelven a crear igual que en la 0031.

CREATE TABLE eligibility_answers_nueva (
    id                  INTEGER PRIMARY KEY,
    session_id          INTEGER NOT NULL REFERENCES eligibility_sessions (id) ON DELETE RESTRICT,
    item_id             INTEGER NOT NULL REFERENCES eligibility_items (id) ON DELETE RESTRICT,
    requisito           TEXT NOT NULL,           -- copia, tal como se preguntó
    pregunta            TEXT NOT NULL,           -- la pregunta que vio la persona
    tipo_evidencia      TEXT NOT NULL CHECK (tipo_evidencia IN ('numero', 'si_no', 'fecha', 'documento', 'texto')),
    estado              TEXT NOT NULL CHECK (estado IN ('respondido', 'archivo_pendiente', 'no_lo_tiene', 'no_se')),
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
    CHECK ((fuente = 'perfil') = (perfil_version_id IS NOT NULL)),
    CHECK (estado <> 'archivo_pendiente' OR (tipo_evidencia = 'documento' AND archivo_ruta IS NULL))
);

INSERT INTO eligibility_answers_nueva (id, session_id, item_id, requisito, pregunta, tipo_evidencia, estado, fuente,
                                       perfil_version_id, valor_texto, valor_numero, valor_fecha, valor_si_no, unidad,
                                       vence_el, nota, archivo_nombre, archivo_extension, archivo_tamano,
                                       archivo_sha256, archivo_ruta, respondido_por, respondido_por_nombre, creado_en)
SELECT id, session_id, item_id, requisito, pregunta, tipo_evidencia, estado, fuente, perfil_version_id, valor_texto,
       valor_numero, valor_fecha, valor_si_no, unidad, vence_el, nota, archivo_nombre, archivo_extension,
       archivo_tamano, archivo_sha256, archivo_ruta, respondido_por, respondido_por_nombre, creado_en
FROM eligibility_answers;

DROP TABLE eligibility_answers;
ALTER TABLE eligibility_answers_nueva RENAME TO eligibility_answers;

CREATE INDEX idx_eligibility_answers ON eligibility_answers (session_id, item_id, id);

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
