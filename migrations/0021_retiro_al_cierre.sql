-- 0021 · Enriquecimiento: borrado al cierre y un reintento ante CAPTCHA o bloqueo (DECISION_OBTENCION.md §9,
-- decisiones de Oscar del 2026-10-27, comunicadas por Ivania).
--
-- * enrich_retiros: una fila por cada cartel cuya información de SICOP se borró al pasar su cierre (enrich run). Es
--   el registro del borrado: qué cartel, cuándo, con qué cierre y cuánto se borró. No se modifica ni se borra.
-- * Las fichas, los documentos y su texto siguen sin poder borrarse, SALVO las filas que cubre un retiro ya anotado
--   (mismo cartel y ficha <= hasta_detalle_id). Un DELETE cualquiera sigue fallando. «No se modifican» no cambia.
-- * enrich_consultas: la bitácora se conserva; lo único que puede cambiar, además del aviso, es que su detalle_id
--   pase a NULL cuando un retiro cubre esa ficha. es_reintento marca la consulta repetida tras un CAPTCHA o bloqueo.
-- No toca tenders, reviews ni seguimientos.

CREATE TABLE enrich_retiros (
    id                INTEGER PRIMARY KEY,
    nro_sicop         TEXT NOT NULL REFERENCES tenders (nro_sicop),
    retirado_en       TEXT NOT NULL,
    run_id            INTEGER REFERENCES enrich_runs (id),
    cierre            TEXT NOT NULL,
    hasta_detalle_id  INTEGER NOT NULL,
    fichas            INTEGER NOT NULL,
    documentos        INTEGER NOT NULL,
    paginas           INTEGER NOT NULL,
    bytes             INTEGER NOT NULL
);

CREATE INDEX idx_enrich_retiros_cartel ON enrich_retiros (nro_sicop, hasta_detalle_id);

CREATE TRIGGER retiros_no_se_borran
BEFORE DELETE ON enrich_retiros
BEGIN
    SELECT RAISE(ABORT, 'El registro de borrados no se borra');
END;

CREATE TRIGGER retiros_no_se_modifican
BEFORE UPDATE ON enrich_retiros
BEGIN
    SELECT RAISE(ABORT, 'El registro de borrados no se modifica');
END;

DROP TRIGGER fichas_no_se_borran;
CREATE TRIGGER fichas_no_se_borran
BEFORE DELETE ON tender_details
WHEN NOT EXISTS (SELECT 1 FROM enrich_retiros r WHERE r.nro_sicop = OLD.nro_sicop AND OLD.id <= r.hasta_detalle_id)
BEGIN
    SELECT RAISE(ABORT, 'Las fichas de SICOP no se borran (solo al cierre, con su retiro anotado)');
END;

DROP TRIGGER documentos_no_se_borran;
CREATE TRIGGER documentos_no_se_borran
BEFORE DELETE ON tender_documents
WHEN NOT EXISTS (SELECT 1 FROM enrich_retiros r WHERE r.nro_sicop = OLD.nro_sicop
                 AND OLD.detalle_id <= r.hasta_detalle_id)
BEGIN
    SELECT RAISE(ABORT, 'Los documentos no se borran (solo al cierre, con su retiro anotado)');
END;

DROP TRIGGER texto_documentos_no_se_borra;
CREATE TRIGGER texto_documentos_no_se_borra
BEFORE DELETE ON tender_document_text
WHEN NOT EXISTS (SELECT 1 FROM tender_documents d JOIN enrich_retiros r ON r.nro_sicop = d.nro_sicop
                 WHERE d.id = OLD.documento_id AND d.detalle_id <= r.hasta_detalle_id)
BEGIN
    SELECT RAISE(ABORT, 'El texto de los documentos no se borra (solo al cierre, con su retiro anotado)');
END;

ALTER TABLE enrich_consultas ADD COLUMN es_reintento INTEGER NOT NULL DEFAULT 0 CHECK (es_reintento IN (0, 1));

-- Igual que en 0020, más: detalle_id puede pasar a NULL si un retiro cubre esa ficha; es_reintento no cambia.
DROP TRIGGER consultas_no_se_modifican;
CREATE TRIGGER consultas_no_se_modifican
BEFORE UPDATE ON enrich_consultas
WHEN NEW.id IS NOT OLD.id OR NEW.run_id IS NOT OLD.run_id OR NEW.nro_sicop IS NOT OLD.nro_sicop
  OR NEW.iniciada_en IS NOT OLD.iniciada_en OR NEW.duracion_s IS NOT OLD.duracion_s
  OR NEW.resultado IS NOT OLD.resultado OR NEW.motivo IS NOT OLD.motivo
  OR (NEW.detalle_id IS NOT OLD.detalle_id AND NOT (NEW.detalle_id IS NULL AND EXISTS (
        SELECT 1 FROM enrich_retiros r WHERE r.nro_sicop = OLD.nro_sicop AND OLD.detalle_id <= r.hasta_detalle_id)))
  OR NEW.documentos_guardados IS NOT OLD.documentos_guardados OR NEW.documentos_fallo IS NOT OLD.documentos_fallo
  OR NEW.grabacion IS NOT OLD.grabacion OR NEW.es_reintento IS NOT OLD.es_reintento
BEGIN
    SELECT RAISE(ABORT, 'La bitácora de consultas no se modifica');
END;
