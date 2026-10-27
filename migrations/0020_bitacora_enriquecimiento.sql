-- 0020 · Bitácora del enriquecimiento automático (lección 4, entrega 4A: enrich run).
--
-- * enrich_runs: una fila por corrida de enrich run (la tarea programada de las 10:00). Pasa de en_curso a ok,
--   con_fallos, detenida (CAPTCHA o bloqueo) o sin_cola; guarda los totales y el estado del resumen por correo
--   (mismo patrón que solicitudes_sicop.alerta_estado: se manda una sola vez y nunca se reenvía sola).
-- * enrich_consultas: una fila por cartel consultado (hora, resultado, duración, documentos, motivo y la carpeta de
--   su grabación dentro de RECORDINGS_DIR). Es el registro de lo que hizo el sistema: no se modifica ni se borra.
--   aviso_estado guarda si ya salió la alerta inmediata de un CAPTCHA o bloqueo.

CREATE TABLE enrich_runs (
    id                  INTEGER PRIMARY KEY,
    iniciada_en         TEXT NOT NULL,
    terminada_en        TEXT,
    estado              TEXT NOT NULL DEFAULT 'en_curso'
        CHECK (estado IN ('en_curso', 'ok', 'con_fallos', 'detenida', 'sin_cola')),
    maximo              INTEGER NOT NULL,
    en_cola             INTEGER NOT NULL DEFAULT 0,
    consultados         INTEGER NOT NULL DEFAULT 0,
    fallos              INTEGER NOT NULL DEFAULT 0,
    motivo              TEXT,
    grabaciones_borradas INTEGER NOT NULL DEFAULT 0,
    resumen_estado      TEXT CHECK (resumen_estado IN ('vista_previa', 'incierta', 'aceptada', 'fallida')),
    resumen_en          TEXT
);

CREATE TABLE enrich_consultas (
    id                  INTEGER PRIMARY KEY,
    run_id              INTEGER REFERENCES enrich_runs (id),  -- NULL: consulta a mano con enrich --nro
    nro_sicop           TEXT NOT NULL REFERENCES tenders (nro_sicop),
    iniciada_en         TEXT NOT NULL,
    duracion_s          REAL,
    resultado           TEXT NOT NULL CHECK (resultado IN ('nueva', 'sin_cambios', 'fallo', 'control')),
    motivo              TEXT,
    detalle_id          INTEGER REFERENCES tender_details (id),
    documentos_guardados INTEGER NOT NULL DEFAULT 0,
    documentos_fallo    INTEGER NOT NULL DEFAULT 0,
    grabacion           TEXT,
    aviso_estado        TEXT CHECK (aviso_estado IN ('vista_previa', 'incierta', 'aceptada', 'fallida'))
);

CREATE INDEX idx_enrich_consultas_dia ON enrich_consultas (substr(iniciada_en, 1, 10), nro_sicop);
CREATE INDEX idx_enrich_consultas_cartel ON enrich_consultas (nro_sicop, id);

CREATE TRIGGER consultas_no_se_borran
BEFORE DELETE ON enrich_consultas
BEGIN
    SELECT RAISE(ABORT, 'La bitácora de consultas no se borra');
END;

-- Solo se puede anotar el aviso (una vez); lo demás de la consulta no cambia.
CREATE TRIGGER consultas_no_se_modifican
BEFORE UPDATE ON enrich_consultas
WHEN NEW.id IS NOT OLD.id OR NEW.run_id IS NOT OLD.run_id OR NEW.nro_sicop IS NOT OLD.nro_sicop
  OR NEW.iniciada_en IS NOT OLD.iniciada_en OR NEW.duracion_s IS NOT OLD.duracion_s
  OR NEW.resultado IS NOT OLD.resultado OR NEW.motivo IS NOT OLD.motivo OR NEW.detalle_id IS NOT OLD.detalle_id
  OR NEW.documentos_guardados IS NOT OLD.documentos_guardados OR NEW.documentos_fallo IS NOT OLD.documentos_fallo
  OR NEW.grabacion IS NOT OLD.grabacion
BEGIN
    SELECT RAISE(ABORT, 'La bitácora de consultas no se modifica');
END;

CREATE TRIGGER corridas_no_se_borran
BEFORE DELETE ON enrich_runs
BEGIN
    SELECT RAISE(ABORT, 'La bitácora de corridas no se borra');
END;
