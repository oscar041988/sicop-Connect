-- 0039 · Reporte de cartel: hasta 3 páginas (Oscar, 2026-11-09, por Ivania).
--
-- Al final del reporte va «Por qué se recomienda»: unos media página con la explicación detallada de la recomendación
-- (prompt v6). Por eso el máximo pasa de 2 a 3 páginas (app/ai/reporte.py, MAX_PAGINAS; DECISION_IA.md regla 9).
--
-- SQLite no cambia un CHECK sin reconstruir la tabla: se copian todos los reportes con su id, sin cambiar nada.
-- Ninguna tabla apunta a ia_reports. DROP TABLE no dispara el trigger de borrado; el índice y los dos triggers se
-- vuelven a crear iguales (0036).

CREATE TABLE ia_reports_nueva (
    id                  INTEGER PRIMARY KEY,
    nro_sicop           TEXT NOT NULL REFERENCES tenders (nro_sicop),
    ia_summary_id       INTEGER NOT NULL REFERENCES ia_summaries (id),
    ruta                TEXT NOT NULL,           -- relativa a REPORTS_DIR: <nro>/reporte_<nro>_<AAAAMMDD-HHMMSS>.pdf
    sha256              TEXT NOT NULL CHECK (length(sha256) = 64),
    paginas             INTEGER NOT NULL CHECK (paginas BETWEEN 1 AND 3),
    creado_por          INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    creado_por_nombre   TEXT NOT NULL CHECK (length(trim(creado_por_nombre)) > 0),
    creado_en           TEXT NOT NULL,
    cumple_huella       TEXT
);

INSERT INTO ia_reports_nueva (id, nro_sicop, ia_summary_id, ruta, sha256, paginas, creado_por, creado_por_nombre,
                              creado_en, cumple_huella)
SELECT id, nro_sicop, ia_summary_id, ruta, sha256, paginas, creado_por, creado_por_nombre, creado_en, cumple_huella
FROM ia_reports;

DROP TABLE ia_reports;
ALTER TABLE ia_reports_nueva RENAME TO ia_reports;

CREATE INDEX idx_ia_reports ON ia_reports (nro_sicop, id);

CREATE TRIGGER ia_reports_no_se_borran
BEFORE DELETE ON ia_reports
BEGIN
    SELECT RAISE(ABORT, 'Los reportes de cartel no se borran');
END;

CREATE TRIGGER ia_reports_no_se_modifican
BEFORE UPDATE ON ia_reports
BEGIN
    SELECT RAISE(ABORT, 'Los reportes de cartel no se modifican: genera uno nuevo');
END;
