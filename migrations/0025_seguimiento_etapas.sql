-- 0025 · Gestor de documentos, paso 5: etapas del seguimiento (docs/GESTOR_DOCUMENTOS.md).
--
-- * Etapas aprobadas por Oscar (2026-10-26): preparando · enviada · ganada · perdida. Se SUMAN a las decisiones
--   «Ofertada» y «No se oferta» (reviews); no las reemplazan ni las cambian.
-- * La etapa vigente es la fila más reciente. Sin filas, el cartel está «preparando» (así empieza al darle
--   seguimiento). Un cambio agrega una fila y nunca reemplaza la anterior: queda el historial.
-- * La cambian el encargado vigente y los administradores (eso lo revisa la ruta). Se permite cualquier cambio,
--   también volver atrás, para corregir un error.
-- * El nombre se copia (como en seguimiento_asignaciones) para que el historial diga quién fue.
-- * Ni import ni evaluate tocan esta tabla. No se borra ni se modifica (triggers).

CREATE TABLE seguimiento_etapas (
    id               INTEGER PRIMARY KEY,
    seguimiento_id   INTEGER NOT NULL REFERENCES seguimientos (id) ON DELETE RESTRICT,
    etapa            TEXT NOT NULL CHECK (etapa IN ('preparando', 'enviada', 'ganada', 'perdida')),
    puesta_por       INTEGER NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    puesta_por_nombre TEXT NOT NULL CHECK (length(trim(puesta_por_nombre)) > 0),
    created_at       TEXT NOT NULL
);

CREATE INDEX idx_etapas_seguimiento ON seguimiento_etapas (seguimiento_id, id);

CREATE TRIGGER etapas_no_se_borran
BEFORE DELETE ON seguimiento_etapas
BEGIN
    SELECT RAISE(ABORT, 'Las etapas del seguimiento no se borran');
END;

CREATE TRIGGER etapas_no_se_modifican
BEFORE UPDATE ON seguimiento_etapas
BEGIN
    SELECT RAISE(ABORT, 'Las etapas del seguimiento no se modifican: cambia la etapa de nuevo');
END;
