-- 0028 · Gestor de documentos, paso 3: notas del expediente (docs/GESTOR_DOCUMENTOS.md).
--
-- * seguimiento_notas: una nota escrita en el expediente de un cartel, con su autor y su fecha.
--   La escriben y la leen el encargado vigente y los administradores (eso lo revisa la ruta).
-- * El nombre del autor se copia (como en seguimiento_etapas) para que la nota diga quién la escribió aunque el
--   usuario cambie de nombre o se elimine.
-- * Hasta 2000 caracteres, como el comentario de una revisión.
-- * Ni import ni evaluate tocan esta tabla. No se borra ni se modifica (triggers): para corregir, otra nota.

CREATE TABLE seguimiento_notas (
    id                 INTEGER PRIMARY KEY,
    seguimiento_id     INTEGER NOT NULL REFERENCES seguimientos (id) ON DELETE RESTRICT,
    texto              TEXT NOT NULL CHECK (length(trim(texto)) > 0 AND length(texto) <= 2000),
    escrita_por        INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    escrita_por_nombre TEXT NOT NULL CHECK (length(trim(escrita_por_nombre)) > 0),
    created_at         TEXT NOT NULL
);

CREATE INDEX idx_notas_seguimiento ON seguimiento_notas (seguimiento_id, id);

CREATE TRIGGER notas_no_se_borran
BEFORE DELETE ON seguimiento_notas
BEGIN
    SELECT RAISE(ABORT, 'Las notas del expediente no se borran');
END;

CREATE TRIGGER notas_no_se_modifican
BEFORE UPDATE ON seguimiento_notas
BEGIN
    SELECT RAISE(ABORT, 'Las notas del expediente no se modifican: escribe otra nota');
END;
