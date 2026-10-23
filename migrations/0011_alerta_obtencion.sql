-- 0011 · Alerta de FALLO de la obtención automática (lección 4). Ver app/sources/automatico.py.
--
-- Cuando una solicitud termina «fallido», obtain auto manda UNA alerta al buzón de OBTAIN_ALERT_TO con el motivo y
-- el plan B (descargar a mano con el correo «Envío de reporte» y dejar el ZIP en la carpeta de entrada).
-- * alerta_estado: vista_previa (dry-run: solo el archivo en EXPORTS_DIR) · incierta (se llamó a Gmail y no hubo
--   respuesta clara) · aceptada · fallida. Una alerta con estado no se repite sola.
-- * alerta_en: hora del último cambio de la alerta.
-- Las solicitudes fallidas de antes de esta migración no se alertan: ya se revisaron a mano.

ALTER TABLE solicitudes_sicop ADD COLUMN alerta_estado TEXT
    CHECK (alerta_estado IN ('vista_previa', 'incierta', 'aceptada', 'fallida', 'anterior'));
ALTER TABLE solicitudes_sicop ADD COLUMN alerta_en TEXT;

UPDATE solicitudes_sicop SET alerta_estado = 'anterior' WHERE estado = 'fallido';
