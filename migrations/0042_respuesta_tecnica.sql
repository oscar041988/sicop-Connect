-- 0042 · Borrador de la respuesta técnica (matriz de cumplimiento) de un cartel (DECISION_PROPUESTA.md, etapa 2).
--
-- Lo que la persona llena en «Respuesta técnica» (panel del cartel) se guarda aquí para seguir otro día: un borrador por
-- cartel, que se reemplaza al guardar. datos_json tiene las filas «el cartel pide · Hermatix ofrece · documento que lo
-- prueba · estado» (app/respuesta_tecnica.py). Sin IA: las filas que salen del resumen con IA llevan origen «resumen»
-- para distinguirlas. Lo ven y lo cambian solo quienes entran al expediente (su encargado y los administradores).

CREATE TABLE respuestas_tecnicas_borrador (
    nro_sicop               TEXT PRIMARY KEY REFERENCES tenders (nro_sicop),
    datos_json              TEXT NOT NULL,
    actualizado_por         INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    actualizado_por_nombre  TEXT NOT NULL CHECK (length(trim(actualizado_por_nombre)) > 0),
    actualizado_en          TEXT NOT NULL
);
