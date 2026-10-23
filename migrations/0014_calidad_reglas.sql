-- 0014 · Calidad de las reglas (A3): cada medición de score-rules queda guardada con su versión de reglas.
--
-- * rule_score_runs: una fila por medición (versión de reglas, cuándo y cuántos casos de cada fuente).
-- * rule_scores: por medición, una fila por familia y una fila «total» (familia = ''), solo con los conteos.
--   Precisión = verdaderos / alertas · cobertura = cubiertos / relevantes. Se guardan los conteos, no los
--   porcentajes, para recalcularlos sin redondeos. Los errores con su evidencia no se guardan: se recalculan.
-- * No se borran: sirven para ver la evolución de las reglas (guía, lección 13).

CREATE TABLE rule_score_runs (
    id              INTEGER PRIMARY KEY,
    rules_version   TEXT NOT NULL,
    measured_at     TEXT NOT NULL,
    casos_golden    INTEGER NOT NULL CHECK (casos_golden >= 0),
    casos_revision  INTEGER NOT NULL CHECK (casos_revision >= 0)
);

CREATE TABLE rule_scores (
    id           INTEGER PRIMARY KEY,
    run_id       INTEGER NOT NULL REFERENCES rule_score_runs (id),
    familia      TEXT NOT NULL,             -- '' = total (por cartel)
    alertas      INTEGER NOT NULL CHECK (alertas >= 0),
    verdaderos   INTEGER NOT NULL CHECK (verdaderos >= 0 AND verdaderos <= alertas),
    relevantes   INTEGER NOT NULL CHECK (relevantes >= 0),
    cubiertos    INTEGER NOT NULL CHECK (cubiertos >= 0 AND cubiertos <= relevantes),
    UNIQUE (run_id, familia)
);

CREATE TRIGGER rule_score_runs_no_se_borran BEFORE DELETE ON rule_score_runs
BEGIN
    SELECT RAISE(ABORT, 'Las mediciones de calidad no se borran');
END;
