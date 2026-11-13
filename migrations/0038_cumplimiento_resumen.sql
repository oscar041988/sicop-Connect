-- 0038 · «¿Cumple?» en el resumen y el Reporte de cartel (pedido de Ivania, 2026-11-05).
--
-- * resumen_lineas_cumple: lo que marca una persona (el encargado o un administrador) en cada fila de «Qué piden»:
--   cumple · no_cumple · revisar, con una nota opcional. La fila se reconoce por «clave» (línea + bien o servicio,
--   normalizados; app/cumplimiento.py), así la marca sigue valiendo si llega un resumen nuevo con la misma fila.
--   Nada se borra ni se modifica (triggers): cambiar de idea es marcar otra vez y vale la última.
-- * ia_reports.cumple_huella: huella de los estados «¿Cumple?» con que se hizo el reporte. Si cambian, el reporte
--   se genera de nuevo aunque el resumen sea el mismo (los reportes anteriores tienen NULL: se rehacen una vez).

CREATE TABLE resumen_lineas_cumple (
    id                INTEGER PRIMARY KEY,
    nro_sicop         TEXT NOT NULL REFERENCES tenders (nro_sicop),
    clave             TEXT NOT NULL CHECK (length(clave) BETWEEN 1 AND 300),
    linea             TEXT NOT NULL,              -- la fila como se veía al marcar (para el historial)
    estado            TEXT NOT NULL CHECK (estado IN ('cumple', 'no_cumple', 'revisar')),
    nota              TEXT NOT NULL DEFAULT '' CHECK (length(nota) <= 500),
    marcado_por       INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    marcado_por_nombre TEXT NOT NULL CHECK (length(trim(marcado_por_nombre)) > 0),
    creado_en         TEXT NOT NULL
);

CREATE INDEX idx_resumen_lineas_cumple ON resumen_lineas_cumple (nro_sicop, clave, id);

CREATE TRIGGER resumen_lineas_cumple_no_se_borran
BEFORE DELETE ON resumen_lineas_cumple
BEGIN
    SELECT RAISE(ABORT, 'Las marcas de «¿Cumple?» no se borran: marca otra vez');
END;

CREATE TRIGGER resumen_lineas_cumple_no_se_modifican
BEFORE UPDATE ON resumen_lineas_cumple
BEGIN
    SELECT RAISE(ABORT, 'Las marcas de «¿Cumple?» no se modifican: marca otra vez');
END;

ALTER TABLE ia_reports ADD COLUMN cumple_huella TEXT;
