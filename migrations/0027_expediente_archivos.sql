-- 0027 · Gestor de documentos, paso 2: archivos del expediente (docs/GESTOR_DOCUMENTOS.md).
--
-- * seguimiento_archivos: un archivo subido al expediente de un cartel (pliego, anexos, borradores de la oferta).
--   Lo suben y lo bajan el encargado vigente y los administradores (eso lo revisa la ruta).
-- * El archivo vive en EXPEDIENTES_DIR/<N.º SICOP>/<sha256>.<extensión>, fuera de Git y de la base. El nombre que
--   mandó el navegador se guarda solo para mostrarlo: nunca se usa como ruta.
-- * Tipos: PDF, Word (.docx, .doc), Excel (.xlsx, .xls) y ZIP; el contenido real se comprueba al subir.
-- * El mismo archivo (misma huella) no entra dos veces en el mismo expediente (UNIQUE).
-- * Ni import ni evaluate tocan esta tabla. No se borra ni se modifica (triggers).

CREATE TABLE seguimiento_archivos (
    id                 INTEGER PRIMARY KEY,
    seguimiento_id     INTEGER NOT NULL REFERENCES seguimientos (id) ON DELETE RESTRICT,
    nombre             TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    extension          TEXT NOT NULL CHECK (extension IN ('.pdf', '.docx', '.doc', '.xlsx', '.xls', '.zip')),
    tamano             INTEGER NOT NULL CHECK (tamano > 0),
    sha256             TEXT NOT NULL CHECK (length(sha256) = 64),
    ruta               TEXT NOT NULL,
    subido_por         INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    subido_por_nombre  TEXT NOT NULL CHECK (length(trim(subido_por_nombre)) > 0),
    created_at         TEXT NOT NULL,
    UNIQUE (seguimiento_id, sha256)
);

CREATE TRIGGER archivos_expediente_no_se_borran
BEFORE DELETE ON seguimiento_archivos
BEGIN
    SELECT RAISE(ABORT, 'Los archivos del expediente no se borran');
END;

CREATE TRIGGER archivos_expediente_no_se_modifican
BEFORE UPDATE ON seguimiento_archivos
BEGIN
    SELECT RAISE(ABORT, 'Los archivos del expediente no se modifican: sube uno nuevo');
END;
