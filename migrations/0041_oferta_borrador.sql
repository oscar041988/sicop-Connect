-- 0041 · Borrador de la oferta económica de un cartel (DECISION_PROPUESTA.md, aprobado por Oscar el 2026-11-09).
--
-- Lo que la persona llena en «Oferta económica» (panel del cartel) se guarda aquí para seguir otro día: un borrador por
-- cartel, que se reemplaza al guardar. datos_json tiene el mismo formato que el YAML de python -m app.cli oferta
-- economica (app/oferta_economica.py). Trae precios: lo ven y lo cambian solo quienes entran al expediente (su
-- encargado y los administradores). Quién guardó y cuándo queda también en el historial.

CREATE TABLE ofertas_borrador (
    nro_sicop               TEXT PRIMARY KEY REFERENCES tenders (nro_sicop),
    datos_json              TEXT NOT NULL,
    actualizado_por         INTEGER REFERENCES users (id) ON DELETE RESTRICT,
    actualizado_por_nombre  TEXT NOT NULL CHECK (length(trim(actualizado_por_nombre)) > 0),
    actualizado_en          TEXT NOT NULL
);
