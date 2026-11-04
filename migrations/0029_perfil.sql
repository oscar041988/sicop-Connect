-- 0029 · Asistente de elegibilidad, lección 1: perfil de Hermatix (docs/Guia_Asistente_Elegibilidad_SICOP.docx).
--
-- * company_profile_items: un dato o documento de la empresa que los carteles suelen pedir (experiencia, permiso,
--   póliza…). Lo ven los dos niveles; lo crean y lo cambian solo los administradores (eso lo revisa la ruta).
-- * company_profile_versions: cada carga o reemplazo agrega una versión; la vigente es la última. Nada se borra
--   ni se modifica (triggers): así queda el historial completo.
-- * El estado (vigente, por vencer, vencido, pendiente) NO se guarda: se calcula al leer con vence_el y la fecha
--   de hoy, para que nunca quede viejo.
-- * El archivo vive en PROFILE_DOCS_DIR/<id del elemento>/<sha256>.<extensión>, fuera de Git y de la base.
--   Son documentos internos y confidenciales de Hermatix: cada vista o descarga queda en audit_log.

CREATE TABLE company_profile_items (
    id                 INTEGER PRIMARY KEY,
    tipo               TEXT NOT NULL CHECK (tipo IN ('experiencia', 'certificacion', 'permiso', 'personal', 'poliza',
                                                    'financiero', 'legal')),
    titulo             TEXT NOT NULL CHECK (length(trim(titulo)) > 0),
    creado_por         INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    creado_por_nombre  TEXT NOT NULL CHECK (length(trim(creado_por_nombre)) > 0),
    created_at         TEXT NOT NULL,
    UNIQUE (tipo, titulo)
);

CREATE TABLE company_profile_versions (
    id                  INTEGER PRIMARY KEY,
    item_id             INTEGER NOT NULL REFERENCES company_profile_items (id) ON DELETE RESTRICT,
    valor               TEXT,                 -- «8 años en rastreo de flotas»
    numero              TEXT,                 -- número exacto como texto decimal («8», «2500000.00»)
    unidad              TEXT,                 -- «años», «CRC»…; con dinero, la moneda
    vigente_desde       TEXT,                 -- AAAA-MM-DD
    vence_el            TEXT,                 -- AAAA-MM-DD; vacío = no vence
    pendiente           INTEGER NOT NULL DEFAULT 0 CHECK (pendiente IN (0, 1)),
    nota                TEXT,
    archivo_nombre      TEXT,                 -- el nombre que mandó el navegador: solo para mostrar
    archivo_extension   TEXT CHECK (archivo_extension IS NULL OR archivo_extension IN ('.pdf', '.png', '.jpg')),
    archivo_tamano      INTEGER CHECK (archivo_tamano IS NULL OR archivo_tamano > 0),
    archivo_sha256      TEXT CHECK (archivo_sha256 IS NULL OR length(archivo_sha256) = 64),
    archivo_ruta        TEXT,
    cargado_por         INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    cargado_por_nombre  TEXT NOT NULL CHECK (length(trim(cargado_por_nombre)) > 0),
    created_at          TEXT NOT NULL,
    CHECK ((archivo_ruta IS NULL) = (archivo_sha256 IS NULL)),
    CHECK (vence_el IS NULL OR vigente_desde IS NULL OR vence_el >= vigente_desde)
);

CREATE INDEX company_profile_versions_item ON company_profile_versions (item_id, id);

CREATE TRIGGER perfil_elementos_no_se_borran
BEFORE DELETE ON company_profile_items
BEGIN
    SELECT RAISE(ABORT, 'Los elementos del perfil no se borran: márcalos como pendientes');
END;

CREATE TRIGGER perfil_versiones_no_se_borran
BEFORE DELETE ON company_profile_versions
BEGIN
    SELECT RAISE(ABORT, 'Las versiones del perfil no se borran');
END;

CREATE TRIGGER perfil_versiones_no_se_modifican
BEFORE UPDATE ON company_profile_versions
BEGIN
    SELECT RAISE(ABORT, 'Las versiones del perfil no se modifican: carga una nueva');
END;
