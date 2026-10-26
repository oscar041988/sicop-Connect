-- 0017 · Obtención en el servidor: dos solicitudes por día y descarga a mano (aprobado por Oscar, 2026-10-26).
--
-- * turno: la hora de OBTAIN_REQUEST_HOUR que originó la solicitud («07:30» o «14:00»). Las filas de antes
--   quedan con ''.
-- * Una sola solicitud por TURNO con el correo enviado: índice único por (día, turno), en lugar del de la 0010
--   (uno por día). La base lo impide aunque falle el programa.
-- * Estado nuevo enlace_recibido: llegó el correo «Envío de reporte» y la descarga es a mano (OBTAIN_DOWNLOAD=manual,
--   porque SICOP bloqueó la descarga hecha por el programa). Es un estado final, como validado.
-- * alerta_estado (0011) sirve también para el recordatorio de enlace_recibido: se manda una sola vez.
-- SQLite no deja cambiar un CHECK: se rehace la tabla con una copia fiel de las filas.

CREATE TABLE solicitudes_sicop_nueva (
    id INTEGER PRIMARY KEY,
    solicitada_en TEXT NOT NULL,
    turno TEXT NOT NULL DEFAULT '',
    correo_enviado INTEGER NOT NULL DEFAULT 0 CHECK (correo_enviado IN (0, 1)),
    estado TEXT NOT NULL DEFAULT 'solicitado' CHECK (estado IN
        ('solicitado', 'codigo_ingresado', 'esperando_enlace', 'descargado', 'validado', 'enlace_recibido',
         'fallido')),
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
    archivo_entrada TEXT,
    alerta_estado TEXT CHECK (alerta_estado IN ('vista_previa', 'incierta', 'aceptada', 'fallida', 'anterior')),
    alerta_en TEXT
);

INSERT INTO solicitudes_sicop_nueva (id, solicitada_en, correo_enviado, estado, motivo, process_id, captura,
                                     codigo_ingresado_en, esperando_enlace_en, enlace_recibido_en, descargado_en,
                                     validado_en, terminada_en, archivo_original, archivo_sha256, archivo_entrada,
                                     alerta_estado, alerta_en)
SELECT id, solicitada_en, correo_enviado, estado, motivo, process_id, captura, codigo_ingresado_en,
       esperando_enlace_en, enlace_recibido_en, descargado_en, validado_en, terminada_en, archivo_original,
       archivo_sha256, archivo_entrada, alerta_estado, alerta_en
FROM solicitudes_sicop;

DROP TABLE solicitudes_sicop;
ALTER TABLE solicitudes_sicop_nueva RENAME TO solicitudes_sicop;

CREATE INDEX solicitudes_sicop_fecha ON solicitudes_sicop (solicitada_en);
CREATE UNIQUE INDEX solicitudes_sicop_una_por_turno ON solicitudes_sicop (substr(solicitada_en, 1, 10), turno)
    WHERE correo_enviado = 1;
