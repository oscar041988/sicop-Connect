-- 0008 · Registro de evaluaciones: el panel avisa si hay datos importados después de la última evaluación.
--
-- * evaluate solo guarda filas para los carteles con alguna señal, así que en opportunity_assessments no se
--   distingue un cartel «evaluado sin coincidencias» de uno «nunca evaluado». Esta tabla anota cada
--   evaluación completa (la de evaluate sin --nro-sicop y la del ciclo); evaluar un solo cartel no cuenta.
-- * Las bases que ya existen empiezan sin registro: el panel pedirá un evaluate la primera vez.

CREATE TABLE evaluation_runs (
    id             INTEGER PRIMARY KEY,
    rules_version  TEXT NOT NULL,
    evaluated_at   TEXT NOT NULL,
    carteles       INTEGER NOT NULL CHECK (carteles >= 0)
);
