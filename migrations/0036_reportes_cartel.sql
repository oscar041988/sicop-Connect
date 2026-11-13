-- 0036 · Reporte de cartel Hermatix en PDF, máximo 2 páginas (Reporte con IA, lección 4).
--
-- ia_reports: cada reporte generado (app/ai/reporte.py). El archivo vive en REPORTS_DIR/<nro_sicop>/ (fuera de Git
-- y de la base; entra en el respaldo). Un reporte nuevo nunca borra el anterior: si el resumen no cambió, se
-- reutiliza el último. Nada se borra ni se modifica (triggers).

CREATE TABLE ia_reports (
    id                  INTEGER PRIMARY KEY,
    nro_sicop           TEXT NOT NULL REFERENCES tenders (nro_sicop),
    ia_summary_id       INTEGER NOT NULL REFERENCES ia_summaries (id),
    ruta                TEXT NOT NULL,           -- relativa a REPORTS_DIR: <nro>/reporte_<nro>_<AAAAMMDD-HHMMSS>.pdf
    sha256              TEXT NOT NULL CHECK (length(sha256) = 64),
    paginas             INTEGER NOT NULL CHECK (paginas BETWEEN 1 AND 2),
    creado_por          INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    creado_por_nombre   TEXT NOT NULL CHECK (length(trim(creado_por_nombre)) > 0),
    creado_en           TEXT NOT NULL
);

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
