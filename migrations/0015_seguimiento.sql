-- 0015 · Gestor de documentos, paso 1A: seguimiento de un cartel y su encargado (docs/GESTOR_DOCUMENTOS.md).
--
-- * seguimientos: un cartel en seguimiento. Lo abre cualquier usuario con el botón «Dar seguimiento»; uno solo por
--   cartel (UNIQUE: dos clics a la vez no lo duplican).
-- * seguimiento_asignaciones: quién es el encargado. Solo un administrador asigna o cambia. El encargado vigente
--   es la fila más reciente; un cambio agrega una fila y nunca reemplaza la anterior (historial de traspasos).
-- * Los nombres se copian (como reviews.responsable) para que el historial diga quién fue aunque el usuario
--   cambie de nombre.
-- * Ni import ni evaluate tocan estas tablas. No se borran ni se modifican (triggers).

CREATE TABLE seguimientos (
    id                  INTEGER PRIMARY KEY,
    nro_sicop           TEXT NOT NULL UNIQUE REFERENCES tenders (nro_sicop) ON DELETE RESTRICT,
    abierto_por         INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    abierto_por_nombre  TEXT NOT NULL CHECK (length(trim(abierto_por_nombre)) > 0),
    abierto_en          TEXT NOT NULL
);

CREATE TABLE seguimiento_asignaciones (
    id                   INTEGER PRIMARY KEY,
    seguimiento_id       INTEGER NOT NULL REFERENCES seguimientos (id) ON DELETE RESTRICT,
    encargado_id         INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    encargado_nombre     TEXT NOT NULL CHECK (length(trim(encargado_nombre)) > 0),
    asignado_por         INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    asignado_por_nombre  TEXT NOT NULL CHECK (length(trim(asignado_por_nombre)) > 0),
    created_at           TEXT NOT NULL
);

CREATE INDEX idx_asignaciones_seguimiento ON seguimiento_asignaciones (seguimiento_id, id);

CREATE TRIGGER seguimientos_no_se_borran
BEFORE DELETE ON seguimientos
BEGIN
    SELECT RAISE(ABORT, 'Los seguimientos no se borran');
END;

CREATE TRIGGER seguimientos_no_se_modifican
BEFORE UPDATE ON seguimientos
BEGIN
    SELECT RAISE(ABORT, 'Los seguimientos no se modifican');
END;

CREATE TRIGGER asignaciones_no_se_borran
BEFORE DELETE ON seguimiento_asignaciones
BEGIN
    SELECT RAISE(ABORT, 'Las asignaciones de encargado no se borran');
END;

CREATE TRIGGER asignaciones_no_se_modifican
BEFORE UPDATE ON seguimiento_asignaciones
BEGIN
    SELECT RAISE(ABORT, 'Las asignaciones de encargado no se modifican: asigna de nuevo');
END;
