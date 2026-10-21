-- 0010 · Máquina de estados de la solicitud a SICOP (obtención automática, lección 3).
--
-- Estados, solo hacia adelante:
--   solicitado → codigo_ingresado → esperando_enlace → descargado → validado; o fallido (con motivo) desde
--   cualquiera. Los estados viven en la base: un reinicio no pierde la solicitud (obtain poll la retoma).
-- * Hora de cada cambio en su columna (*_en). enlace_recibido_en es la hora en que Gmail recibió el correo.
-- * archivo_original: el ZIP tal como llegó (RAW_DATA_DIR/descargas), con su archivo_sha256.
--   archivo_entrada: la copia validada en INCOMING_DIR, la que importa el ciclo.
-- * Una sola solicitud por día con el correo enviado: índice único (la base lo impide aunque falle el programa).
-- SQLite no deja cambiar un CHECK: se rehace la tabla y se convierten los estados de la 0009
-- (en_curso → solicitado, procesando → esperando_enlace, fallo → fallido).

CREATE TABLE solicitudes_sicop_nueva (
    id INTEGER PRIMARY KEY,
    solicitada_en TEXT NOT NULL,
    correo_enviado INTEGER NOT NULL DEFAULT 0 CHECK (correo_enviado IN (0, 1)),
    estado TEXT NOT NULL DEFAULT 'solicitado' CHECK (estado IN
        ('solicitado', 'codigo_ingresado', 'esperando_enlace', 'descargado', 'validado', 'fallido')),
    motivo TEXT,
    process_id TEXT,
    captura TEXT,
    codigo_ingresado_en TEXT,
    esperando_enlace_en TEXT,
    enlace_recibido_en TEXT,
    descargado_en TEXT,
    validado_en TEXT,
    terminada_en TEXT,
    archivo_original TEXT,
    archivo_sha256 TEXT,
    archivo_entrada TEXT
);

INSERT INTO solicitudes_sicop_nueva (id, solicitada_en, correo_enviado, estado, motivo, process_id, captura,
                                     esperando_enlace_en, terminada_en)
SELECT id, solicitada_en, correo_enviado,
       CASE estado WHEN 'en_curso' THEN 'solicitado' WHEN 'procesando' THEN 'esperando_enlace' ELSE 'fallido' END,
       motivo, process_id, captura,
       CASE estado WHEN 'procesando' THEN terminada_en END,
       CASE estado WHEN 'fallo' THEN terminada_en END
FROM solicitudes_sicop;

DROP TABLE solicitudes_sicop;
ALTER TABLE solicitudes_sicop_nueva RENAME TO solicitudes_sicop;

CREATE INDEX solicitudes_sicop_fecha ON solicitudes_sicop (solicitada_en);
CREATE UNIQUE INDEX solicitudes_sicop_una_por_dia ON solicitudes_sicop (substr(solicitada_en, 1, 10))
    WHERE correo_enviado = 1;
