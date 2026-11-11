-- 0045 · Corregir la oferta desde el chat (DECISION_IA.md §10, paso 4 de §10.7; aprobado por Oscar el 2026-11-11).
--
-- * oferta_versiones: cada versión de la oferta de un cartel. No guarda el PDF: guarda la LISTA de cambios que se le
--   aplican a la oferta que arma la app (cambiar la respuesta de una sección, quitar una sección, etc.;
--   app/oferta_cambios.py). La versión 1 no tiene cambios (es la oferta tal como la arma la app). Cada «Aplicar»
--   crea la siguiente con la lista anterior más el cambio nuevo. Las versiones no se borran ni se modifican.
-- * oferta_propuestas: lo que propuso la IA en el chat. Nada cambia la oferta sin el clic de una persona en
--   «Aplicar» (decisión de Ivania, 2026-11-11). Una propuesta solo pasa de «pendiente» a «aplicada» o «rechazada»,
--   una vez; no se borra.

CREATE TABLE oferta_versiones (
    id                  INTEGER PRIMARY KEY,
    nro_sicop           TEXT NOT NULL REFERENCES tenders (nro_sicop),
    numero              INTEGER NOT NULL CHECK (numero >= 1),
    cambios_json        TEXT NOT NULL,                          -- lista JSON de cambios, en orden
    descripcion         TEXT NOT NULL,                          -- qué cambió respecto a la anterior
    creado_por          INTEGER REFERENCES users (id),
    creado_por_nombre   TEXT NOT NULL,
    creado_en           TEXT NOT NULL,
    UNIQUE (nro_sicop, numero)
);

CREATE TRIGGER oferta_versiones_no_se_borran
BEFORE DELETE ON oferta_versiones
BEGIN
    SELECT RAISE(ABORT, 'Las versiones de la oferta no se borran');
END;

CREATE TRIGGER oferta_versiones_no_se_modifican
BEFORE UPDATE ON oferta_versiones
BEGIN
    SELECT RAISE(ABORT, 'Las versiones de la oferta no se modifican');
END;

CREATE TABLE oferta_propuestas (
    id                  INTEGER PRIMARY KEY,
    nro_sicop           TEXT NOT NULL REFERENCES tenders (nro_sicop),
    mensaje_id          INTEGER REFERENCES asistente_chat (id),  -- el mensaje del chat que la muestra
    cambio_json         TEXT NOT NULL,
    descripcion         TEXT NOT NULL,
    estado              TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aplicada', 'rechazada')),
    creado_en           TEXT NOT NULL,
    decidido_por        INTEGER REFERENCES users (id),
    decidido_por_nombre TEXT,
    decidido_en         TEXT,
    version_id          INTEGER REFERENCES oferta_versiones (id),  -- la versión que creó al aplicarse
    CHECK ((estado = 'pendiente') = (decidido_en IS NULL)),
    CHECK (estado <> 'aplicada' OR version_id IS NOT NULL)
);

CREATE INDEX idx_oferta_propuestas ON oferta_propuestas (nro_sicop, estado);

CREATE TRIGGER oferta_propuestas_no_se_borran
BEFORE DELETE ON oferta_propuestas
BEGIN
    SELECT RAISE(ABORT, 'Las propuestas de cambio no se borran');
END;

CREATE TRIGGER oferta_propuestas_se_deciden_una_vez
BEFORE UPDATE ON oferta_propuestas
WHEN OLD.estado <> 'pendiente' OR NEW.cambio_json IS NOT OLD.cambio_json OR NEW.descripcion IS NOT OLD.descripcion
     OR NEW.nro_sicop IS NOT OLD.nro_sicop OR NEW.mensaje_id IS NOT OLD.mensaje_id OR NEW.creado_en IS NOT OLD.creado_en
BEGIN
    SELECT RAISE(ABORT, 'Una propuesta de cambio solo se decide una vez');
END;
