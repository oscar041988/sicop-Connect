-- 0018 · Ficha del concurso en la consulta pública de SICOP (enriquecimiento, lección 2; docs/DETALLE_CARTEL.md).
--
-- Una fila por VERSIÓN de la ficha: si al consultar de nuevo la ficha no cambió (mismo hash), no se agrega nada;
-- si cambió (p. ej. SICOP publicó una modificación), se agrega otra fila y la anterior queda igual.
-- * copia_fiel: las respuestas JSON de SICOP tal como llegaron, MENOS los campos de personas (funcionarios:
--   nombres, identificaciones, correos, teléfonos; decisión de Oscar, 2026-10-27). campos_quitados dice cuáles.
-- * content_hash: SHA-256 de la copia fiel sin los campos que cambian solos con el reloj (startPassYn…).
-- * Las demás columnas son los campos que Oscar marcó como útiles, extraídos de la copia fiel.
-- * Montos como texto Decimal con su moneda; fechas ISO con la zona de Costa Rica; códigos como texto.
-- No toca tenders, reviews ni seguimientos.

CREATE TABLE tender_details (
    id                    INTEGER PRIMARY KEY,
    nro_sicop             TEXT NOT NULL REFERENCES tenders (nro_sicop),
    consultado_en         TEXT NOT NULL,
    content_hash          TEXT NOT NULL,
    copia_fiel            TEXT NOT NULL,
    campos_quitados       TEXT NOT NULL,
    estado_concurso       TEXT,
    version_pliego        TEXT,
    secuencia             TEXT,
    modificado            TEXT CHECK (modificado IS NULL OR modificado IN ('Y', 'N')),
    numero_procedimiento  TEXT,
    descripcion           TEXT,
    tipo_procedimiento    TEXT,
    tipo_modalidad        TEXT,
    tipo_recepcion        TEXT,
    inicio_recepcion      TEXT,
    cierre_recepcion      TEXT,
    apertura              TEXT,
    limite_aclaraciones   TEXT,
    monto_estimado        TEXT,
    moneda_monto          TEXT CHECK (moneda_monto IS NULL OR (length(moneda_monto) = 3 AND moneda_monto = upper(moneda_monto))),
    monto_estimado_usd    TEXT,
    garantias             TEXT,
    criterios             TEXT,
    lineas_total          INTEGER,
    documentos            TEXT,
    UNIQUE (nro_sicop, content_hash),
    CHECK (monto_estimado IS NULL OR moneda_monto IS NOT NULL)  -- dinero siempre con moneda
);

CREATE INDEX idx_tender_details_cartel ON tender_details (nro_sicop, id);

CREATE TRIGGER fichas_no_se_borran
BEFORE DELETE ON tender_details
BEGIN
    SELECT RAISE(ABORT, 'Las fichas de SICOP no se borran');
END;

CREATE TRIGGER fichas_no_se_modifican
BEFORE UPDATE ON tender_details
BEGIN
    SELECT RAISE(ABORT, 'Las fichas de SICOP no se modifican: cada cambio es una fila nueva');
END;
