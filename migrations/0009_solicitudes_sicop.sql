-- 0009 · Solicitudes automáticas a SICOP (obtención automática, lección 2). Ver docs/DECISION_OBTENCION.md §8.
--
-- Cada ejecución de python -m app.cli obtain request deja una fila, también cuando falla.
-- * correo_enviado = 1 desde que se pulsó «Continuar» con el correo: desde ahí SICOP manda un código y la solicitud
--   cuenta para el día (regla 4: una sola por día). Un fallo antes de eso no cuenta.
-- * estado: en_curso → procesando (SICOP mostró «Procesando el reporte») o fallo (con su motivo).
-- * process_id: el número del vínculo «URL de descarga», si lo trae, para la lección 3. Es texto y se guarda solo
--   aquí (base local, fuera de Git): nunca se muestra completo.
-- * captura: ruta de la captura de pantalla del fallo, si la hay.
-- La lección 3 agregará la espera del correo con el enlace y la descarga.

CREATE TABLE solicitudes_sicop (
    id INTEGER PRIMARY KEY,
    solicitada_en TEXT NOT NULL,
    correo_enviado INTEGER NOT NULL DEFAULT 0 CHECK (correo_enviado IN (0, 1)),
    estado TEXT NOT NULL DEFAULT 'en_curso' CHECK (estado IN ('en_curso', 'procesando', 'fallo')),
    motivo TEXT,
    process_id TEXT,
    captura TEXT,
    terminada_en TEXT
);

CREATE INDEX solicitudes_sicop_fecha ON solicitudes_sicop (solicitada_en);
